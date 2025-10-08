from django.urls import path, include

from institution.views import ImportView

from . import views

urlpatterns = [
    path(
        "institution-categories/",
        views.InstitutionCategoryViewSet.as_view(
            {
                "get": "list",
                "post": "create",
            }
        ),
    ),
    path(
        "institution-categories/<int:pk>/",
        views.InstitutionCategoryViewSet.as_view(
            {
                "get": "retrieve",
                "put": "partial_update",
                "delete": "destroy",
            }
        ),
    ),
    path(
        "institutions/",
        views.InstitutionViewSet.as_view(
            {
                "get": "list",
                "post": "create",
            }
        ),
    ),
    path('institution/report/', views.InstitutionReportAPIView.as_view(), name='institution-report'),
    path(
        "institutions/<int:pk>/",
        views.InstitutionViewSet.as_view(
            {
                "get": "retrieve",
                "put": "partial_update",
                "delete": "destroy",
            }
        ),
    ),
    path(
        "institutions/<int:pk>/delivery-settings/",
        views.InstitutionViewSet.as_view(
            {
                "get": "get_delivery_settings",
                "put": "update_delivery_settings",
            }
        ),
    ),
    path(
        "institutions/<int:pk>/owner/",
        views.InstitutionViewSet.as_view(
            {
                "post": "add_institution_owner",
                "put": "update_institution_owner",
            }
        ),
    ),
    path(
        "institutions/<int:pk>/owner/password/",
        views.InstitutionViewSet.as_view(
            {
                "put": "change_institution_owner_password",
            }
        ),
    ),
    path(
        "institutions/<int:pk>/admin/",
        views.InstitutionViewSet.as_view(
            {
                "post": "add_institution_admin",
                "put": "update_institution_admin",
                "delete": "delete_institution_admin",
            }
        ),
    ),
    path(
        "institutions/<int:pk>/admin/password/",
        views.InstitutionViewSet.as_view(
            {
                "put": "change_institution_admin_password",
            }
        ),
    ),
    path("institutions/<int:pk>/import/", ImportView.as_view()),

    path(
        "institution-branches/",
        include(
            [
                path("", views.InstitutionBranchViewSet.as_view({"get": "list", "post": "create"})),
                path(
                    "<int:pk>/",
                    views.InstitutionBranchViewSet.as_view(
                        {"get": "retrieve", "put": "partial_update"}
                    ),
                ),
                path(
                    "<int:pk>/update_schedule/",
                    views.InstitutionBranchViewSet.as_view({"put": "update_schedule"}),
                ),
                path(
                    "<int:pk>/schedule_day/<int:schedule_id>/",
                    views.InstitutionBranchViewSet.as_view({"put": "change_schedule_day_active"}),
                ),
            ]
        ),
    ),
]
