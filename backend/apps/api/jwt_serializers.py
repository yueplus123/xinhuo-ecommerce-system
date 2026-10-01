from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer, TokenRefreshSerializer
from rest_framework_simplejwt.settings import api_settings
from rest_framework_simplejwt.tokens import RefreshToken

from backend.apps.catalog.login_tracking import record_staff_login, touch_staff_last_login


class StaffTokenObtainPairSerializer(TokenObtainPairSerializer):
    def validate(self, attrs):
        data = super().validate(attrs)
        if not self.user.is_active:
            raise serializers.ValidationError("账号已禁用。")
        if not self.user.is_staff:
            raise serializers.ValidationError(
                "该账号未开通职员权限，无法登录业务前台。日常操作请等待管理员在「用户」中勾选「职员状态」；"
                "数据维护由管理员在 Django 后台完成。"
            )
        req = self.context.get("request")
        record_staff_login(req, self.user.pk)
        return data


class StaffTokenRefreshSerializer(TokenRefreshSerializer):
    """刷新 access 时同步最近登录（职员端长期会话常只走 refresh，不走账号密码 token）。"""

    def validate(self, attrs):
        refresh_str = attrs["refresh"]
        token = RefreshToken(refresh_str)
        uid = token[api_settings.USER_ID_CLAIM]
        data = super().validate(attrs)
        req = self.context.get("request")
        touch_staff_last_login(req, uid)
        return data
