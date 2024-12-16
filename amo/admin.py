from django.contrib import admin

from amo.models import AmocrmAccount


class AmocrmAccountAdmin(admin.ModelAdmin):
    change_form_template = "admin/amo/amocrmaccount/change_form.html"


admin.site.register(AmocrmAccount, AmocrmAccountAdmin)
