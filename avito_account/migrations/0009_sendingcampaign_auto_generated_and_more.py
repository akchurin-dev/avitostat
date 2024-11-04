from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('avito_account', '0008_alter_analyticschema_created_at_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='sendingcampaign',
            name='auto_generated',
            field=models.BooleanField(default=False, verbose_name='Автоматически'),
        ),
        migrations.AddField(
            model_name='sendingreport',
            name='balance_decrease',
            field=models.IntegerField(default=0, verbose_name='К списанию с баланса'),
        ),
        migrations.AlterField(
            model_name='sendingcampaign',
            name='test_from_prod',
            field=models.BooleanField(default=False, verbose_name='Тест'),
        ),
    ]
