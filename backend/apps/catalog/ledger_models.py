"""记账模块（原 Node store.json），与商品 catalog.Business 无关。"""

from django.db import models


class LedgerBusiness(models.Model):
    id = models.CharField(max_length=36, primary_key=True)
    name = models.CharField(max_length=500)

    class Meta:
        verbose_name = "记账一级业务"
        verbose_name_plural = "记账一级业务"

    def __str__(self) -> str:
        return self.name


class LedgerBusinessOption(models.Model):
    id = models.CharField(max_length=36, primary_key=True)
    business = models.ForeignKey(
        LedgerBusiness,
        on_delete=models.CASCADE,
        related_name="options",
    )
    label = models.CharField(max_length=500)

    class Meta:
        verbose_name = "记账二级选项"
        verbose_name_plural = "记账二级选项"

    def __str__(self) -> str:
        return self.label


class LedgerRecord(models.Model):
    class Status(models.TextChoices):
        ACTIVE = "ACTIVE", "未清账"
        PROCESSED = "PROCESSED", "已清账"
        REVERSED = "REVERSED", "已撤销"

    id = models.CharField(max_length=36, primary_key=True)
    record_at = models.CharField(max_length=64, db_index=True)
    record_no = models.CharField(max_length=64, blank=True, default="", db_index=True)
    external_id = models.CharField(max_length=128, blank=True, null=True, unique=True)
    business = models.ForeignKey(
        LedgerBusiness,
        on_delete=models.PROTECT,
        related_name="ledger_records",
    )
    business_name = models.CharField(max_length=500)
    option_id = models.CharField(max_length=36, blank=True, null=True)
    option_label = models.CharField(max_length=500, blank=True, default="")
    amount = models.DecimalField(max_digits=16, decimal_places=2, default=0)
    give_amount = models.DecimalField(max_digits=16, decimal_places=2, default=0)
    take_amount = models.DecimalField(max_digits=16, decimal_places=2, default=0)
    profit = models.DecimalField(max_digits=16, decimal_places=2, default=0)
    employee_name = models.CharField(max_length=128, blank=True, default="")
    chat_name = models.CharField(max_length=128, blank=True, default="")
    status = models.CharField(
        max_length=16,
        choices=Status.choices,
        default=Status.ACTIVE,
        db_index=True,
    )
    settled_at = models.CharField(max_length=64, blank=True, null=True)

    class Meta:
        verbose_name = "记账记录"
        verbose_name_plural = "记账记录"
        ordering = ["record_at", "id"]


class LedgerWalletRecord(models.Model):
    id = models.CharField(max_length=36, primary_key=True)
    record_at = models.CharField(max_length=64, db_index=True)
    wechat = models.DecimalField(max_digits=16, decimal_places=2, default=0)
    alipay = models.DecimalField(max_digits=16, decimal_places=2, default=0)
    card = models.DecimalField(max_digits=16, decimal_places=2, default=0)
    pocket = models.DecimalField(max_digits=16, decimal_places=2, default=0)
    total = models.DecimalField(max_digits=16, decimal_places=2, default=0)

    class Meta:
        verbose_name = "钱包余额记录"
        verbose_name_plural = "钱包余额记录"
        ordering = ["record_at", "id"]
