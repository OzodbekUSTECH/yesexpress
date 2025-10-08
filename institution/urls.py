from django.urls import path
from . import views

urlpatterns = [
    # path("favourite/", views.LikedInstitutionsList.as_view()),
    path("<int:pk>/like/", views.LikeInstitutionView.as_view()),
    path("<int:pk>/rate/", views.RateInstitutionView.as_view()),
    path("<int:pk>/search/", views.SearchView.as_view()),
]
