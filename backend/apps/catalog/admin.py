from django.contrib import admin

from .models import (
    Business,
    ChannelTagPool,
    HallBlock,
    PaymentRecord,
    PaymentTutorial,
    PhrasePool,
    Platform,
    PlatformAccount,
    PlatformTagPool,
    QuickPhrase,
    SharedAppleIDPage,
    PictCartPage,
    FanboxStatsPage,
    ServiceMonitorPage,
    MaterialRenewal,
    CommonCard,
    CommonAccount,
    SKU,
    SubscriptionPlatformOption,
    SubscriptionReminder,
    SubscriptionReminderWecomDailyDigest,
    SubscriptionReminderWecomNotify,
    Tag,
    TutorialPool,
    UsdProxyPriceTier,
)


@admin.register(Tag)
class TagAdmin(admin.ModelAdmin):
    list_display = ("name", "type", "order")
    list_filter = ("type",)
    ordering = ("type", "order", "id")


class BusinessInline(admin.TabularInline):
    model = Business
    extra = 0
    fields = ("name", "status")


@admin.register(Platform)
class PlatformAdmin(admin.ModelAdmin):
    list_display = ("name", "status", "sort_order", "url")
    inlines = [BusinessInline]
    filter_horizontal = ("platform_tags",)


class QuickPhraseInline(admin.TabularInline):
    model = QuickPhrase
    extra = 0


@admin.register(SKU)
class SKUAdmin(admin.ModelAdmin):
    list_display = ("name", "business", "status", "price")
    list_filter = ("status", "business")
    filter_horizontal = ("channel_tags",)
    inlines = [QuickPhraseInline]


@admin.register(Business)
class BusinessAdmin(admin.ModelAdmin):
    list_display = ("name", "platform", "status")


@admin.register(QuickPhrase)
class QuickPhraseAdmin(admin.ModelAdmin):
    list_display = ("sku", "order", "content")


@admin.register(HallBlock)
class HallBlockAdmin(admin.ModelAdmin):
    list_display = ("title", "is_pinned", "sort_order", "is_active", "updated_at")


@admin.register(PaymentRecord)
class PaymentRecordAdmin(admin.ModelAdmin):
    list_display = ("channel", "order_count", "amount", "user", "record_date", "created_at")
    list_filter = ("channel", "record_date")


@admin.register(PaymentTutorial)
class PaymentTutorialAdmin(admin.ModelAdmin):
    list_display = ("name", "sort_order", "detail_url")


@admin.register(TutorialPool)
class TutorialPoolAdmin(admin.ModelAdmin):
    list_display = ("name", "sort_order", "detail_url")


@admin.register(UsdProxyPriceTier)
class UsdProxyPriceTierAdmin(admin.ModelAdmin):
    list_display = ("usd_range", "rate_percent", "sort_order")
    ordering = ("sort_order", "id")


@admin.register(PlatformTagPool)
class PlatformTagPoolAdmin(admin.ModelAdmin):
    list_display = ("name", "order")
    search_fields = ("name",)


@admin.register(ChannelTagPool)
class ChannelTagPoolAdmin(admin.ModelAdmin):
    list_display = ("name", "order")
    search_fields = ("name",)


@admin.register(PhrasePool)
class PhrasePoolAdmin(admin.ModelAdmin):
    list_display = ("name", "sort_order", "content")
    search_fields = ("name", "content")


@admin.register(PlatformAccount)
class PlatformAccountAdmin(admin.ModelAdmin):
    list_display = ("name", "sort_order", "account", "url")


@admin.register(SharedAppleIDPage)
class SharedAppleIDPageAdmin(admin.ModelAdmin):
    list_display = ("name", "sort_order", "is_active", "share_url")
    list_filter = ("is_active",)


@admin.register(PictCartPage)
class PictCartPageAdmin(admin.ModelAdmin):
    list_display = ("name", "sort_order", "is_active", "share_url")
    list_filter = ("is_active",)


@admin.register(FanboxStatsPage)
class FanboxStatsPageAdmin(admin.ModelAdmin):
    list_display = ("name", "sort_order", "is_active", "share_url")
    list_filter = ("is_active",)


@admin.register(ServiceMonitorPage)
class ServiceMonitorPageAdmin(admin.ModelAdmin):
    list_display = ("name", "sort_order", "is_active", "share_url")
    list_filter = ("is_active",)


@admin.register(MaterialRenewal)
class MaterialRenewalAdmin(admin.ModelAdmin):
    list_display = ("name", "category", "cycle_type", "next_due_at", "amount", "is_active")
    list_filter = ("cycle_type", "is_active", "category")
    search_fields = ("name", "category", "remark")


@admin.register(CommonCard)
class CommonCardAdmin(admin.ModelAdmin):
    list_display = ("platform", "card_number", "expiry", "cvv", "updated_at", "remark")
    search_fields = ("platform", "card_number", "remark")
    readonly_fields = ("created_at", "updated_at")


@admin.register(CommonAccount)
class CommonAccountAdmin(admin.ModelAdmin):
    list_display = ("platform", "account", "password", "updated_at", "remark")
    search_fields = ("platform", "account", "remark")
    readonly_fields = ("created_at", "updated_at")


@admin.register(SubscriptionPlatformOption)
class SubscriptionPlatformOptionAdmin(admin.ModelAdmin):
    list_display = ("name", "sort_order")
    search_fields = ("name",)


@admin.register(SubscriptionReminder)
class SubscriptionReminderAdmin(admin.ModelAdmin):
    list_display = (
        "wechat_label",
        "platform_option",
        "remark",
        "next_reminder_at",
        "user",
        "last_renewed_at",
        "updated_at",
    )
    list_filter = ("next_reminder_at",)
    search_fields = ("wechat_label", "remark", "platform_option__name", "user__username")
    raw_id_fields = ("user",)


@admin.register(SubscriptionReminderWecomNotify)
class SubscriptionReminderWecomNotifyAdmin(admin.ModelAdmin):
    list_display = ("reminder", "next_reminder_at", "sent_at")
    list_filter = ("sent_at",)
    ordering = ("-sent_at",)
    readonly_fields = ("reminder", "next_reminder_at", "sent_at")

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False


@admin.register(SubscriptionReminderWecomDailyDigest)
class SubscriptionReminderWecomDailyDigestAdmin(admin.ModelAdmin):
    list_display = ("user", "digest_date", "sent_at")
    list_filter = ("digest_date", "sent_at")
    ordering = ("-digest_date", "-sent_at")
    readonly_fields = ("user", "digest_date", "sent_at")

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False
