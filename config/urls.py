from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/", include("apps.recruitment.urls")),
    path("api/auth/", include("apps.recruitment.auth_urls")),
]

# Resumes are served exclusively through the authenticated candidate CV action.
