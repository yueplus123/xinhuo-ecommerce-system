from django.contrib.auth import get_user_model
from rest_framework import serializers

from backend.apps.catalog.roles import is_boss, is_ceo, is_guest
from backend.apps.catalog.models import (
    Business,
    ChannelTagPool,
    HallBlock,
    PaymentRecord,
    PhrasePool,
    Platform,
    PlatformTagPool,
    QuickPhrase,
    SKU,
    SKUPriceItem,
    Tag,
    PaymentTutorial,
    PlatformAccount,
    SharedAppleIDPage,
    PictCartPage,
    FanboxStatsPage,
    ServiceMonitorPage,
    SubscriptionPlatformOption,
    SubscriptionReminder,
    MaterialRenewal,
    CommonCard,
    CommonAccount,
    StaffLoginLog,
    TutorialPool,
    UsdProxyPriceTier,
)


class UserSerializer(serializers.ModelSerializer):
    last_login_ip = serializers.SerializerMethodField()
    avatar_url = serializers.SerializerMethodField()
    is_boss = serializers.SerializerMethodField()
    is_ceo = serializers.SerializerMethodField()
    is_guest = serializers.SerializerMethodField()

    class Meta:
        model = get_user_model()
        fields = (
            "id",
            "username",
            "is_staff",
            "is_superuser",
            "is_boss",
            "is_ceo",
            "is_guest",
            "last_login_ip",
            "avatar_url",
        )

    def get_is_boss(self, obj):
        return is_boss(obj)

    def get_is_ceo(self, obj):
        return is_ceo(obj)

    def get_is_guest(self, obj):
        return is_guest(obj)

    def get_last_login_ip(self, obj):
        m = getattr(obj, "staff_login_meta", None)
        return (m.last_login_ip if m else "") or ""

    def get_avatar_url(self, obj):
        m = getattr(obj, "staff_login_meta", None)
        if not m or not m.avatar:
            return ""
        request = self.context.get("request")
        try:
            u = m.avatar.url
            return request.build_absolute_uri(u) if request else u
        except Exception:
            return ""


class StaffLoginLogSerializer(serializers.ModelSerializer):
    class Meta:
        model = StaffLoginLog
        fields = ("id", "logged_at", "ip")


class TagSerializer(serializers.ModelSerializer):
    class Meta:
        model = Tag
        fields = ("id", "type", "name", "order")


class PlatformTagPoolSerializer(serializers.ModelSerializer):
    class Meta:
        model = PlatformTagPool
        fields = ("id", "name", "order")


class ChannelTagPoolSerializer(serializers.ModelSerializer):
    class Meta:
        model = ChannelTagPool
        fields = ("id", "name", "order")


class QuickPhraseSerializer(serializers.ModelSerializer):
    class Meta:
        model = QuickPhrase
        fields = ("id", "content", "order")


class SKUPriceItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = SKUPriceItem
        fields = ("id", "label", "rmb_amount", "notice", "sort_order")


class SKUSerializer(serializers.ModelSerializer):
    channel_tags = TagSerializer(many=True, read_only=True)
    quick_phrases = QuickPhraseSerializer(many=True, read_only=True)
    price_items = serializers.SerializerMethodField()
    price_type = serializers.SerializerMethodField()
    price_type_label = serializers.SerializerMethodField()
    status_label = serializers.CharField(source="get_status_display", read_only=True)
    image_url = serializers.SerializerMethodField()
    image_urls = serializers.SerializerMethodField()

    class Meta:
        model = SKU
        fields = (
            "id",
            "business",
            "name",
            "status",
            "status_label",
            "channel_tags",
            "price",
            "price_type",
            "price_type_label",
            "price_notice",
            "precaution",
            "price_items",
            "image_url",
            "image_urls",
            "tutorial_text",
            "quick_phrases",
        )

    def _media_url(self, url):
        if not url:
            return ""
        request = self.context.get("request")
        try:
            if request:
                return request.build_absolute_uri(url)
            return url
        except Exception:
            return ""

    def get_image_urls(self, obj):
        urls = []
        if obj.image:
            u = self._media_url(obj.image.url)
            if u:
                urls.append(u)
        for row in obj.member_images.all():
            u = self._media_url(row.image.url)
            if u and u not in urls:
                urls.append(u)
        return urls

    def get_image_url(self, obj):
        urls = self.get_image_urls(obj)
        return urls[0] if urls else ""

    def _resolved_price_type(self, obj):
        if obj.price_type:
            return obj.price_type
        if obj.price is not None:
            return SKU.PRICE_TYPE_CNY_SINGLE
        return ""

    def get_price_type(self, obj):
        return self._resolved_price_type(obj)

    def get_price_type_label(self, obj):
        price_type = self._resolved_price_type(obj)
        if not price_type:
            return ""
        return dict(SKU.PRICE_TYPE_CHOICES).get(price_type, price_type)

    def get_price_items(self, obj):
        items = list(obj.price_items.all())
        if items:
            return SKUPriceItemSerializer(items, many=True).data
        if obj.price is not None:
            return [
                {
                    "id": None,
                    "label": "",
                    "rmb_amount": obj.price,
                    "notice": "",
                    "sort_order": 0,
                }
            ]
        return []


