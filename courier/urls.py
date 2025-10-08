from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView

from . import views

urlpatterns = [
    path("demo/", views.CourierDemoView.as_view()),
    path("delivering-price/", views.DeliveryPriceCalculatorView.as_view()),
    path("assign-order/<int:pk>/", views.AssignOrderView.as_view()),
    path("arrival/<int:pk>/", views.ChangeStatusView.as_view()),
    path("take-order/<int:pk>/", views.TakeOrderView.as_view()),
    path("close-order/<int:pk>/", views.CloseOrderView.as_view()),
    path("get-courier-id/", views.GetCourierID.as_view()),
    path("delivery-settings/", views.DeliverySettingsView.as_view()),
    path("order-history/", views.OrderHistory.as_view()),
    path("payment-history/", views.PaymentHistory.as_view()),
    path("token/refresh/", TokenRefreshView.as_view(), name="token_refresh"),
    path("get_verification_code/", views.GetVerificationCodeAPIView.as_view()),
    path("verify/", views.VerifyAPIView.as_view()),
    path("topup/", views.Topup.as_view()),
]
