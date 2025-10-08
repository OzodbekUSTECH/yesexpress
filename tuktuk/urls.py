"""tuktuk URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/3.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import path, include

from crm.admin_views import OrderReportView, UserCheckView
from .settings import DEBUG, MEDIA_URL, MEDIA_ROOT, STATIC_ROOT, STATIC_URL

urlpatterns = [
    path("admin/order-reports/", OrderReportView.as_view(), name="order-reports"),
    path("user-check/", UserCheckView.as_view(), name="order-reports"),
    path("admin/", admin.site.urls),
    path("", include("crm.urls")),
    path("api/", include("api.urls")),
    path("api/crm/", include("api.crm_urls")),
    path("__debug__/", include("debug_toolbar.urls")),
]

if DEBUG:
    urlpatterns += static(MEDIA_URL, document_root=MEDIA_ROOT)
    urlpatterns += static(STATIC_URL, document_root=STATIC_ROOT)
