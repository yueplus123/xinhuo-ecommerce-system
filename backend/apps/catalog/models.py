"""薪火系统业务模型（与 migrations 及 SQLite 表结构对齐）。"""

from __future__ import annotations

from django.conf import settings
from django.db import models
from django.utils import timezone


PAYMENT_CHANNELS = (
    ("千牛", "淘宝"),
    ("拉卡拉", "拉卡拉"),
    ("企业微信", "企业微信"),
    ("咸鱼/得物", "闲鱼/得物"),
    ("十类收款", "十类收款"),
    ("普通微信", "普通微信"),
    ("Bilibili(B站)", "Bilibili(B站)"),
    ("其他渠道", "其他渠道"),
    ("退款项", "退款项"),
)


class Tag(models.Model):
    TYPE_PLATFORM = "platform"
    TYPE_CHANNEL = "channel"
    TYPE_CHOICES = (
        (TYPE_PLATFORM, "平台标签"),
        (TYPE_CHANNEL, "渠道标签"),
    )

    type = models.CharField(max_length=20, choices=TYPE_CHOICES)
    name = models.CharField(max_length=100)
    order = models.PositiveIntegerField(default=0, verbose_name="排序")

    class Meta:
        ordering = ["type", "order", "id"]
        unique_together = (("type", "name"),)

    def __str__(self) -> str:
        return f"{self.get_type_display()} · {self.name}"


class PlatformTagPoolManager(models.Manager):
    def get_queryset(self):
        return super().get_queryset().filter(type=Tag.TYPE_PLATFORM)


class PlatformTagPool(Tag):
    """标签池：平台编辑时从中选取。"""

    objects = PlatformTagPoolManager()

    class Meta:
        proxy = True
        verbose_name = "平台标签"
        verbose_name_plural = "标签池"


class ChannelTagPoolManager(models.Manager):
    def get_queryset(self):
        return super().get_queryset().filter(type=Tag.TYPE_CHANNEL)


class ChannelTagPool(Tag):
    """渠道池：SKU 编辑时从中选取。"""

    objects = ChannelTagPoolManager()

    class Meta:
        proxy = True
        verbose_name = "渠道标签"
        verbose_name_plural = "渠道池"


class Platform(models.Model):
    STATUS_ON_SALE = "on_sale"
    STATUS_OFF_SALE = "off_sale"
    STATUS_PENDING_TEST = "pending_test"
    STATUS_CHOICES = (
        (STATUS_ON_SALE, "在售"),
        (STATUS_OFF_SALE, "禁售"),
        (STATUS_PENDING_TEST, "待测试"),
    )

    name = models.CharField(max_length=200, verbose_name="平台名称")
    url = models.URLField(blank=True, verbose_name="网址")
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default=STATUS_ON_SALE,
        verbose_name="状态",
    )
    note = models.CharField(max_length=500, blank=True, verbose_name="备注")
    sort_order = models.PositiveIntegerField(
        default=0,
        help_text="数字越小越靠前；职员端平台列表按此顺序展示。",
        verbose_name="排序",
    )
    platform_tags = models.ManyToManyField(
        Tag,
        blank=True,
        limit_choices_to={"type": Tag.TYPE_PLATFORM},
        related_name="platforms_b",
        verbose_name="平台标签",
    )

    class Meta:
        ordering = ["sort_order", "id"]

    def __str__(self) -> str:
        return self.name


class Business(models.Model):
    STATUS_ON_SALE = "on_sale"
    STATUS_OFF_SALE = "off_sale"
    STATUS_PENDING_TEST = "pending_test"
    STATUS_CHOICES = (
        (STATUS_ON_SALE, "在售"),
        (STATUS_OFF_SALE, "禁售"),
        (STATUS_PENDING_TEST, "待测试"),
    )

    name = models.CharField(max_length=200, verbose_name="业务名称")
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default=STATUS_ON_SALE,
        verbose_name="状态",
    )
    platform = models.ForeignKey(
        Platform,
        on_delete=models.CASCADE,
        related_name="businesses",
        verbose_name="平台",
    )

    class Meta:
        ordering = ["platform_id", "id"]

    def __str__(self) -> str:
        return self.name


