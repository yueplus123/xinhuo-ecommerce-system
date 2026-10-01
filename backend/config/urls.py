from django.conf import settings
from django.contrib import admin
from django.contrib.auth import views as auth_views
from django.urls import include, path
from django.conf.urls.static import static

from backend.apps.catalog import views as catalog_views

urlpatterns = [
    path("django-admin/", admin.site.urls),
    path("accounts/login/", auth_views.LoginView.as_view(template_name="registration/login.html"), name="login"),
    path("accounts/logout/", auth_views.LogoutView.as_view(), name="logout"),
    path("", catalog_views.home, name="home"),
    path("backoffice/", include("backend.apps.catalog.urls", namespace="backoffice")),
    path("api/", include("backend.apps.api.urls", namespace="api")),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
