from django.conf import settings
from drf_yasg.openapi import Schema, TYPE_STRING, TYPE_OBJECT
from drf_yasg.utils import swagger_auto_schema
from rest_framework import views
from rest_framework.authtoken.models import Token
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.authentication import TokenAuthentication

from user.models import CustomFCMDevice, User
from user.serializers import CustomFCMDeviceSerializer, UserSerializer
from user.services import check_otp, send_otp_sms

from fcm_django.models import FCMDevice
from rest_framework import status

class GetVerificationCodeAPIView(views.APIView):
    authentication_classes = []
    permission_classes = []

    @swagger_auto_schema(
        request_body=Schema(
            properties={
                "phone_number": Schema(type=TYPE_STRING),
            },
            type=TYPE_OBJECT,
        )
    )
    def post(self, request, *args, **kwargs):
        phone_number = request.data.get("phone_number")

        if not phone_number:
            response = {"phone_number": "field is required"}
            return Response(response, status=400)

        try:
            user = User.objects.get(phone_number=phone_number)
            response = {"status": "success", "action": "signin"}
        except User.DoesNotExist:
            user = User(phone_number=phone_number, is_active=True)
            user.save()
            response = {"status": "success", "action": "signup"}

        # for testing purposes only!
        if settings.DEBUG or user.phone_number == "998111111111":
            return Response(status=200)

        is_success = send_otp_sms(user)

        if not is_success:
            return Response({"detail": "error"}, status=500)

        return Response({"status": "success"}, status=200)


class VerifyAPIView(views.APIView):
    authentication_classes = []
    permission_classes = []

    @swagger_auto_schema(
        request_body=Schema(
            properties={
                "phone_number": Schema(type=TYPE_STRING),
                "sms_code": Schema(type=TYPE_STRING),
            },
            type=TYPE_OBJECT,
            required=["phone_number", "sms_code"],
        )
    )
    def post(self, request, *args, **kwargs):
        data = request.data
        sms_code = data.get("sms_code")
        phone_number = data.get("phone_number")

        if not (sms_code and phone_number):
            response = {
                "sms_code": "field is required",
                "phone_number": "field is required",
                "error_code": "-1"
            }
            return Response(response, status=400)

        try:
            user = User.objects.select_related("auth_token").get(phone_number=phone_number)
        except User.DoesNotExist:
            return Response({"detail": "the phone number is not correct", "error_code": "-2"}, status=400)

        # if settings.DEBUG or phone_number == "998111111111":
        #     Token.objects.get_or_create(user=user)
        #     return Response(UserSerializer(user).data)

        is_correct = check_otp(user, sms_code)

        if is_correct:
            Token.objects.get_or_create(user=user)
            return Response(UserSerializer(user).data)

        else:
            return Response({"detail": "the otp is not correct", "error_code": "-3"}, status=400)

class LogoutAPIView(views.APIView):
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]

    def post(self, request, *args, **kwargs):
        
        try:
            user = request.user
            register_id = request.data.get("registration_id")
            device_id = request.data.get("device_id")
            app_name = request.data.get('app_name')
            type = request.data.get('type')

            device = CustomFCMDevice.objects.filter(user=user, registration_id=register_id, device_id=device_id, app_name=app_name, type=type).first()
            if device:
                device.delete()

            return Response({"status": "success"}, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({"detail": f"User Device not registered, {e}", "error_code": "-2"}, status.HTTP_400_BAD_REQUEST)

class CustomFCMDeviceView(views.APIView):
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]
    serializer_class = CustomFCMDeviceSerializer

    def post(self, request, *args, **kwargs):
        user = request.user

        existing_device = CustomFCMDevice.objects.filter(app_name=request.data.get("app_name"), registration_id=request.data.get("registration_id")).first()
        if existing_device:
            existing_device.delete()

        serializer = self.serializer_class(data=request.data)
        if serializer.is_valid():
            serializer.save(user=user)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    def patch(self, request, *args, **kwargs):
        user = request.user
        app_name = request.data.get("app_name")
        register_id = request.data.get("registration_id")
        active = request.data.get("active")

        try:
            if app_name:
                existing_device = CustomFCMDevice.objects.filter(user=user, app_name=app_name, registration_id=register_id).first()
                # if existing_device:
                existing_device.active = active
                existing_device.save()
                return Response({"status": "success", "message": "status updated successfully."}, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({"status": "error", "message": str(e)}, status=status.HTTP_400_BAD_REQUEST)