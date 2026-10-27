from django.urls import path

from .auth_views import LoginAPIView, LogoutAPIView, MeAPIView, RegisterAPIView, CSRFAPIView

urlpatterns = [
    path("csrf/", CSRFAPIView.as_view(), name="auth-csrf"),
    path("register/", RegisterAPIView.as_view(), name="auth-register"),
    path("login/", LoginAPIView.as_view(), name="auth-login"),
    path("logout/", LogoutAPIView.as_view(), name="auth-logout"),
    path("me/", MeAPIView.as_view(), name="auth-me"),
]