class SKU(models.Model):
    STATUS_ON_SALE = "on_sale"
    STATUS_OFF_SALE = "off_sale"
    STATUS_PENDING_TEST = "pending_test"
    STATUS_CHOICES = (
        (STATUS_ON_SALE, "在售"),
        (STATUS_OFF_SALE, "禁售"),
        (STATUS_PENDING_TEST, "待测试"),
    )

    PRICE_TYPE_CNY_SINGLE = "cny_single"
    PRICE_TYPE_USD_SINGLE = "usd_single"
    PRICE_TYPE_USD_TIER = "usd_tier"
    PRICE_TYPE_PACKAGE = "package"
    PRICE_TYPE_JPY_RECHARGE = "jpy_recharge"
    PRICE_TYPE_USD_PROXY = "usd_proxy"
    PRICE_TYPE_CHOICES = (
        (PRICE_TYPE_CNY_SINGLE, "单一人民币"),
        (PRICE_TYPE_USD_SINGLE, "美金（单一）"),
        (PRICE_TYPE_USD_TIER, "美金（多档）"),
        (PRICE_TYPE_PACKAGE, "套餐"),
        (PRICE_TYPE_JPY_RECHARGE, "日元充值"),
        (PRICE_TYPE_USD_PROXY, "按美金代付收费"),
    )

    name = models.CharField(max_length=200, verbose_name="SKU名称")
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default=STATUS_ON_SALE,
        verbose_name="状态",
    )
    price = models.DecimalField(max_digits=12, decimal_places=2, blank=True, null=True, verbose_name="价格")
    price_type = models.CharField(
        max_length=20,
        choices=PRICE_TYPE_CHOICES,
        blank=True,
        default="",
        verbose_name="价格类型",
    )
    price_notice = models.TextField(blank=True, verbose_name="价格整组注意事项")
    precaution = models.TextField(blank=True, verbose_name="注意事项")
    note = models.CharField(max_length=500, blank=True, verbose_name="备注")
    image = models.ImageField(upload_to="sku_screenshots/", blank=True, null=True, verbose_name="会员截图")
    tutorial_text = models.CharField(max_length=500, blank=True, verbose_name="对应教程")
    extend_config = models.CharField(max_length=500, blank=True, verbose_name="扩展配置")
    business = models.ForeignKey(
        Business,
        on_delete=models.CASCADE,
        related_name="skus",
        verbose_name="业务",
    )
    channel_tags = models.ManyToManyField(
        Tag,
        blank=True,
        limit_choices_to={"type": Tag.TYPE_CHANNEL},
        related_name="skus_b",
        verbose_name="渠道标签",
    )

    class Meta:
        ordering = ["business_id", "id"]

    def __str__(self) -> str:
        return self.name


class SKUPriceItem(models.Model):
    sku = models.ForeignKey(
        SKU,
        on_delete=models.CASCADE,
        related_name="price_items",
        verbose_name="SKU",
    )
    label = models.CharField(max_length=100, blank=True, verbose_name="档位标签")
    rmb_amount = models.DecimalField(max_digits=12, decimal_places=2, verbose_name="人民币")
    notice = models.TextField(blank=True, verbose_name="单条注意事项")
    sort_order = models.PositiveIntegerField(default=0, verbose_name="排序")

    class Meta:
        ordering = ["sort_order", "id"]
        verbose_name = "SKU价格档"
        verbose_name_plural = "SKU价格档"

    def __str__(self) -> str:
        left = (self.label or "").strip() or "—"
        return f"{left} → ¥{self.rmb_amount}"


class SKUImage(models.Model):
    sku = models.ForeignKey(
        SKU,
        on_delete=models.CASCADE,
        related_name="member_images",
        verbose_name="SKU",
    )
    image = models.ImageField(upload_to="sku_screenshots/", verbose_name="会员截图")
    sort_order = models.PositiveIntegerField(default=0, verbose_name="排序")

    class Meta:
        ordering = ["sort_order", "id"]
        verbose_name = "SKU会员截图"
        verbose_name_plural = "SKU会员截图"

    def __str__(self) -> str:
        return f"{self.sku_id} #{self.sort_order}"


