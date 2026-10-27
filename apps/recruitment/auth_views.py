from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.core.validators import validate_email
from django.db import IntegrityError, transaction
from django.middleware.csrf import get_token
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_protect, ensure_csrf_cookie
from rest_framework import permissions
from rest_framework.authtoken.models import Token
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.views import APIView


def _serialize_user(user):
    return {
        "id": user.pk,
        "username": user.username,
        "email": user.email,
        "full_name": user.get_full_name() or user.username,
        "is_staff": user.is_staff,
        "date_joined": user.date_joined.isoformat(),
    }


def signed_in(request, user, code=200):
    login(request._request, user, backend="django.contrib.auth.backends.ModelBackend")
    data = {"user": _serialize_user(user), "csrfToken": get_token(request)}
    if request.data.get("issue_token") is True:
        Token.objects.filter(user=user).delete()
        data["token"] = Token.objects.create(user=user).key
    return Response(data, status=code)


@method_decorator(ensure_csrf_cookie, name="dispatch")
class CSRFAPIView(APIView):
    permission_classes = [permissions.AllowAny]

    def get(self, request):
        return Response({"csrfToken": get_token(request)})


@method_decorator(csrf_protect, name="dispatch")
class PublicAuthAPIView(APIView):
    permission_classes = [permissions.AllowAny]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "auth"


class RegisterAPIView(PublicAuthAPIView):
    def post(self, request):
        username = str(request.data.get("username", "")).strip()
        email = str(request.data.get("email", "")).strip().lower()
        password = request.data.get("password", "")
        if not username or not isinstance(password, str) or len(username) > 150:
            return Response({"detail": "A username and password are required."}, status=400)
        user = User(username=username, email=email)
        try:
            User._meta.get_field("username").run_validators(username)
            validate_email(email)
            validate_password(password, user=user)
        except ValidationError as exc:
            return Response({"detail": " ".join(exc.messages)}, status=400)
        if (
            User.objects.filter(username=username).exists()
            or User.objects.filter(email__iexact=email).exists()
        ):
            return Response({"detail": "Username or email already registered."}, status=409)
        names = str(request.data.get("full_name", "")).strip().split(" ", 1)
        try:
            with transaction.atomic():
                user = User.objects.create_user(
                    username=username,
                    email=email,
                    password=password,
                    first_name=names[0][:150],
                    last_name=(names[1] if len(names) > 1 else "")[:150],
                )
        except IntegrityError:
            return Response({"detail": "Username already registered."}, status=409)
        return signed_in(request, user, 201)


class LoginAPIView(PublicAuthAPIView):
    def post(self, request):
        username = str(request.data.get("username", "")).strip()
        password = request.data.get("password", "")
        if not isinstance(password, str):
            return Response({"detail": "Invalid credentials."}, status=400)
        user = authenticate(request=request._request, username=username, password=password)
        if not user and "@" in username:
            matches = list(User.objects.filter(email__iexact=username)[:2])
            if len(matches) == 1:
                user = authenticate(
                    request=request._request, username=matches[0].username, password=password
                )
        if not user:
            return Response({"detail": "Invalid credentials."}, status=401)
        return signed_in(request, user)


class LogoutAPIView(APIView):
    def post(self, request):
        Token.objects.filter(user=request.user).delete()
        logout(request._request)
        return Response({"detail": "Logged out."})


class MeAPIView(APIView):
    def get(self, request):
        return Response({"user": _serialize_user(request.user)})
