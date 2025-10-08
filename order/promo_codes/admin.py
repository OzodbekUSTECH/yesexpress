from django.contrib import admin

from order.promo_codes.models import PromoCode, PromoCodeUsage


class UsableListFilter(admin.SimpleListFilter):
    title = "Можно использовать"
    parameter_name = "usable"

    def lookups(self, request, model_admin):
        return (("usable", "Можно использовать"),)

    def queryset(self, request, queryset):
        value = self.value()
        if value == "usable":
            return queryset.filter_usable()

        return queryset


@admin.register(PromoCode)
class PromoCodeAdmin(admin.ModelAdmin):
    list_display = "name", "sum"
    list_filter = UsableListFilter, "revokable"

    def get_queryset(self, request):
        return PromoCode.objects.annotate_usable()


@admin.register(PromoCodeUsage)
class PromoCodeUsageAdmin(admin.ModelAdmin):
    list_display = "user", "promo_code"
