import os
from django.core.management.base import BaseCommand
from django.core.files.base import ContentFile
from institution.models import Institution, InstitutionCategory
from product.models import Product
from PIL import Image
from io import BytesIO
import logging
from django.db.models import Model, Q
from banner.models import Banner


class NEW_RESOLUTIONS:
    RESTAURANT = (2048, 1536)
    PRODUCT = (1024, 1024)
    CATEGORY = (300, 300)
    BANNER = (1680, 420)


class Command(BaseCommand):
    help = "Resize Thumbnails to new resolution"

    def handle(self, *args, **options):
        # TO_HANDLE
        # institution/models.py Institution.image
        # product/models.py Product.image
        logging.info("Started resizing ")

        institutions = Institution.objects.all().exclude(image="").exclude(image__isnull=True)
        for institution in institutions:
            resize_image_of_object(
                handler=self,
                obj=institution,
                attrnames=["image"],
                resolution=NEW_RESOLUTIONS.RESTAURANT,
            )

        products = Product.objects.all().exclude(image="").exclude(image__isnull=True)
        for product in products:
            resize_image_of_object(
                handler=self, obj=product, attrnames=["image"], resolution=NEW_RESOLUTIONS.PRODUCT
            )

        banners = Banner.objects.all().filter(
            Q(img_ru__isnull=False) & Q(img_uz__isnull=False) & Q(img_en__isnull=False)
        )
        for banner in banners:
            resize_image_of_object(
                handler=self,
                obj=banner,
                attrnames=["img_ru", "img_uz", "img_en"],
                resolution=NEW_RESOLUTIONS.BANNER,
            )

        categories = InstitutionCategory.objects.all().exclude(image__isnull=True)
        for category in categories:
            resize_image_of_object(
                handler=self, obj=category, attrnames=["image"], resolution=NEW_RESOLUTIONS.CATEGORY
            )


def resize_image_of_object(
    handler: BaseCommand, obj: Model, attrnames: list, resolution: tuple[int, int]
) -> tuple[bool, int]:
    for attrname in attrnames:
        object_image = getattr(obj, attrname)
        image_path = object_image.path
        obj_type = str(obj.__class__).split(".")[-1]
        message_str = f"{obj_type} > {obj.id}"
        if not os.path.exists(image_path):
            handler.stdout.write(handler.style.WARNING(f"IMAGE NOT FOUND: {message_str}"))
            continue
        with Image.open(image_path) as img:
            if img.size == resolution:
                handler.stdout.write(handler.style.SUCCESS(f"SKIPPING: {message_str}"))
                continue
            img = img.resize(resolution, Image.Resampling.LANCZOS)
            buffer = BytesIO()
            img.save(buffer, format="JPEG", quality=95)
            new_image_content = ContentFile(buffer.getvalue())
            object_image.save(object_image.name, new_image_content, save=True)
            handler.stdout.write(handler.style.SUCCESS(f"RESIZED: {message_str}"))
            continue
        handler.stdout.write(handler.style.ERROR(f"UNKNOWN ERROR: {message_str}"))
