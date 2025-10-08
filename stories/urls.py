from django.urls import path
from . import views


urlpatterns = [
    path("stories-list/", views.StoriesList.as_view(), name="stories"),
    path("stories-detail/<int:pk>/", views.StoriesDetail.as_view(), name="stories-detail"),
]
