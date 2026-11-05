from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('catalog', '0072_commonaccount'),
    ]

    operations = [
        migrations.AlterField(
            model_name='wechatbotrecord',
            name='table_type',
            field=models.CharField(choices=[('pixivcoban', '充币'), ('once_card', '一次卡'), ('shared', '共享'), ('package', '打包'), ('openrouter', 'openrouter'), ('patreon', 'patreon'), ('commission', '约稿'), ('booth', 'booth'), ('pictspace', 'pictspace'), ('remote', '远程'), ('premium', '高级会员'), ('mega', 'mega'), ('chatgpt', 'gpt'), ('usdt', 'USDT')], db_index=True, max_length=32, verbose_name='所属表'),
        ),
    ]
