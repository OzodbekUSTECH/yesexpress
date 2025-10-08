from django.shortcuts import redirect
from django.urls import reverse

from product.models import OptionItem, ProductOption


def create_option(request):
    data = request.POST
    product_id = data.get("product_id")
    option = ProductOption(
        title_ru=data.get("title_ru"),
        title_uz=data.get("title_uz"),
        title_en=data.get("title_en"),
        is_required=not not data.get("is_required"),
        product_id=product_id,
    )
    option.save()

    indexes = data.get("indexes").split()
    items = []
    for index in indexes:
        title_ru = data.get(f"title_ru_{index}")
        title_uz = data.get(f"title_uz_{index}")
        title_en = data.get(f"title_en_{index}")
        adding_price = data.get(f"adding_price_{index}")

        if all([title_ru, title_uz, title_en, adding_price]):
            item = OptionItem(
                title_ru=title_ru,
                title_uz=title_uz,
                title_en=title_en,
                adding_price=adding_price,
                is_deleted=False,
                is_default=False,
                option=option,
            )
            items.append(item)

    OptionItem.objects.bulk_create(items)

    return redirect(reverse("product-detail-admin", kwargs={"pk": product_id}))


def delete_option(request):
    data = request.POST
    product_id = data.get("product_id")
    ProductOption.objects.get(pk=data.get("option_id")).delete()
    return redirect(reverse("product-detail-admin", kwargs={"pk": product_id}))


# TODO: add fuctionality
def update_option(request):
    print(dict(request.POST))
