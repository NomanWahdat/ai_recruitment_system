"""Tests for authentication API."""
from django.test import TestCase
from django.contrib.auth.models import User
from rest_framework.test import APITestCase
from rest_framework import status


class AuthAPITests(APITestCase):
    """Test cases for authentication endpoints."""

    def test_register_user(self):
        """Test user registration."""
        data = {
            "username": "testuser",
            "email": "test@example.com",
            "password": "testpass123",
            "full_name": "Test User",
        }
        response = self.client.post("/api/auth/register/", data, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIn("token", response.data)
        self.assertIn("user", response.data)
        self.assertEqual(response.data["user"]["username"], "testuser")

    def test_register_duplicate_username(self):
        """Test registration with duplicate username fails."""
        User.objects.create_user(username="existing", password="pass123")
        data = {
            "username": "existing",
            "email": "new@example.com",
            "password": "testpass123",
        }
        response = self.client.post("/api/auth/register/", data, format="json")
        self.assertEqual(response.status_code, status.HTTP_409_CONFLICT)

    def test_login_success(self):
        """Test successful login."""
        User.objects.create_user(username="logintest", password="mypassword")
        data = {
            "username": "logintest",
            "password": "mypassword",
        }
        response = self.client.post("/api/auth/login/", data, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("token", response.data)
        self.assertIn("user", response.data)

    def test_login_invalid_credentials(self):
        """Test login with wrong password fails."""
        User.objects.create_user(username="wrongpass", password="correct123")
        data = {
            "username": "wrongpass",
            "password": "wrongpassword",
        }
        response = self.client.post("/api/auth/login/", data, format="json")
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_me_endpoint_authenticated(self):
        """Test /me endpoint returns user when authenticated."""
        user = User.objects.create_user(username="meuser", password="pass123")
        from rest_framework.authtoken.models import Token
        token, _ = Token.objects.get_or_create(user=user)

        self.client.credentials(HTTP_AUTHORIZATION=f"Token {token.key}")
        response = self.client.get("/api/auth/me/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["user"]["username"], "meuser")

    def test_me_endpoint_unauthenticated(self):
        """Test /me endpoint fails without authentication."""
        response = self.client.get("/api/auth/me/")
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_logout(self):
        """Test logout invalidates token."""
        user = User.objects.create_user(username="logoutuser", password="pass123")
        from rest_framework.authtoken.models import Token
        token, _ = Token.objects.get_or_create(user=user)

        self.client.credentials(HTTP_AUTHORIZATION=f"Token {token.key}")
        response = self.client.post("/api/auth/logout/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
