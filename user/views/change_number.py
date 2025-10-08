from rest_framework.response import Response
from rest_framework.views import APIView

from user.models import User
from user.services import send_otp_sms, check_otp


class ChangeNumberView(APIView):
    def post(self, request):
        phone_number = request.data.get("phone_number")
        if not phone_number:
            return Response({"phone_number": "this field is required"}, status=400)

        if User.objects.filter(phone_number=phone_number).exists():
            return Response(
                {"phone_number": "user with this phone_number already exists"}, status=400
            )

        user = request.user

        user.phone_number = phone_number
        # set new phone number but not save it yet

        is_success = send_otp_sms(user, number_change=True)

        if not is_success:
            return Response({"detail": "error"}, status=500)

        return Response({"status": "success"}, status=200)


class VerifyChangeNumber(APIView):
    def post(self, request):
        data = request.data
        user = request.user
        sms_code = data.get("sms_code")
        phone_number = data.get("phone_number")

        if not (sms_code and phone_number):
            response = {
                "sms_code": "field is required",
                "phone_number": "field is required",
            }
            return Response(response, status=400)

        if phone_number == "998111111111":
            return Response({"status": "success"})

        is_correct = check_otp(user, sms_code, number_change=True)
        if is_correct:
            user.phone_number = phone_number
            user.save()
            return Response({"status": "success"})

        return Response({"status": "error"})
