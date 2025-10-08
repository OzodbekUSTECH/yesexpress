from django.urls import path, include
from drf_yasg import openapi
from drf_yasg.views import get_schema_view
from rest_framework.routers import SimpleRouter

from address.views import AddressViewSet
from courier.views import AvailableOrdersViewSet, CourierOrdersViewSet
from institution.views import (
    ShopViewSet,
    RestaurantViewSet,
    InstitutionCategoryViewSet,
    InstitutionViewSet,
)
from order.feedback.views import InstitutionFeedbackAPIView, DeliveryFeedbackAPIView
from order.promo_codes.views import get_promo_code_info
from order.views import OrderViewSet
from payme.views import CardViewSet
from banner.views import BannerViewSet
from product.views import ProductViewSet, LikeProductView, ProductCategoryViewSet
from tuktuk.swagger import CustomSwaggerGenerator
from user.views import UserViewSet
from .views import SearchView, GetLastVersionsView

router = SimpleRouter()
router.register(r"users", UserViewSet)
router.register(r"banner", BannerViewSet)
router.register(r"orders", OrderViewSet)
router.register(r"categories", InstitutionCategoryViewSet)
router.register(r"restaurants", RestaurantViewSet)
router.register(r"institutions", InstitutionViewSet, basename="institutions")
router.register(r"shops", ShopViewSet, basename="shops")
router.register(r"products", ProductViewSet)
router.register(r"addresses", AddressViewSet)
router.register(r"payme/payme-cards", CardViewSet, basename="payme-cards")
router.register(r"courier/available-orders", AvailableOrdersViewSet, basename="available-orders")
router.register(r"courier/my-orders", CourierOrdersViewSet, basename="courier-orders")
router.register(r"product-categories", ProductCategoryViewSet, basename="product-categories")

schema_view = get_schema_view(
    openapi.Info(
        title="Tuk Tuk API",
        default_version="v1",
    ),
    public=True,
    generator_class=CustomSwaggerGenerator,
    permission_classes=[],
)

urlpatterns = [
    # Подключенные приложения
    path("institutions/", include("institution.urls")),
    path("products/", include("product.urls")),
    path("users/", include("user.urls")),
    path("payme/", include("payme.urls")),
    path("courier/", include("courier.urls")),
    path("stories/", include("stories.urls")),
    path("restauraunt-mobile/", include("restaurant.urls")),
    path("", include("common.urls")),
    path("", include("payment.urls")),
    # Подключенные API
    path("products/<int:pk>/like/", LikeProductView.as_view()),
    path("search/", SearchView.as_view()),
    path("get-last-versions/", GetLastVersionsView.as_view()),
    path("feedbacks/institution/", InstitutionFeedbackAPIView.as_view()),
    path("feedbacks/delivery/", DeliveryFeedbackAPIView.as_view()),
    path("promo-codes/get-promo-code-info/", get_promo_code_info),
]

# if settings.DEBUG:
urlpatterns += [path("swagger/", schema_view.with_ui("swagger", cache_timeout=0), name="swagger")]

urlpatterns += router.urls