class QuickPhrase(models.Model):
    content = models.TextField(verbose_name="内容")
    order = models.PositiveIntegerField(default=0, verbose_name="排序")
    sku = models.ForeignKey(
        SKU,
        on_delete=models.CASCADE,
        related_name="quick_phrases",
        verbose_name="SKU",
    )

    class Meta:
        ordering = ["order", "id"]

    def __str__(self) -> str:
        return (self.content or "")[:40]


class PhrasePool(models.Model):
    """话术池：SKU 编辑时从中选取，不再批量发送到 SKU。"""

    name = models.CharField(max_length=200, verbose_name="名称")
    content = models.TextField(verbose_name="内容")
    sort_order = models.PositiveIntegerField(
        default=0,
        help_text="数字越小越靠前。",
        verbose_name="排序",
    )

    class Meta:
        ordering = ["sort_order", "id"]
        unique_together = (("name", "content"),)
        verbose_name = "话术池"
        verbose_name_plural = "话术池"

    def __str__(self) -> str:
        return self.name


# 兼容旧代码引用
QuickPhraseTemplate = PhrasePool


class HallBlock(models.Model):
    title = models.CharField(max_length=200, verbose_name="标题")
    body = models.TextField(blank=True, verbose_name="正文")
    image = models.ImageField(upload_to="hall/", blank=True, null=True, verbose_name="配图")
    sort_order = models.PositiveIntegerField(default=0, verbose_name="排序")
    is_active = models.BooleanField(default=True, verbose_name="显示")
    is_pinned = models.BooleanField(
        default=False,
        help_text="置顶的板块在职员端大厅最前展示，同置顶内仍按排序数字。",
        verbose_name="置顶",
    )
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-is_pinned", "sort_order", "id"]

    def __str__(self) -> str:
        return self.title


class HallBlockImage(models.Model):
    block = models.ForeignKey(
        HallBlock,
        on_delete=models.CASCADE,
        related_name="images",
        verbose_name="大厅板块",
    )
    image = models.ImageField(upload_to="hall/", verbose_name="配图")
    sort_order = models.PositiveIntegerField(default=0, verbose_name="排序")

    class Meta:
        ordering = ["sort_order", "id"]
        verbose_name = "大厅配图"
        verbose_name_plural = "大厅配图"

    def __str__(self) -> str:
        return f"{self.block_id} #{self.sort_order}"


class PaymentTutorial(models.Model):
    name = models.CharField(max_length=200, verbose_name="名称")
    detail_url = models.URLField(verbose_name="详情链接")
    sort_order = models.PositiveIntegerField(
        default=0,
        help_text="数字越小越靠前；职员端支付教程列表按此顺序展示。",
        verbose_name="排序",
    )

    class Meta:
        ordering = ["sort_order", "id"]

    def __str__(self) -> str:
        return self.name


class PlatformAccount(models.Model):
    name = models.CharField(max_length=200, verbose_name="平台名称")
    account = models.CharField(max_length=200, verbose_name="账号")
    password = models.CharField(max_length=500, verbose_name="密码")
    url = models.URLField(blank=True, verbose_name="网址链接")
    note = models.CharField(max_length=500, blank=True, verbose_name="备注")
    sort_order = models.PositiveIntegerField(
        default=0,
        help_text="数字越小越靠前；职员端平台账号密码表按此顺序展示。",
        verbose_name="排序",
    )

    class Meta:
        ordering = ["sort_order", "id"]

    def __str__(self) -> str:
        return self.name


class PaymentRecord(models.Model):
    channel = models.CharField(max_length=50, choices=PAYMENT_CHANNELS, verbose_name="收款渠道")
    order_count = models.PositiveIntegerField(default=0, verbose_name="订单数")
    amount = models.DecimalField(max_digits=14, decimal_places=2, default=0, verbose_name="金额")
    screenshot = models.ImageField(upload_to="payment_screenshots/", blank=True, null=True, verbose_name="截图")
    note = models.CharField(max_length=500, blank=True, verbose_name="备注")
    record_date = models.DateField(default=timezone.localdate, verbose_name="订单时间")
    created_at = models.DateTimeField(default=timezone.now, verbose_name="填写时间")
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="payment_records_b",
        verbose_name="填写人",
    )
    # 外部系统推送幂等键（同一 event_id 只入库一次）
    external_id = models.CharField(
        max_length=128,
        blank=True,
        null=True,
        unique=True,
        db_index=True,
        verbose_name="外部事件ID",
    )

    class Meta:
        ordering = ["-created_at"]

    def save(self, *args, **kwargs):
        if self._state.adding:
            if not self.created_at:
                self.created_at = timezone.now()
            if not self.record_date:
                self.record_date = timezone.localdate(self.created_at)
        super().save(*args, **kwargs)

    def __str__(self) -> str:
        return f"{self.channel} · {self.amount}"


