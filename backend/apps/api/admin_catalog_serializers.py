from django.core.exceptions import ValidationError
from django.core.validators import URLValidator
from django.db.models import Count, Max
from rest_framework import serializers

from backend.apps.catalog.models import Business, Platform, PlatformTagPool, SKU, Tag

from .serializers import TagSerializer


def _normalize_url(value: str) -> str:
    value = (value or "").strip()
    if not value:
        return value
    if "://" not in value:
        return f"https://{value}"
    return value


class AdminSkuTreeSerializer(serializers.ModelSerializer):
    status_label = serializers.CharField(source="get_status_display", read_only=True)
    quick_phrase_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = SKU
        fields = ("id", "business", "name", "status", "status_label", "quick_phrase_count")


class AdminBusinessTreeSerializer(serializers.ModelSerializer):
    skus = AdminSkuTreeSerializer(many=True, read_only=True)
    status_label = serializers.CharField(source="get_status_display", read_only=True)
    sku_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = Business
        fields = ("id", "platform", "name", "status", "status_label", "sku_count", "skus")


class AdminPlatformWorkbenchSerializer(serializers.ModelSerializer):
    platform_tags = TagSerializer(many=True, read_only=True)
    businesses = AdminBusinessTreeSerializer(many=True, read_only=True)
    status_label = serializers.CharField(source="get_status_display", read_only=True)
    business_count = serializers.IntegerField(read_only=True)
    sku_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = Platform
        fields = (
            "id",
            "name",
            "status",
            "status_label",
            "url",
            "note",
            "sort_order",
            "platform_tags",
            "business_count",
            "sku_count",
            "businesses",
        )


class AdminPlatformWriteSerializer(serializers.ModelSerializer):
    platform_tag_ids = serializers.PrimaryKeyRelatedField(
        source="platform_tags",
        queryset=PlatformTagPool.objects.all(),
        many=True,
        required=False,
    )
    url = serializers.CharField(required=False, allow_blank=True)

    class Meta:
        model = Platform
        fields = ("id", "name", "status", "url", "note", "platform_tag_ids")

    def validate_url(self, value):
        value = _normalize_url(value)
        if not value:
            return value
        try:
            URLValidator()(value)
        except ValidationError as exc:
            raise serializers.ValidationError("请输入有效的网址。") from exc
        return value

    def create(self, validated_data):
        tags = validated_data.pop("platform_tags", [])
        max_o = Platform.objects.aggregate(m=Max("sort_order"))["m"] or 0
        obj = Platform.objects.create(sort_order=max_o + 1, **validated_data)
        if tags:
            obj.platform_tags.set(tags)
        return obj

    def update(self, instance, validated_data):
        tags = validated_data.pop("platform_tags", None)
        for key, val in validated_data.items():
            setattr(instance, key, val)
        instance.save()
        if tags is not None:
            instance.platform_tags.set(tags)
        return instance


class AdminBusinessWriteSerializer(serializers.ModelSerializer):
    class Meta:
        model = Business
        fields = ("id", "platform", "name", "status")


class AdminSkuWriteSerializer(serializers.ModelSerializer):
    class Meta:
        model = SKU
        fields = ("id", "business", "name", "status")


class AdminPlatformReorderSerializer(serializers.Serializer):
    order = serializers.ListField(child=serializers.IntegerField(min_value=1), allow_empty=False)
