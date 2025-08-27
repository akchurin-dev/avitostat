from django.contrib.auth.models import User
from avito_account.models.models import AnalyticSchema, AvitoAccount, Criterion, WorkSchedule
from avito_account.models.sending_report import SendingCampaign, SendingReport
from django.core.management.base import BaseCommand
from django.utils import timezone
import random


class Command(BaseCommand):
    help = 'Populate the database with sample data'

    def handle(self, *args, **kwargs):
        # Создаём пользователей
        superuser = User.objects.create_superuser(username='superuser', password='password', email='super@example.com')
        user1 = User.objects.create_user(username='user1', password='password', email='user1@example.com',
                                         is_staff=True)
        user2 = User.objects.create_user(username='user2', password='password', email='user2@example.com',
                                         is_staff=True)
        users = [superuser, user1, user2]

        # Создаём схемы аналитики
        schemas = []
        for i, user in enumerate(users):
            schema = AnalyticSchema.objects.create(
                name=f"Schema {i + 1}",
                created_by=user
            )
            schemas.append(schema)

            # Создаём критерии для каждой схемы аналитики
            for j in range(3):  # Создаём 3 критерия для каждой схемы
                Criterion.objects.create(
                    schema=schema,
                    name=f"Criterion {i + 1}.{j + 1}"
                )

        # Создаём Avito аккаунты
        accounts = []
        for i, user in enumerate(users):
            account = AvitoAccount.objects.create(
                name=f"Account {i + 1}",
                telegram_id=f"@account{i + 1}",
                phone=f"+7900123456{i}",
                profile_url=f"https://avito.ru/profile/{i + 1}",
                access_token="dummy_access_token",
                refresh_token="dummy_refresh_token",
                created_by=user,
                analytic_schema=schemas[i]
            )
            accounts.append(account)

        # Создаём рабочие графики для Avito аккаунтов
        for account in accounts:
            WorkSchedule.objects.create(
                avito_account=account,
                weekday_start=timezone.now().replace(hour=10, minute=0).time(),
                weekday_end=timezone.now().replace(hour=18, minute=0).time(),
                saturday_is_day_off=True,
                sunday_is_day_off=True
            )

        # Создаём рассылки
        campaigns = []
        for i in range(2):
            campaign = SendingCampaign.objects.create(
                name=f"Campaign {i + 1}",
                test_from_prod=False,
                sending_type=random.choice([SendingCampaign.PDF, SendingCampaign.TEXT]),
                created_at=timezone.now(),
                accounts_presented_count=3
            )
            campaigns.append(campaign)

        # Создаём отчёты рассылок
        for account in accounts:
            for campaign in campaigns:
                SendingReport.objects.create(
                    avito_account=account,
                    campaign=campaign,
                    success=random.choice([True, False]),
                    error_message=None if random.choice([True, False]) else "Some error occurred",
                    pdf_path="path/to/file.pdf" if campaign.sending_type == SendingCampaign.PDF else None,
                    timestamp=timezone.now()
                )

        self.stdout.write(self.style.SUCCESS('База данных успешно заполнена данными!'))