class PaymentBatchSubmitKey(models.Model):
    """批量收款提交幂等键：同一 batch_id 只处理一次，防止连点重复入库。"""

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="payment_batch_submit_keys",
        verbose_name="职员",
    )
    batch_id = models.CharField(max_length=64, verbose_name="提交批次 ID")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="创建时间")

    class Meta:
        verbose_name = "收款批量提交幂等键"
        verbose_name_plural = "收款批量提交幂等键"
        constraints = [
            models.UniqueConstraint(fields=("user", "batch_id"), name="uniq_payment_batch_submit_key"),
        ]


class PaymentRecordImage(models.Model):
    image = models.ImageField(upload_to="payment_screenshots/", verbose_name="截图")
    sort_order = models.PositiveSmallIntegerField(default=0, verbose_name="顺序")
    payment_record = models.ForeignKey(
        PaymentRecord,
        on_delete=models.CASCADE,
        related_name="extra_images",
        verbose_name="收款记录",
    )

    class Meta:
        ordering = ["sort_order", "id"]


class SharedAppleIDPage(models.Model):
    name = models.CharField(max_length=200, verbose_name="页面名称")
    share_url = models.URLField(verbose_name="分享页链接")
    sort_order = models.PositiveIntegerField(
        default=0,
        help_text="数字越小越靠前；职员端共享苹果ID页按此顺序展示。",
        verbose_name="排序",
    )
    is_active = models.BooleanField(default=True, verbose_name="启用")

    class Meta:
        ordering = ["sort_order", "id"]
        verbose_name = "共享苹果ID分享页"
        verbose_name_plural = "共享苹果ID分享页"

    def __str__(self) -> str:
        return self.name


class PictCartPage(models.Model):
    """pict加购物车：后台配置外链，前端 iframe 展示。"""

    name = models.CharField(max_length=200, verbose_name="页面名称")
    share_url = models.URLField(verbose_name="页面链接")
    sort_order = models.PositiveIntegerField(
        default=0,
        help_text="数字越小越靠前；职员端「pict加购物车」按此顺序展示。",
        verbose_name="排序",
    )
    is_active = models.BooleanField(default=True, verbose_name="启用")

    class Meta:
        ordering = ["sort_order", "id"]
        verbose_name = "pict加购物车页面"
        verbose_name_plural = "pict加购物车页面"

    def __str__(self) -> str:
        return self.name


class FanboxStatsPage(models.Model):
    """fanbox投稿作品统计：后台配置外链，前端 iframe 展示。"""

    name = models.CharField(max_length=200, verbose_name="页面名称")
    share_url = models.URLField(verbose_name="页面链接")
    sort_order = models.PositiveIntegerField(
        default=0,
        help_text="数字越小越靠前；职员端「fanbox投稿作品统计」按此顺序展示。",
        verbose_name="排序",
    )
    is_active = models.BooleanField(default=True, verbose_name="启用")

    class Meta:
        ordering = ["sort_order", "id"]
        verbose_name = "fanbox投稿作品统计页面"
        verbose_name_plural = "fanbox投稿作品统计页面"

    def __str__(self) -> str:
        return self.name


class ServiceMonitorPage(models.Model):
    """服务监控：嵌入 Uptime Kuma（或其它状态页），后台配置外链。"""

    name = models.CharField(max_length=200, verbose_name="页面名称")
    share_url = models.URLField(verbose_name="页面链接")
    sort_order = models.PositiveIntegerField(
        default=0,
        help_text="数字越小越靠前；职员端「服务监控」按此顺序展示。",
        verbose_name="排序",
    )
    is_active = models.BooleanField(default=True, verbose_name="启用")

    class Meta:
        ordering = ["sort_order", "id"]
        verbose_name = "服务监控页面"
        verbose_name_plural = "服务监控页面"

    def __str__(self) -> str:
        return self.name


