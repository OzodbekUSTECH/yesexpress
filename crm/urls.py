from django.urls import path

from . import views
from . import operator_views
from . import content_manager_views

urlpatterns = [
    path("login/", views.LoginView.as_view(), name="login"),
    path("logout/", views.CRMLogoutView.as_view(), name="logout"),
    path("dashboard/", views.DashboardView.as_view(), name="dashboard"),
    path("institution/", views.InstitutionView.as_view(), name="institution-admin"),
    path(
        "institution/update/",
        views.InstitutionUpdateView.as_view(),
        name="institution-update-admin",
    ),
    path(
        "instutution/addess/",
        views.InstitutionAddressView.as_view(),
        name="change-institution-address",
    ),
    path(
        "delivery_settings/update/",
        views.DeliverySettingsUpdate.as_view(),
        name="delivery-settings",
    ),
    path("management/", views.InstitutionManagement.as_view(), name="institution-management"),
    path(
        "management/create-admin",
        views.InstitutionAdminCreate.as_view(),
        name="insitution-admin-create",
    ),
    path("new_orders/", views.NewOrdersView.as_view(), name="new-orders"),
    path("orders/", views.OrderListView.as_view(), name="orders-admin"),
    path("orders/<int:pk>", views.OrderDetailView.as_view(), name="order-detail-admin"),
    path("index/", views.AdminIndexView.as_view(), name="institution_index"),
    path("categories/", views.CategoryListView.as_view(), name="categories"),
    path(
        "categories/<int:pk>/update/",
        views.CategoryUpdateView.as_view(),
        name="category-update-admin",
    ),
    path("categories/create/", views.CategoryCreateView.as_view(), name="category-create-admin"),
    path("categories/delete/", views.CategoryDeleteView.as_view(), name="category-delete-admin"),
    path("products/", views.ProductListView.as_view(), name="products"),
    path("products/create/", views.ProductCreateView.as_view(), name="product-create-admin"),
    path("products/<int:pk>/", views.ProductDetailView.as_view(), name="product-detail-admin"),
    path(
        "products/<int:pk>/update/", views.ProductUpdateView.as_view(), name="product-update-admin"
    ),
    path("options/<int:pk>/update/", views.update_option_items, name="option-update-admin"),
    path("options/", views.OptionView.as_view(), name="option-admin"),
    path("operator_orders/", operator_views.OrdersView.as_view(), name="operator-orders"),
    path(
        "operator_orders_history/",
        operator_views.OrdersHistoryView.as_view(),
        name="operator-orders-history",
    ),
    path("couriers/<int:pk>/", operator_views.CourierUpdateView.as_view(), name="courier-update"),
    path("couriers/", operator_views.CourierListView.as_view(), name="courier-list"),
    path("couriers/create/", operator_views.CourierCreateView.as_view(), name="courier-create"),
    path(
        "couriers/<int:pk>/orders/",
        operator_views.CourierOrderView.as_view(),
        name="courier-orders",
    ),
    path(
        "content-manager/institution-categories/",
        content_manager_views.InstitutionCategoryListView.as_view(),
        name="content-manager-institution-category-list",
    ),
    path(
        "content-manager/institution-categories/create/",
        content_manager_views.InstitutionCategoryCreateView.as_view(),
        name="content-manager-institution-category-create",
    ),
    path(
        "content-manager/institution-categories/<int:pk>/",
        content_manager_views.InstitutionCategoryDetailView.as_view(),
        name="content-manager-institution-category-detail",
    ),
    path(
        "content-manager/institutions/",
        content_manager_views.InstitutionListView.as_view(),
        name="content-manager-institution-list",
    ),
    path(
        "content-manager/institutions/create/",
        content_manager_views.InstitutionCreateView.as_view(),
        name="content-manager-institution-create",
    ),
    path(
        "content-manager/institutions/<int:pk>/",
        content_manager_views.InstitutionDetailView.as_view(),
        name="content-manager-institution-detail",
    ),
    path(
        "content-manager/categories/",
        content_manager_views.CategoryListView.as_view(),
        name="content-manager-category-list",
    ),
    path(
        "content-manager/categories/create/",
        content_manager_views.CategoryCreateView.as_view(),
        name="content-manager-category-create",
    ),
    path(
        "content-manager/categories/<int:pk>/",
        content_manager_views.CategoryDetailView.as_view(),
        name="content-manager-category-detail",
    ),
    path(
        "content-manager/products/",
        content_manager_views.ProductListView.as_view(),
        name="content-manager-product-list",
    ),
    path(
        "content-manager/products/create/",
        content_manager_views.ProductCreateView.as_view(),
        name="content-manager-product-create",
    ),
    path(
        "content-manager/products/<int:pk>/",
        content_manager_views.ProductDetailView.as_view(),
        name="content-manager-product-detail",
    ),
    path(
        "content-manager/product-options/<int:pk>/",
        content_manager_views.ProductOptionDetailView.as_view(),
        name="content-manager-product-options-detail",
    ),
    path("change_password/", views.ChangePasswordView.as_view(), name="change-password"),
    path("report/", views.OrderReportView.as_view(), name="order-report"),
    path("", views.RedirectView.as_view(), name="index"),
]
