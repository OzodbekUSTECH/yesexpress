from drf_yasg.utils import swagger_auto_schema
from rest_framework.viewsets import ViewSetMixin
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.generics import RetrieveAPIView

from user.models import User
from user.serializers import UserSerializer


class ProfileView(APIView):
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(responses={200: UserSerializer()})
    def get(self, request):
        serializer = UserSerializer(instance=request.user, context={"request": request})
        return Response(serializer.data)

    @swagger_auto_schema(request_body=UserSerializer(), responses={200: UserSerializer()})
    def put(self, request):
        data = request.data
        serializer = UserSerializer().update(request.user, data)
        return Response(UserSerializer(serializer, context={"request": request}).data)


class UserViewSet(ViewSetMixin, RetrieveAPIView):
    queryset = User.objects.all()
    serializer_class = UserSerializer
    permission_classes = [IsAuthenticated]


class DeleteAccountView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        user = request.user
        user.is_active = False
        phone = user.phone_number
        user.phone_number = f"{phone}_deleted_account_{user.id}"
        user.save()
        return Response({"status": "success"})