class MaterialRenewal(models.Model):
    """公司物料续费台账（轻量，替代嵌入整站 Wallos）。"""

    CYCLE_MONTHLY = "monthly"
    CYCLE_YEARLY = "yearly"
    CYCLE_DAYS = "days"
    CYCLE_CHOICES = (
        (CYCLE_MONTHLY, "每月"),
        (CYCLE_YEARLY, "每年"),
        (CYCLE_DAYS, "自定义天数"),
    )

    name = models.CharField(max_length=200, verbose_name="物料名称")
    category = models.CharField(max_length=100, blank=True, default="", verbose_name="分类")
    amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        blank=True,
        null=True,
        verbose_name="费用",
    )
    currency = models.CharField(max_length=8, blank=True, default="CNY", verbose_name="币种")
    cycle_type = models.CharField(
        max_length=16,
        choices=CYCLE_CHOICES,
        default=CYCLE_YEARLY,
        verbose_name="续费周期",
    )
    cycle_days = models.PositiveIntegerField(
        blank=True,
        null=True,
        help_text="仅「自定义天数」时填写。",
        verbose_name="周期天数",
    )
    next_due_at = models.DateField(verbose_name="下次到期日")
    last_renewed_at = models.DateTimeField(blank=True, null=True, verbose_name="上次续费登记时间")
    remark = models.CharField(max_length=500, blank=True, default="", verbose_name="备注")
    is_active = models.BooleanField(default=True, verbose_name="启用")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="创建时间")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="更新时间")

    class Meta:
        ordering = ["next_due_at", "id"]
        verbose_name = "物料续费"
        verbose_name_plural = "物料续费"

    def __str__(self) -> str:
        return f"{self.name} · {self.next_due_at}"


class CommonCard(models.Model):
    """常用卡：共享卡号台账，职员/游客均可增删改查。"""

    platform = models.CharField(max_length=100, verbose_name="平台")
    card_number = models.CharField(max_length=64, verbose_name="卡号")
    expiry = models.CharField(max_length=16, verbose_name="有效期")
    cvv = models.CharField(max_length=8, verbose_name="安全码")
    remark = models.CharField(max_length=500, blank=True, default="", verbose_name="备注/平台")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="创建时间")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="最近更改日期")

    class Meta:
        ordering = ["-updated_at", "id"]
        verbose_name = "常用卡"
        verbose_name_plural = "常用卡"

    def __str__(self) -> str:
        return f"{self.platform} · {self.card_number}"


class CommonAccount(models.Model):
    """常用卡页内的账号密码小表，职员/游客均可增删改查。"""

    platform = models.CharField(max_length=100, verbose_name="平台")
    account = models.CharField(max_length=200, verbose_name="账号")
    password = models.CharField(max_length=500, verbose_name="密码")
    remark = models.CharField(max_length=500, blank=True, default="", verbose_name="备注")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="创建时间")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="更新时间")

    class Meta:
        ordering = ["-updated_at", "id"]
        verbose_name = "常用账号"
        verbose_name_plural = "常用账号"

    def __str__(self) -> str:
        return f"{self.platform} · {self.account}"


class TutorialPool(models.Model):
    """教程池：SKU 编辑时从中选取，不再批量发送到 SKU。"""

    name = models.CharField(max_length=200, verbose_name="名称")
    detail_url = models.URLField(verbose_name="详情链接")
    sort_order = models.PositiveIntegerField(
        default=0,
        help_text="数字越小越靠前。",
        verbose_name="排序",
    )

    class Meta:
        ordering = ["sort_order", "id"]
        verbose_name = "教程池"
        verbose_name_plural = "教程池"

    def __str__(self) -> str:
        return self.name


# 兼容旧代码引用
TutorialDeployTemplate = TutorialPool


