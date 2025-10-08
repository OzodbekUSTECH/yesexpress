from django.urls import path, include

urlpatterns = [
    path("", include("crm.api.order.urls")),
    path("", include("crm.api.product.urls")),
    path("", include("crm.api.courier.urls")),
    path("", include("crm.api.institution.urls")),
    path("", include("crm.api.address.urls")),
    path("", include("crm.api.banner.urls")),
    path("", include("crm.api.stories.urls")),
    path("", include("crm.api.dashboard.urls")),
    path("", include("crm.api.user.urls")),
    path("", include("crm.api.common.urls")),
    path("", include("crm.api.promo_code.urls")),
]
