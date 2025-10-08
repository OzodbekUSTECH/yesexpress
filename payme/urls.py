from django.urls import path

from . import views

urlpatterns = [
    path("payment/", views.PaymentView.as_view()),
    path("card-add/", views.CardView.as_view()),
    path("card-verify/", views.VerifyCardView.as_view()),
    path("cards/", views.CardListView.as_view()),
]
