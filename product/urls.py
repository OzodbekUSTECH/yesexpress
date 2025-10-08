from django.urls import path
from . import views

urlpatterns = [
    path("favourite/", views.LikedProductsList.as_view()),
    path("<int:pk>/like", views.LikeProductView.as_view()),
]
