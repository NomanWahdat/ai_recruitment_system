from django.contrib.auth import authenticate
from django.contrib.auth.models import User
from rest_framework import permissions, status
from rest_framework.authtoken.models import Token
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView


class RegisterAPIView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request: Request):
        username = (request.data.get("username") or "").strip()
        email = (request.data.get("email") or "").strip()
        password = request.data.get("password") or ""
        full_name = (request.data.get("full_name") or "").strip()

        if not username or not password:
            return Response({"detail": "Username and password are required."}, status=status.HTTP_400_BAD_REQUEST)

        if len(password) < 6:
            return Response({"detail": "Password must be at least 6 characters."}, status=status.HTTP_400_BAD_REQUEST)

        if User.objects.filter(username=username).exists():
            return Response({"detail": "Username already taken."}, status=status.HTTP_409_CONFLICT)

        if email and User.objects.filter(email=email).exists():
            return Response({"detail": "Email already registered."}, status=status.HTTP_409_CONFLICT)

        first_name = full_name.split(" ")[0] if full_name else ""
        last_name = " ".join(full_name.split(" ")[1:]) if full_name else ""

        user = User.objects.create_user(
            username=username,
            email=email,
            password=password,
            first_name=first_name,
            last_name=last_name,
        )

        token, _ = Token.objects.get_or_create(user=user)

        return Response({
            "token": token.key,
            "user": _serialize_user(user),
        }, status=status.HTTP_201_CREATED)


class LoginAPIView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request: Request):
        username = (request.data.get("username") or "").strip()
        password = request.data.get("password") or ""

        if not username or not password:
            return Response({"detail": "Username and password are required."}, status=status.HTTP_400_BAD_REQUEST)

        # Try authenticating by username first. If that fails, allow users
        # to supply their email address in the username field as a fallback.
        user = authenticate(username=username, password=password)
        if not user:
            # If the submitted username looks like an email, try to find
            # the user by email and authenticate using their username.
            if "@" in username:
                try:
                    candidate = User.objects.get(email__iexact=username)
                    user = authenticate(username=candidate.username, password=password)
                except User.DoesNotExist:
                    user = None

        if not user:
            return Response({"detail": "Invalid credentials."}, status=status.HTTP_401_UNAUTHORIZED)

        token, _ = Token.objects.get_or_create(user=user)

        return Response({
            "token": token.key,
            "user": _serialize_user(user),
        }, status=status.HTTP_200_OK)


class LogoutAPIView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request: Request):
        try:
            request.user.auth_token.delete()
        except Exception:
            pass
        return Response({"detail": "Logged out."}, status=status.HTTP_200_OK)


class MeAPIView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request: Request):
        return Response({"user": _serialize_user(request.user)}, status=status.HTTP_200_OK)


def _serialize_user(user: User) -> dict:
    return {
        "id": user.id,
        "username": user.username,
        "email": user.email,
        "full_name": f"{user.first_name} {user.last_name}".strip() or user.username,
        "is_staff": user.is_staff,
        "date_joined": user.date_joined.isoformat(),
    }