class BusinessSerializer(serializers.ModelSerializer):
    skus = SKUSerializer(many=True, read_only=True)
    status_label = serializers.CharField(source="get_status_display", read_only=True)

    class Meta:
        model = Business
        fields = ("id", "platform", "name", "status", "status_label", "skus")


class PlatformListSerializer(serializers.ModelSerializer):
    platform_tags = TagSerializer(many=True, read_only=True)
    business_count = serializers.IntegerField(read_only=True)
    sku_count = serializers.IntegerField(read_only=True)
    sku_on_sale_count = serializers.IntegerField(read_only=True)
    sku_off_sale_count = serializers.IntegerField(read_only=True)
    sku_pending_test_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = Platform
        fields = (
            "id",
            "name",
            "status",
            "url",
            "note",
            "sort_order",
            "platform_tags",
            "business_count",
            "sku_count",
            "sku_on_sale_count",
            "sku_off_sale_count",
            "sku_pending_test_count",
        )


class PlatformDetailSerializer(serializers.ModelSerializer):
    platform_tags = TagSerializer(many=True, read_only=True)
    businesses = BusinessSerializer(many=True, read_only=True)
    status_label = serializers.CharField(source="get_status_display", read_only=True)
    website_name = serializers.CharField(source="name", read_only=True)

    class Meta:
        model = Platform
        fields = ("id", "website_name", "name", "status", "status_label", "url", "note", "platform_tags", "businesses")


class HallBlockSerializer(serializers.ModelSerializer):
    image = serializers.SerializerMethodField()

    class Meta:
        model = HallBlock
        fields = ("id", "title", "body", "image", "sort_order", "is_pinned", "is_active", "updated_at")

    def get_image(self, obj):
        img_field = obj.image
        if not img_field:
            first = obj.images.order_by("sort_order", "id").first()
            img_field = first.image if first else None
        if not img_field:
            return None
        request = self.context.get("request")
        try:
            url = img_field.url
            if request:
                return request.build_absolute_uri(url)
            return url
        except Exception:
            return None


class PaymentRecordSerializer(serializers.ModelSerializer):
    user_name = serializers.CharField(source="user.username", read_only=True)
    channel_label = serializers.CharField(source="get_channel_display", read_only=True)
    screenshot_urls = serializers.SerializerMethodField()

    def get_screenshot_urls(self, obj):
        request = self.context.get("request")
        out = []
        if obj.screenshot:
            try:
                u = obj.screenshot.url
                out.append(request.build_absolute_uri(u) if request else u)
            except Exception:
                pass
        for ei in obj.extra_images.all():
            try:
                u = ei.image.url
                out.append(request.build_absolute_uri(u) if request else u)
            except Exception:
                continue
        return out

    class Meta:
        model = PaymentRecord
        fields = (
            "id",
            "channel",
            "channel_label",
            "order_count",
            "amount",
            "note",
            "record_date",
            "created_at",
            "user",
            "user_name",
            "screenshot_urls",
        )
        read_only_fields = ("user", "record_date", "created_at")


class PaymentTutorialSerializer(serializers.ModelSerializer):
    class Meta:
        model = PaymentTutorial
        fields = ("id", "name", "detail_url", "sort_order")


class TutorialPoolSerializer(serializers.ModelSerializer):
    class Meta:
        model = TutorialPool
        fields = ("id", "name", "detail_url", "sort_order")


class UsdProxyPriceTierSerializer(serializers.ModelSerializer):
    class Meta:
        model = UsdProxyPriceTier
        fields = ("id", "usd_range", "rate_percent", "sort_order")


class PhrasePoolSerializer(serializers.ModelSerializer):
    class Meta:
        model = PhrasePool
        fields = ("id", "name", "content", "sort_order")


class PlatformAccountSerializer(serializers.ModelSerializer):
    class Meta:
        model = PlatformAccount
        fields = ("id", "name", "account", "password", "url", "note", "sort_order")


class SharedAppleIDPageSerializer(serializers.ModelSerializer):
    class Meta:
        model = SharedAppleIDPage
        fields = ("id", "name", "share_url", "sort_order", "is_active")


class PictCartPageSerializer(serializers.ModelSerializer):
    class Meta:
        model = PictCartPage
        fields = ("id", "name", "share_url", "sort_order", "is_active")


class FanboxStatsPageSerializer(serializers.ModelSerializer):
    class Meta:
        model = FanboxStatsPage
        fields = ("id", "name", "share_url", "sort_order", "is_active")


class ServiceMonitorPageSerializer(serializers.ModelSerializer):
    class Meta:
        model = ServiceMonitorPage
        fields = ("id", "name", "share_url", "sort_order", "is_active")


