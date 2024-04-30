from django.db import models

from avito_account.models import Item


class ServiceType(models.Model):
    service_name = models.CharField(max_length=255, null=True)
    service_type = models.CharField(max_length=255, null=True)
    service_id = models.IntegerField(null=True)

    def __str__(self):
        return self.service_name


class Operation(models.Model):
    amount_bonus = models.IntegerField()
    amount_rub = models.IntegerField()
    amount_total = models.IntegerField()
    item = models.ForeignKey(Item, on_delete=models.CASCADE, null=True)
    name = models.CharField(max_length=255, null=True)
    type = models.CharField(max_length=255, null=True)
    service = models.ForeignKey(ServiceType, on_delete=models.CASCADE)
    updated_at = models.DateTimeField()

    def __str__(self):
        return self.name

    class Meta:
        unique_together = ['updated_at', 'name']


# Create your models here.
class Statistic(models.Model):
    item = models.ForeignKey(Item, on_delete=models.CASCADE, null=True)
    date = models.DateTimeField()
    uniq_contacts = models.IntegerField()
    uniq_favorites = models.IntegerField()
    uniq_views = models.IntegerField()

    def __str__(self):
        return str(self.item.title)

    class Meta:
        unique_together = ['item', 'date']