class UsdProxyPriceTier(models.Model):
    """美金代付价格池：按美金区间对应代付费率。"""

    usd_range = models.CharField(max_length=100, verbose_name="美金区间")
    rate_percent = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        verbose_name="费率（%）",
    )
    sort_order = models.PositiveIntegerField(
        default=0,
        help_text="数字越小越靠前。",
        verbose_name="排序",
    )

    class Meta:
        ordering = ["sort_order", "id"]
        verbose_name = "美金代付价格档"
        verbose_name_plural = "美金代付价格池"

    def __str__(self) -> str:
        return f"{self.usd_range} → {self.rate_percent}%"


class StaffLoginMeta(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="staff_login_meta",
    )
    last_login_ip = models.CharField(max_length=64, blank=True, default="", verbose_name="最近登录 IP")
    avatar = models.ImageField(
        upload_to="avatars/%Y/%m/",
        blank=True,
        null=True,
        verbose_name="头像",
    )

    class Meta:
        verbose_name = "职员登录位置"
        verbose_name_plural = "职员登录位置"

    def __str__(self) -> str:
        return f"{self.user_id}"


class StaffLoginLog(models.Model):
    """职员登录日志（密码登录 / Django 会话登录）。"""

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="login_logs",
        verbose_name="职员",
    )
    ip = models.CharField(max_length=64, blank=True, default="", verbose_name="登录 IP")
    logged_at = models.DateTimeField(auto_now_add=True, db_index=True, verbose_name="登录时间")

    class Meta:
        ordering = ["-logged_at", "-id"]
        verbose_name = "职员登录日志"
        verbose_name_plural = "职员登录日志"

    def __str__(self) -> str:
        return f"{self.user_id} @ {self.logged_at}"


class StaffSalaryProfile(models.Model):
    """职员底薪（按人持久保存，工资核算页可编辑）。"""

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="salary_profile",
        verbose_name="职员",
    )
    base_salary = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0,
        verbose_name="底薪",
    )
    yinli_separate = models.BooleanField(
        default=False,
        verbose_name="引力币单独核算",
        help_text="勾选后工资条可填引力币销售额，并按下方比例提成。",
    )
    yinli_commission_rate_percent = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        null=True,
        blank=True,
        verbose_name="引力币提成比例（%）",
        help_text="如 10 表示按引力币销售额的 10% 提成；不单独核算时可留空。",
    )
    has_social_insurance = models.BooleanField(
        default=False,
        verbose_name="是否有社保",
    )
    social_insurance_amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0,
        verbose_name="社保金额",
    )

    class Meta:
        verbose_name = "职员工资档案"
        verbose_name_plural = "职员工资档案"

    def __str__(self) -> str:
        return f"{self.user_id} · 底薪 {self.base_salary}"


class StaffBaseSalaryLog(models.Model):
    """基本工资录入记录（每次保存一条，便于下方列表展示）。"""

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="base_salary_logs",
        verbose_name="职员",
    )
    base_salary = models.DecimalField(max_digits=12, decimal_places=2, verbose_name="基本工资")
    yinli_separate = models.BooleanField(default=False, verbose_name="引力币单独核算")
    yinli_commission_rate_percent = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        null=True,
        blank=True,
        verbose_name="引力币提成比例（%）",
    )
    has_social_insurance = models.BooleanField(default=False, verbose_name="是否有社保")
    social_insurance_amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0,
        verbose_name="社保金额",
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="录入时间")
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="base_salary_logs_created",
        verbose_name="录入人",
    )

    class Meta:
        ordering = ["-created_at", "-id"]
        verbose_name = "基本工资录入记录"
        verbose_name_plural = "基本工资录入记录"

    def __str__(self) -> str:
        return f"{self.user_id} · {self.base_salary} @ {self.created_at}"


class StaffSalaryMonthEntry(models.Model):
    """某月工资核算手动项（如引力币销售额）。"""

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="salary_month_entries",
        verbose_name="职员",
    )
    year = models.PositiveSmallIntegerField(verbose_name="年")
    month = models.PositiveSmallIntegerField(verbose_name="月")
    yinli_sales_amount = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        default=0,
        verbose_name="引力币销售额（手动）",
        help_text="用于按配置比例计算引力币提成。",
    )
    shilei_sales_amount = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        null=True,
        blank=True,
        verbose_name="十类销售额（手动）",
    )
    tier2_sales_amount = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        null=True,
        blank=True,
        verbose_name="二类销售额（手动）",
    )
    social_insurance_amount = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        default=0,
        verbose_name="社保金额（手动）",
    )
    refund_amount = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        null=True,
        blank=True,
        verbose_name="退款项金额（手动）",
    )

    class Meta:
        verbose_name = "月工资核算录入"
        verbose_name_plural = "月工资核算录入"
        constraints = [
            models.UniqueConstraint(fields=("user", "year", "month"), name="uniq_staff_salary_month"),
        ]

    def __str__(self) -> str:
        return f"{self.user_id} {self.year}-{self.month:02d}"


