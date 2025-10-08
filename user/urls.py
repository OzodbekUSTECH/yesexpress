from django.urls import path
from fcm_django.api.rest_framework import FCMDeviceAuthorizedViewSet
from rest_framework.authtoken.views import obtain_auth_token
from user.views.registration import CustomFCMDeviceView

from . import views

urlpatterns = [
    path("me/", views.ProfileView.as_view()),
    path("me/token/", obtain_auth_token),
    path("get_verification_code/", views.GetVerificationCodeAPIView.as_view()),
    path("verify/", views.VerifyAPIView.as_view()),
    path("logout/", views.LogoutAPIView.as_view()),
    path("delete-account/", views.DeleteAccountView.as_view()),
    path("change-number/get-verification-code/", views.ChangeNumberView.as_view()),
    path("change-number/verify/", views.VerifyChangeNumber.as_view()),
    path("devices/", CustomFCMDeviceView.as_view(), name="create_fcm_device"),
]