class SubscriptionPlatformOptionSerializer(serializers.ModelSerializer):
    def validate_name(self, value):
        v = (value or "").strip()
        if not v:
            raise serializers.ValidationError("请填写平台名称。")
        qs = SubscriptionPlatformOption.objects.filter(name=v)
        if self.instance is not None:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise serializers.ValidationError("该名称已存在。")
        return v

    class Meta:
        model = SubscriptionPlatformOption
        fields = ("id", "name", "sort_order")


class SubscriptionReminderSerializer(serializers.ModelSerializer):
    owner_username = serializers.CharField(source="user.username", read_only=True)
    platform_name = serializers.CharField(source="platform_option.name", read_only=True)
    platform_input = serializers.CharField(write_only=True, required=False, allow_blank=True)
    # 创建时可仅传 platform_input；字段级校验会在 validate() 解析后再写入 platform_option。
    platform_option = serializers.PrimaryKeyRelatedField(
        queryset=SubscriptionPlatformOption.objects.all(),
        required=False,
        allow_null=True,
    )

    class Meta:
        model = SubscriptionReminder
        fields = (
            "id",
            "wechat_label",
            "remark",
            "platform_option",
            "platform_input",
            "platform_name",
            "next_reminder_at",
            "last_renewed_at",
            "created_at",
            "updated_at",
            "owner_username",
        )
        read_only_fields = ("last_renewed_at", "created_at", "updated_at", "owner_username", "platform_name")

    def validate(self, attrs):
        pin_raw = attrs.pop("platform_input", None)
        pin = (pin_raw or "").strip() if isinstance(pin_raw, str) else ""
        has_po = "platform_option" in attrs

        if pin:
            opt, _ = SubscriptionPlatformOption.objects.get_or_create(name=pin, defaults={"sort_order": 0})
            attrs["platform_option"] = opt
        elif has_po:
            if attrs.get("platform_option") is None:
                raise serializers.ValidationError({"platform_option": "订阅平台不能为空。"})
        elif self.instance is None:
            raise serializers.ValidationError({"platform_input": "请填写或选择订阅平台。"})
        return attrs


class MaterialRenewalSerializer(serializers.ModelSerializer):
    cycle_type_label = serializers.CharField(source="get_cycle_type_display", read_only=True)

    class Meta:
        model = MaterialRenewal
        fields = (
            "id",
            "name",
            "category",
            "amount",
            "currency",
            "cycle_type",
            "cycle_type_label",
            "cycle_days",
            "next_due_at",
            "last_renewed_at",
            "remark",
            "is_active",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("last_renewed_at", "created_at", "updated_at", "cycle_type_label")

    def validate(self, attrs):
        cycle = attrs.get("cycle_type")
        if cycle is None and self.instance is not None:
            cycle = self.instance.cycle_type
        days = attrs.get("cycle_days")
        if "cycle_days" not in attrs and self.instance is not None:
            days = self.instance.cycle_days
        if cycle == MaterialRenewal.CYCLE_DAYS:
            if not days or int(days) < 1:
                raise serializers.ValidationError({"cycle_days": "自定义天数请填写 ≥ 1 的整数。"})
        return attrs


class CommonCardSerializer(serializers.ModelSerializer):
    class Meta:
        model = CommonCard
        fields = (
            "id",
            "platform",
            "card_number",
            "expiry",
            "cvv",
            "remark",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("created_at", "updated_at")

    def validate_platform(self, value):
        v = (value or "").strip()
        if not v:
            raise serializers.ValidationError("请填写平台。")
        return v[:100]

    def validate_card_number(self, value):
        v = (value or "").strip()
        if not v:
            raise serializers.ValidationError("请填写卡号。")
        return v[:64]

    def validate_expiry(self, value):
        v = (value or "").strip()
        if not v:
            raise serializers.ValidationError("请填写有效期。")
        return v[:16]

    def validate_cvv(self, value):
        v = (value or "").strip()
        if not v:
            raise serializers.ValidationError("请填写安全码。")
        return v[:8]

    def validate_remark(self, value):
        return (value or "").strip()[:500]


class CommonAccountSerializer(serializers.ModelSerializer):
    class Meta:
        model = CommonAccount
        fields = (
            "id",
            "platform",
            "account",
            "password",
            "remark",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("created_at", "updated_at")

    def validate_platform(self, value):
        v = (value or "").strip()
        if not v:
            raise serializers.ValidationError("请填写平台。")
        return v[:100]

    def validate_account(self, value):
        v = (value or "").strip()
        if not v:
            raise serializers.ValidationError("请填写账号。")
        return v[:200]

    def validate_password(self, value):
        v = (value or "").strip()
        if not v:
            raise serializers.ValidationError("请填写密码。")
        return v[:500]

    def validate_remark(self, value):
        return (value or "").strip()[:500]