class SalarySlipShareToken(models.Model):
    """员工工资条分享链接（按人按月唯一 token，供员工自助填写销售项）。"""

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="salary_slip_share_tokens",
        verbose_name="职员",
    )
    year = models.PositiveSmallIntegerField(verbose_name="年")
    month = models.PositiveSmallIntegerField(verbose_name="月")
    token = models.CharField(max_length=64, unique=True, db_index=True, verbose_name="分享令牌")
    submitted_at = models.DateTimeField(null=True, blank=True, verbose_name="员工提交时间")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="创建时间")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="更新时间")

    class Meta:
        verbose_name = "工资条分享链接"
        verbose_name_plural = "工资条分享链接"
        indexes = [
            models.Index(fields=["user", "year", "month"], name="salary_slip_share_user_month"),
        ]

    def __str__(self) -> str:
        return f"{self.user_id} {self.year}-{self.month:02d}"


class SubscriptionPlatformOption(models.Model):
    name = models.CharField(max_length=200, unique=True, verbose_name="平台名称")
    sort_order = models.PositiveIntegerField(default=0, help_text="数字越小越靠前。", verbose_name="排序")

    class Meta:
        ordering = ["sort_order", "id"]
        verbose_name = "订阅平台选项"
        verbose_name_plural = "订阅平台选项"

    def __str__(self) -> str:
        return self.name


class SubscriptionReminder(models.Model):
    wechat_label = models.CharField(max_length=200, verbose_name="微信名或微信号")
    remark = models.CharField(max_length=500, blank=True, default="", verbose_name="备注")
    platform_option = models.ForeignKey(
        SubscriptionPlatformOption,
        on_delete=models.PROTECT,
        related_name="subscription_reminders",
        verbose_name="订阅平台",
    )
    next_reminder_at = models.DateField(
        help_text="只需年月日；到该日当天起视为需要跟进。",
        verbose_name="下次提醒日期",
    )
    last_renewed_at = models.DateTimeField(
        blank=True,
        null=True,
        help_text="职员点击「已续费，预约下次」并保存新的提醒日时自动记录，便于核对跟进节奏。",
        verbose_name="上次续费登记时间",
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="创建时间")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="更新时间")
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="subscription_reminders_b",
        verbose_name="负责人",
    )

    class Meta:
        ordering = ["next_reminder_at", "id"]
        verbose_name = "订阅到期提醒"
        verbose_name_plural = "订阅到期提醒"

    def __str__(self) -> str:
        return f"{self.wechat_label} · {self.next_reminder_at}"


class SubscriptionReminderWecomNotify(models.Model):
    """历史：按「单条提醒 × 提醒日期」去重；新推送逻辑见 SubscriptionReminderWecomDailyDigest。"""

    reminder = models.ForeignKey(
        SubscriptionReminder,
        on_delete=models.CASCADE,
        related_name="wecom_notifies",
        verbose_name="订阅提醒",
    )
    next_reminder_at = models.DateField(db_index=True, verbose_name="对应的下次提醒日期")
    sent_at = models.DateTimeField(auto_now_add=True, verbose_name="推送时间")

    class Meta:
        verbose_name = "订阅提醒企微群推送记录"
        verbose_name_plural = "订阅提醒企微群推送记录"
        constraints = [
            models.UniqueConstraint(
                fields=("reminder", "next_reminder_at"),
                name="catalog_subrem_wecom_once_per_next_at",
            ),
        ]

    def __str__(self) -> str:
        return f"notify#{self.pk}"


