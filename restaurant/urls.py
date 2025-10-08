from django.urls import path, include
from rest_framework.routers import SimpleRouter
from .views import OrderActionsViewSet, RestaurantInstitutionViewSet, RestaurantWorkerViewSet, FeedbackViewSet

restaurant_router = SimpleRouter()

restaurant_router.register(
    prefix="restaurant/orders", viewset=OrderActionsViewSet, basename="restaurantorders"
)
restaurant_router.register(
    prefix="restaurant/feedbacks", viewset=FeedbackViewSet, basename="restaurantfeedbacks"
)
restaurant_router.register(
    prefix="restaurant/branches", viewset=RestaurantInstitutionViewSet, basename="restaurantbranches"
)

urlpatterns = [
    path(
        "restaurant/workers/",
        include(
            [
                path("", RestaurantWorkerViewSet.as_view({"get": "list", "post": "create"})),
                path(
                    "<int:pk>/",
                    RestaurantWorkerViewSet.as_view({"get": "retrieve", "put": "partial_update"}),
                ),
            ]
        ),
    ),
]

urlpatterns += restaurant_router.urls
