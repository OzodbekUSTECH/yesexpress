import requests
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.viewsets import ModelViewSet

from .utils import PaymeApiClient, make_payment
from .serializers import PaymentSerializer, CardSerializer, ShortCardSerializer
from .models import PaymeCard


class PaymentView(APIView):
    def post(self, request):
        serializer = PaymentSerializer(data=request.data)

        if not serializer.is_valid():
            return Response(serializer.errors)

        card = serializer.validated_data["card"]
        order = serializer.validated_data["order"]

        with requests.Session() as session:
            request = make_payment(session, order, card.token)
        return Response(data=request.json())

class CardView(APIView):
    def mask_card_number(self, card_number: str) -> str:
        if len(card_number) != 16 or not card_number.isdigit():
            raise ValueError("Karta raqami 16 xonali bo'lishi kerak va faqat raqamlardan iborat bo'lishi kerak.")
        
        return f"{card_number[:6]}******{card_number[-4:]}"

    def post(self, request):
        try:
            payme_api = PaymeApiClient()
            owner = request.user
            card_number = request.data['card_number']
            card_holder = request.data.get('card_holder', "")
            hidden_number = self.mask_card_number(card_number)
            expire = request.data['expire']
            card = PaymeCard.objects.filter(owner=owner, hidden_number=hidden_number, expires=expire, is_verify=True)
            if not card:
                token = payme_api.add_new_card(number=card_number, expire=expire)
                if token:
                    card = PaymeCard.objects.filter(owner=owner, hidden_number=hidden_number, expires=expire, is_verify=True)
                    
                    card = PaymeCard.objects.create(owner=owner, token=token, expires=expire, hidden_number=hidden_number, name=card_holder)
                    result = payme_api.verify_token(token=token)
                    return Response(data={"status": "success", "data": {"phone_number": result['phone'], "card_id": card.id}}, status=201)
            
            return Response(data={"status": "error", "message": "Карта уже существует!"}, status=400)
        
        except Exception as e:
            return Response(data={"status": "error", "message": str(e)}, status=400)
class CardListView(APIView):
    def get(self, request):
        try:
            owner = request.user
            cards = PaymeCard.objects.filter(owner=owner, is_verify=True)
            if cards:
                serializer = ShortCardSerializer(cards, many=True)

                return Response(data={"status": "success", "data": serializer.data}, status=200)
            
            return Response(data={"status": "success", "data": []}, status=400)
        except Exception as e:
            return Response(data={"status": "error", "message": str(e)}, status=400)
class VerifyCardView(APIView):
    def post(self, request):
        try:
            payme_api = PaymeApiClient()
            card_id = request.data['card_id']
            code = request.data['code']
            card = PaymeCard.objects.filter(pk=card_id).first()
            
            if card:
                res = payme_api.verify_phone_number(token=card.token, code=code)
                if 'error' in res:
                    return Response(data={"status": "error", "message": res['error']['message']}, status=400)
                else:
                   card.is_verify = True
                   card.save()
                   return Response(data={"status": "success", "message": "OK"}, status=200)
            
        except Exception as e:
            return Response(data={"status": "error", "message": str(e)}, status=400)


class CardViewSet(ModelViewSet):
    serializer_class = CardSerializer

    def perform_create(self, serializer):
        serializer.save(owner=self.request.user)
        return super(CardViewSet, self).perform_create(serializer)

    def get_queryset(self):
        user = self.request.user

        return PaymeCard.objects.filter(owner=user)
