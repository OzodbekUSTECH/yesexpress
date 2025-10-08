from django.views.generic import TemplateView

from crm.mixins import IsContentManagerMixin


class InstitutionCategoryListView(IsContentManagerMixin, TemplateView):
    template_name = "crm/content_manager/institution_category_list.html"


class InstitutionCategoryDetailView(IsContentManagerMixin, TemplateView):
    template_name = "crm/content_manager/institution_category_detail.html"


class InstitutionCategoryCreateView(IsContentManagerMixin, TemplateView):
    template_name = "crm/content_manager/institution_category_create.html"


class InstitutionListView(IsContentManagerMixin, TemplateView):
    template_name = "crm/content_manager/institution_list.html"


class InstitutionDetailView(IsContentManagerMixin, TemplateView):
    template_name = "crm/content_manager/institution_detail.html"


class InstitutionCreateView(IsContentManagerMixin, TemplateView):
    template_name = "crm/content_manager/institution_create.html"


class CategoryListView(IsContentManagerMixin, TemplateView):
    template_name = "crm/content_manager/categories.html"


class CategoryDetailView(IsContentManagerMixin, TemplateView):
    template_name = "crm/content_manager/category_detail.html"


class CategoryCreateView(IsContentManagerMixin, TemplateView):
    template_name = "crm/content_manager/category_create.html"


class ProductListView(IsContentManagerMixin, TemplateView):
    template_name = "crm/content_manager/products.html"


class ProductDetailView(IsContentManagerMixin, TemplateView):
    template_name = "crm/content_manager/product_detail.html"


class ProductCreateView(IsContentManagerMixin, TemplateView):
    template_name = "crm/content_manager/product_create.html"


class ProductOptionDetailView(IsContentManagerMixin, TemplateView):
    template_name = "crm/content_manager/product_option_detail.html"
