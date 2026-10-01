from django import forms
from django.contrib.auth import get_user_model
from django.forms import inlineformset_factory
from .roles import (
    ensure_boss_group,
    ensure_ceo_group,
    ensure_guest_group,
    is_boss,
    is_ceo,
    is_guest,
)
from django.core.exceptions import ValidationError
from django.core.validators import URLValidator
from django.utils import timezone

from .models import (
    Business,
    ChannelTagPool,
    HallBlock,
    PAYMENT_CHANNELS,
    PaymentTutorial,
    PhrasePool,
    Platform,
    PlatformAccount,
    PlatformTagPool,
    PaymentRecord,
    QuickPhrase,
    SharedAppleIDPage,
    PictCartPage,
    FanboxStatsPage,
    ServiceMonitorPage,
    SKU,
    SKUPriceItem,
    SKUImage,
    SubscriptionPlatformOption,
    SubscriptionReminder,
    Tag,
    TutorialPool,
    UsdProxyPriceTier,
)


def normalize_url_value(value: str) -> str:
    value = (value or "").strip()
    if not value:
        return value
    if "://" not in value:
        return f"https://{value}"
    return value


class PlatformForm(forms.ModelForm):
    url = forms.CharField(required=False)

    class Meta:
        model = Platform
        fields = ("name", "status", "url", "note", "platform_tags")
        widgets = {
            "url": forms.TextInput(attrs={"placeholder": "例如：example.com"}),
            "note": forms.Textarea(attrs={"rows": 3}),
            "platform_tags": forms.CheckboxSelectMultiple(),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["platform_tags"].queryset = Tag.objects.filter(type=Tag.TYPE_PLATFORM).order_by("order", "id")

    def clean_url(self):
        value = normalize_url_value(self.cleaned_data.get("url"))
        if not value:
            return value
        try:
            URLValidator()(value)
        except ValidationError as exc:
            raise ValidationError("请输入网址。") from exc
        return value


class BusinessForm(forms.ModelForm):
    class Meta:
        model = Business
        fields = ("platform", "name", "status")


class SKUForm(forms.ModelForm):
    class Meta:
        model = SKU
        fields = ("business", "name", "status", "channel_tags", "price")
        widgets = {
            "channel_tags": forms.CheckboxSelectMultiple(),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["channel_tags"].queryset = Tag.objects.filter(type=Tag.TYPE_CHANNEL).order_by("order", "id")


class QuickPhraseForm(forms.ModelForm):
    class Meta:
        model = QuickPhrase
        fields = ("sku", "content", "order")
        widgets = {"content": forms.Textarea(attrs={"rows": 4})}


class HallBlockForm(forms.ModelForm):
    class Meta:
        model = HallBlock
        fields = ("title", "body", "sort_order", "is_pinned")
        widgets = {
            "body": forms.Textarea(attrs={"rows": 8}),
            "is_pinned": forms.Select(
                choices=[
                    (True, "置顶"),
                    (False, "普通"),
                ]
            ),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["is_pinned"].required = True
        self.fields["is_pinned"].help_text = "置顶板块在职员端大厅最前展示，同置顶内仍按排序数字。"
        if not getattr(self.instance, "pk", None):
            self.fields["is_pinned"].initial = False

    def save(self, commit=True):
        obj = super().save(commit=False)
        obj.is_active = True
        if commit:
            obj.save()
        return obj


class PlatformTagPoolForm(forms.ModelForm):
    class Meta:
        model = PlatformTagPool
        fields = ("name", "order")
        labels = {"name": "名称", "order": "排序"}

    def save(self, commit=True):
        obj = super().save(commit=False)
        obj.type = Tag.TYPE_PLATFORM
        if commit:
            obj.save()
        return obj


class ChannelTagPoolForm(forms.ModelForm):
    class Meta:
        model = ChannelTagPool
        fields = ("name", "order")
        labels = {"name": "名称", "order": "排序"}

    def save(self, commit=True):
        obj = super().save(commit=False)
        obj.type = Tag.TYPE_CHANNEL
        if commit:
            obj.save()
        return obj


class PlatformTagPoolQuickForm(forms.ModelForm):
    """平台编辑弹窗：仅填名称。"""

    class Meta:
        model = PlatformTagPool
        fields = ("name",)
        labels = {"name": "标签名称"}

    def save(self, commit=True):
        obj = super().save(commit=False)
        obj.type = Tag.TYPE_PLATFORM
        if commit:
            obj.save()
        return obj


class ChannelTagPoolQuickForm(forms.ModelForm):
    """SKU 编辑器弹窗：仅填名称。"""

    class Meta:
        model = ChannelTagPool
        fields = ("name",)
        labels = {"name": "渠道名称"}

    def save(self, commit=True):
        obj = super().save(commit=False)
        obj.type = Tag.TYPE_CHANNEL
        if commit:
            obj.save()
        return obj


class PlatformTagQuickForm(forms.ModelForm):
    """@deprecated 使用 PlatformTagPoolForm"""

    class Meta:
        model = Tag
        fields = ("name", "order")
        labels = {"name": "名称", "order": "排序"}

    def save(self, commit=True):
        obj = super().save(commit=False)
        obj.type = Tag.TYPE_PLATFORM
        if commit:
            obj.save()
        return obj


class ChannelTagQuickForm(forms.ModelForm):
    """@deprecated 使用 ChannelTagPoolForm"""

    class Meta:
        model = Tag
        fields = ("name", "order")
        labels = {"name": "名称", "order": "排序"}

    def save(self, commit=True):
        obj = super().save(commit=False)
        obj.type = Tag.TYPE_CHANNEL
        if commit:
            obj.save()
        return obj


class PlatformAccountForm(forms.ModelForm):
    url = forms.CharField(required=False)

    class Meta:
        model = PlatformAccount
        fields = ("name", "account", "password", "url", "note")
        widgets = {
            "url": forms.TextInput(attrs={"placeholder": "例如：example.com"}),
            "note": forms.Textarea(attrs={"rows": 3}),
        }

    def clean_url(self):
        value = normalize_url_value(self.cleaned_data.get("url"))
        if not value:
            return value
        try:
            URLValidator()(value)
        except ValidationError as exc:
            raise ValidationError("请输入网址。") from exc
        return value


class StaffUserForm(forms.ModelForm):
    ROLE_EMPLOYEE = "employee"
    ROLE_ADMIN = "admin"
    ROLE_BOSS = "boss"
    ROLE_CEO = "ceo"
    ROLE_GUEST = "guest"
    ROLE_CHOICES = (
        (ROLE_EMPLOYEE, "员工"),
        (ROLE_CEO, "CEO"),
        (ROLE_ADMIN, "管理员"),
        (ROLE_BOSS, "老板"),
        (ROLE_GUEST, "游客/访客"),
    )

    role = forms.ChoiceField(label="权限等级", choices=ROLE_CHOICES, initial=ROLE_EMPLOYEE)
    password = forms.CharField(
        label="密码",
        required=False,
        widget=forms.PasswordInput(
            attrs={
                "autocomplete": "new-password",
                "placeholder": "留空表示不修改",
            }
        ),
    )

    class Meta:
        model = get_user_model()
        fields = ("username", "is_active")
        labels = {
            "username": "用户名",
            "is_active": "启用账号",
        }

    def __init__(self, *args, require_password=False, **kwargs):
        self.require_password = require_password
        super().__init__(*args, **kwargs)
        self.fields["username"].help_text = ""
        if self.instance and self.instance.pk:
            if self.instance.is_superuser:
                self.fields["role"].initial = self.ROLE_ADMIN
            elif is_boss(self.instance):
                self.fields["role"].initial = self.ROLE_BOSS
            elif is_ceo(self.instance):
                self.fields["role"].initial = self.ROLE_CEO
            elif is_guest(self.instance):
                self.fields["role"].initial = self.ROLE_GUEST
            else:
                self.fields["role"].initial = self.ROLE_EMPLOYEE
            self.fields["password"].help_text = "留空表示不修改密码。"
            self.fields["password"].initial = ""
        else:
            self.fields["password"].help_text = "请设置登录密码。"
        self.fields["is_active"].initial = True if not (self.instance and self.instance.pk) else self.instance.is_active

    def clean_password(self):
        pwd = (self.cleaned_data.get("password") or "").strip()
        if self.require_password and not pwd:
            raise ValidationError("请设置密码。")
        if pwd and (pwd.startswith("pbkdf2_") or pwd.startswith("argon2") or pwd.startswith("bcrypt")):
            return ""
        return pwd

    def save(self, commit=True):
        obj = super().save(commit=False)
        role = self.cleaned_data.get("role")
        obj.is_staff = True
        obj.is_superuser = role == self.ROLE_ADMIN
        if commit:
            obj.save()
            boss_group = ensure_boss_group()
            ceo_group = ensure_ceo_group()
            guest_group = ensure_guest_group()
            if role == self.ROLE_BOSS:
                obj.groups.add(boss_group)
                obj.groups.remove(ceo_group)
                obj.groups.remove(guest_group)
            elif role == self.ROLE_CEO:
                obj.groups.add(ceo_group)
                obj.groups.remove(boss_group)
                obj.groups.remove(guest_group)
            elif role == self.ROLE_GUEST:
                obj.groups.add(guest_group)
                obj.groups.remove(boss_group)
                obj.groups.remove(ceo_group)
            else:
                obj.groups.remove(boss_group)
                obj.groups.remove(ceo_group)
                obj.groups.remove(guest_group)
        pwd = (self.cleaned_data.get("password") or "").strip()
        if pwd:
            obj.set_password(pwd)
            if commit:
                obj.save(update_fields=["password"])
        return obj


class UsdProxyPriceTierForm(forms.ModelForm):
    class Meta:
        model = UsdProxyPriceTier
        fields = ("usd_range", "rate_percent")
        labels = {
            "usd_range": "美金区间",
            "rate_percent": "费率（%）",
        }
        widgets = {
            "usd_range": forms.TextInput(attrs={"placeholder": "例如：1-5美金"}),
            "rate_percent": forms.NumberInput(attrs={"step": "0.01", "min": "0"}),
        }


class PaymentRecordFilterForm(forms.Form):
    user = forms.ModelChoiceField(
        label="人员",
        queryset=get_user_model().objects.none(),
        required=False,
        empty_label="全部人员",
    )
    channel = forms.ChoiceField(label="渠道", required=False)
    date_from = forms.DateField(
        label="",
        required=False,
        widget=forms.HiddenInput(),
    )
    date_to = forms.DateField(
        label="",
        required=False,
        widget=forms.HiddenInput(),
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        User = get_user_model()
        self.fields["user"].queryset = User.objects.filter(is_staff=True).order_by("username")
        self.fields["channel"].choices = [("", "全部渠道")] + list(PAYMENT_CHANNELS)


class PlatformListFilterForm(forms.Form):
    platform = forms.ModelChoiceField(
        label="平台",
        queryset=Platform.objects.none(),
        required=False,
        empty_label="全部平台",
    )
    q = forms.CharField(label="搜索", required=False)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["platform"].queryset = Platform.objects.all().order_by("sort_order", "id")
        self.fields["q"].widget.attrs.update({"placeholder": "搜索平台名称/网址/备注/标签"})


class BusinessListFilterForm(forms.Form):
    platform = forms.ModelChoiceField(
        label="平台",
        queryset=Platform.objects.none(),
        required=False,
        empty_label="全部平台",
    )
    q = forms.CharField(label="搜索", required=False)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["platform"].queryset = Platform.objects.all().order_by("sort_order", "id")
        self.fields["q"].widget.attrs.update({"placeholder": "搜索业务名/描述"})


class SKUListFilterForm(forms.Form):
    platform = forms.ModelChoiceField(
        label="平台",
        queryset=Platform.objects.none(),
        required=False,
        empty_label="全部平台",
    )
    q = forms.CharField(label="搜索", required=False)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["platform"].queryset = Platform.objects.all().order_by("sort_order", "id")
        self.fields["q"].widget.attrs.update({"placeholder": "搜索SKU/业务/备注/教程"})

class PaymentRecordAdminForm(forms.ModelForm):
    class Meta:
        model = PaymentRecord
        fields = ("user", "channel", "order_count", "amount", "note", "record_date")
        labels = {
            "user": "填写人",
            "channel": "收款渠道",
            "order_count": "订单数",
            "amount": "金额",
            "note": "备注",
            "record_date": "订单时间",
        }
        widgets = {
            "note": forms.Textarea(attrs={"rows": 3}),
            "record_date": forms.DateInput(
                format="%Y-%m-%d",
                attrs={"type": "date"},
            ),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        User = get_user_model()
        self.fields["user"].queryset = User.objects.filter(is_staff=True, is_active=True).order_by("username")
        self.fields["record_date"].input_formats = ["%Y-%m-%d"]
        if self.instance.pk and self.instance.record_date:
            self.initial.setdefault("record_date", self.instance.record_date)

    def clean_record_date(self):
        value = self.cleaned_data.get("record_date")
        if value:
            return value
        if self.instance.pk and self.instance.record_date:
            return self.instance.record_date
        return timezone.localdate()

    def save(self, commit=True):
        instance = super().save(commit=False)
        if instance._state.adding:
            now = timezone.now()
            if not instance.created_at:
                instance.created_at = now
            if not instance.record_date:
                instance.record_date = timezone.localdate(instance.created_at)
        if commit:
            instance.save()
        return instance


class PaymentTutorialForm(forms.ModelForm):
    detail_url = forms.CharField(
        label="详情链接",
        widget=forms.TextInput(attrs={"placeholder": "例如：example.com/help"}),
    )

    class Meta:
        model = PaymentTutorial
        fields = ("name", "detail_url")

    def clean_detail_url(self):
        value = normalize_url_value(self.cleaned_data.get("detail_url"))
        if not value:
            raise ValidationError("请输入详情链接。")
        try:
            URLValidator()(value)
        except ValidationError as exc:
            raise ValidationError("请输入有效的链接。") from exc
        return value


class TutorialPoolForm(forms.ModelForm):
    detail_url = forms.CharField(
        label="详情链接",
        widget=forms.TextInput(attrs={"placeholder": "例如：example.com/guide/fanbox"}),
    )

    class Meta:
        model = TutorialPool
        fields = ("name", "detail_url")

    def clean_detail_url(self):
        value = normalize_url_value(self.cleaned_data.get("detail_url"))
        if not value:
            raise ValidationError("请输入详情链接。")
        try:
            URLValidator()(value)
        except ValidationError as exc:
            raise ValidationError("请输入有效的链接。") from exc
        return value


class PhrasePoolForm(forms.ModelForm):
    class Meta:
        model = PhrasePool
        fields = ("name", "content")
        widgets = {"content": forms.Textarea(attrs={"rows": 6})}


class SharedAppleIDPageForm(forms.ModelForm):
    share_url = forms.CharField(
        label="分享页链接",
        widget=forms.TextInput(attrs={"placeholder": "例如：example.com/share/apple-id"}),
    )

    class Meta:
        model = SharedAppleIDPage
        fields = ("name", "share_url", "is_active")

    def clean_share_url(self):
        value = normalize_url_value(self.cleaned_data.get("share_url"))
        if not value:
            raise ValidationError("请输入分享页链接。")
        try:
            URLValidator()(value)
        except ValidationError as exc:
            raise ValidationError("请输入有效的链接。") from exc
        return value


class PictCartPageForm(forms.ModelForm):
    share_url = forms.CharField(
        label="页面链接",
        widget=forms.TextInput(attrs={"placeholder": "例如：https://pict.example.com/cart"}),
    )

    class Meta:
        model = PictCartPage
        fields = ("name", "share_url", "is_active")

    def clean_share_url(self):
        value = normalize_url_value(self.cleaned_data.get("share_url"))
        if not value:
            raise ValidationError("请输入页面链接。")
        try:
            URLValidator()(value)
        except ValidationError as exc:
            raise ValidationError("请输入有效的链接。") from exc
        return value


class FanboxStatsPageForm(forms.ModelForm):
    share_url = forms.CharField(
        label="页面链接",
        widget=forms.TextInput(attrs={"placeholder": "例如：https://fanbox.xinhuo.pro/"}),
    )

    class Meta:
        model = FanboxStatsPage
        fields = ("name", "share_url", "is_active")

    def clean_share_url(self):
        value = normalize_url_value(self.cleaned_data.get("share_url"))
        if not value:
            raise ValidationError("请输入页面链接。")
        try:
            URLValidator()(value)
        except ValidationError as exc:
            raise ValidationError("请输入有效的链接。") from exc
        return value


class ServiceMonitorPageForm(forms.ModelForm):
    share_url = forms.CharField(
        label="页面链接",
        widget=forms.TextInput(attrs={"placeholder": "例如：http://127.0.0.1:3001/"}),
    )

    class Meta:
        model = ServiceMonitorPage
        fields = ("name", "share_url", "is_active")

    def clean_share_url(self):
        value = normalize_url_value(self.cleaned_data.get("share_url"))
        if not value:
            raise ValidationError("请输入页面链接。")
        try:
            URLValidator()(value)
        except ValidationError as exc:
            raise ValidationError("请输入有效的链接。") from exc
        return value


class SubscriptionReminderFilterForm(forms.Form):
    q = forms.CharField(label="搜索", required=False)
    user = forms.ModelChoiceField(
        label="负责人",
        queryset=get_user_model().objects.none(),
        required=False,
        empty_label="全部员工",
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        User = get_user_model()
        self.fields["user"].queryset = User.objects.filter(is_staff=True, is_active=True).order_by("username")
        self.fields["q"].widget.attrs.update({"placeholder": "微信名/微信号/订阅平台/备注"})


class SubscriptionReminderAdminForm(forms.ModelForm):
    next_reminder_at = forms.DateField(
        label="下次提醒日期",
        widget=forms.DateInput(attrs={"type": "date"}),
        input_formats=["%Y-%m-%d"],
    )
    platform_display = forms.CharField(
        label="订阅平台",
        max_length=200,
        widget=forms.TextInput(
            attrs={
                "placeholder": "输入或从提示中选择已有平台",
                "list": "bb-subscription-platform-datalist",
                "autocomplete": "off",
            }
        ),
        help_text="与历史平台名称提示同步；直接输入新名称保存后会自动加入列表。",
    )

    class Meta:
        model = SubscriptionReminder
        fields = ("user", "wechat_label", "platform_display", "remark", "next_reminder_at")
        labels = {
            "user": "负责人",
            "wechat_label": "微信名或微信号",
            "remark": "备注",
            "next_reminder_at": "下次提醒日期",
        }
        widgets = {
            "wechat_label": forms.TextInput(attrs={"placeholder": "客户微信备注"}),
            "remark": forms.Textarea(attrs={"rows": 2, "placeholder": "选填", "maxlength": 500}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        User = get_user_model()
        self.fields["user"].queryset = User.objects.filter(is_staff=True, is_active=True).order_by("username")
        if self.instance.pk and self.instance.next_reminder_at:
            self.initial.setdefault("next_reminder_at", self.instance.next_reminder_at.isoformat())
        if self.instance.pk and getattr(self.instance, "platform_option_id", None):
            po = getattr(self.instance, "platform_option", None)
            if po is not None:
                self.initial.setdefault("platform_display", po.name)

    def clean(self):
        cleaned = super().clean()
        name = (cleaned.get("platform_display") or "").strip()
        if not name:
            self.add_error("platform_display", "请填写或选择订阅平台。")
            return cleaned
        opt, _ = SubscriptionPlatformOption.objects.get_or_create(name=name, defaults={"sort_order": 0})
        cleaned["_resolved_platform_option"] = opt
        return cleaned

    def save(self, commit=True):
        instance = super().save(commit=False)
        instance.platform_option = self.cleaned_data["_resolved_platform_option"]
        if commit:
            instance.save()
            self.save_m2m()
        return instance


class SKUPriceItemForm(forms.ModelForm):
    class Meta:
        model = SKUPriceItem
        fields = ("label", "rmb_amount", "notice", "sort_order")
        widgets = {
            "label": forms.TextInput(attrs={"placeholder": "档位名称（可选）"}),
            "rmb_amount": forms.NumberInput(attrs={"step": "0.01", "min": "0"}),
            "notice": forms.Textarea(attrs={"rows": 2, "placeholder": "单条注意事项（可选）"}),
            "sort_order": forms.NumberInput(attrs={"min": "0"}),
        }


class QuickPhraseEditorForm(forms.ModelForm):
    class Meta:
        model = QuickPhrase
        fields = ("content", "order")
        widgets = {
            "content": forms.Textarea(attrs={"rows": 2}),
            "order": forms.NumberInput(attrs={"min": "0"}),
        }


SKUPriceItemFormSet = inlineformset_factory(
    SKU,
    SKUPriceItem,
    form=SKUPriceItemForm,
    extra=2,
    can_delete=True,
)

QuickPhraseEditorFormSet = inlineformset_factory(
    SKU,
    QuickPhrase,
    form=QuickPhraseEditorForm,
    extra=0,
    can_delete=True,
)


class SKUEditorForm(forms.ModelForm):
    tutorial_pool = forms.ModelMultipleChoiceField(
        queryset=TutorialPool.objects.all(),
        required=False,
        widget=forms.CheckboxSelectMultiple,
        label="教程",
    )

    class Meta:
        model = SKU
        fields = (
            "business",
            "name",
            "status",
            "precaution",
            "price_type",
            "price_notice",
            "channel_tags",
        )
        widgets = {
            "precaution": forms.Textarea(attrs={"rows": 4, "placeholder": "职员端 SKU 卡片上显示的注意事项"}),
            "price_notice": forms.Textarea(attrs={"rows": 3, "placeholder": "价格弹层内整组说明（可选）"}),
            "channel_tags": forms.CheckboxSelectMultiple(),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["channel_tags"].queryset = Tag.objects.filter(type=Tag.TYPE_CHANNEL).order_by("order", "id")
        self.fields["tutorial_pool"].queryset = TutorialPool.objects.all().order_by("sort_order", "id")
        if self.instance.pk:
            names = [n.strip() for n in (self.instance.tutorial_text or "").split(" / ") if n.strip()]
            if names:
                self.initial["tutorial_pool"] = TutorialPool.objects.filter(name__in=names)

    def save(self, commit=True):
        sku = super().save(commit=False)
        pools = self.cleaned_data.get("tutorial_pool") or []
        sku.tutorial_text = " / ".join(p.name for p in pools)
        if commit:
            sku.save()
            self.save_m2m()
        return sku

