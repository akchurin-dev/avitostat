from django.contrib import admin

from payments.models import Payment, UserProfile

# Register your models here.
admin.site.register(Payment)
admin.site.register(UserProfile)
