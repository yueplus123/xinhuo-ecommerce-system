from django.conf import settings
from django.conf.urls.static import static
from django.urls import include, path

# 后端是纯 API 服务：不再提供任何 HTML 页面（登录页 / Django admin 均已移除）。
# 页面分别由 frontend（职员端）与 admin（管理后台）两个独立前端应用提供。
urlpatterns = [
    path("api/", include("backend.apps.api.urls", namespace="api")),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