class SubscriptionReminderWecomDailyDigest(models.Model):
    """按「职员 × 自然日」记录当日汇总推送，避免重复发送。"""

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="subscription_wecom_daily_digests",
        verbose_name="职员",
    )
    digest_date = models.DateField(db_index=True, verbose_name="汇总日期")
    sent_at = models.DateTimeField(auto_now_add=True, verbose_name="推送时间")

    class Meta:
        verbose_name = "订阅提醒企微每日汇总"
        verbose_name_plural = "订阅提醒企微每日汇总"
        constraints = [
            models.UniqueConstraint(
                fields=("user", "digest_date"),
                name="catalog_subrem_wecom_daily_once_per_user_date",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.user_id} · {self.digest_date}"


from .ledger_models import (  # noqa: E402,F401
    LedgerBusiness,
    LedgerBusinessOption,
    LedgerRecord,
    LedgerWalletRecord,
)


class WechatBotRecord(models.Model):
    """微信机器人推送的各业务记单明细（供「微信BOT数据」页按业务展示）。不含普通记账。"""

    class TableType(models.TextChoices):
        PIXIVCOBAN = "pixivcoban", "充币"
        ONCE_CARD = "once_card", "一次卡"
        SHARED = "shared", "共享"
        PACKAGE = "package", "打包"
        OPENROUTER = "openrouter", "openrouter"
        PATREON = "patreon", "patreon"
        COMMISSION = "commission", "约稿"
        BOOTH = "booth", "booth"
        PICTSPACE = "pictspace", "pictspace"
        PREMIUM = "premium", "高级会员"
        MEGA = "mega", "mega"
        CHATGPT = "chatgpt", "gpt"
        USDT = "usdt", "USDT"

    table_type = models.CharField(
        max_length=32,
        choices=TableType.choices,
        db_index=True,
        verbose_name="所属表",
    )
    external_id = models.CharField(
        max_length=128,
        unique=True,
        db_index=True,
        verbose_name="外部事件ID",
    )
    record_no = models.CharField(max_length=64, blank=True, default="", verbose_name="机器人流水号")
    book = models.CharField(max_length=32, blank=True, default="", verbose_name="机器人账本")
    direction = models.CharField(max_length=16, blank=True, default="", verbose_name="收支")
    # 记单数量（+1 / -1）；USDT 不用此字段
    quantity = models.IntegerField(default=0, verbose_name="数量")
    # 通用金额；USDT 表表示「人民币数」
    amount = models.DecimalField(max_digits=18, decimal_places=2, default=0, verbose_name="金额/人民币数")
    # USDT 表「美金数」
    amount_usd = models.DecimalField(max_digits=18, decimal_places=2, default=0, verbose_name="美金数")
    currency = models.CharField(max_length=8, blank=True, default="CNY", verbose_name="币种")
    business_name = models.CharField(max_length=128, blank=True, default="", verbose_name="业务名")
    amount_to_you = models.DecimalField(max_digits=18, decimal_places=2, default=0, verbose_name="给你")
    amount_to_me = models.DecimalField(max_digits=18, decimal_places=2, default=0, verbose_name="给我")
    profit_amount = models.DecimalField(max_digits=18, decimal_places=2, default=0, verbose_name="利润")
    employee_name = models.CharField(max_length=128, blank=True, default="", verbose_name="人员")
    chat_name = models.CharField(max_length=128, blank=True, default="", verbose_name="群名")
    raw_text = models.CharField(max_length=500, blank=True, default="", verbose_name="原始消息")
    remark = models.CharField(max_length=200, blank=True, default="", verbose_name="备注")
    # ACTIVE=未清空；PROCESSED/CLEARED=已清空
    status = models.CharField(max_length=16, blank=True, default="ACTIVE", verbose_name="清空状态")
    occurred_at = models.DateTimeField(null=True, blank=True, verbose_name="时间")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="入库时间")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="更新时间")

    class Meta:
        ordering = ["-occurred_at", "-id"]
        verbose_name = "微信BOT记录"
        verbose_name_plural = "微信BOT记录"
        indexes = [
            models.Index(fields=["table_type", "-occurred_at"]),
            models.Index(fields=["table_type", "status"]),
        ]

    def __str__(self) -> str:
        return f"{self.table_type} · {self.amount} · {self.external_id}"
