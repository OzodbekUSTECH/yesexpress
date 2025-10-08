from django.db import transaction

from stories.models import Stories, StoriesToRegion
from datetime import datetime


def create_stories(
    user,
    image_stories_ru,
    image_stories_uz,
    image_stories_en,
    logo_stories_ru,
    logo_stories_uz,
    logo_stories_en,
    start_date=datetime.today(),
    end_date=datetime.today(),
    url_link=None,
    title="",
    is_active=True,
    position=True,
    region_ids=None,
    institution=None,
):
    stories_instance = Stories.objects.create(
        created_user=user,
        image_stories_ru=image_stories_ru,
        image_stories_uz=image_stories_uz,
        image_stories_en=image_stories_en,
        logo_stories_ru=logo_stories_ru,
        logo_stories_uz=logo_stories_uz,
        logo_stories_en=logo_stories_en,
        start_date=start_date,
        end_date=end_date,
        url_link=url_link,
        title=title,
        is_active=is_active,
        position=position,
        institution=institution,
    )

    if region_ids:
        StoriesToRegion.objects.bulk_create(
            StoriesToRegion(region_id=region, story=stories_instance) for region in region_ids
        )
    return stories_instance


def update_stories(stories: Stories, data):
    regions = data.pop("region_ids", None)
    institution_branch = data.pop("institution_branch", None)

    with transaction.atomic():
        for attr, value in data.items():
            setattr(stories, attr, value)

        if institution_branch is not None:
            stories.institution_branch = institution_branch

        if regions is not None:
            current_region_ids = set(stories.regions.values_list("region_id", flat=True))
            new_region_ids = set(regions) - current_region_ids
            removed_region_ids = current_region_ids - set(regions)

            if new_region_ids:
                StoriesToRegion.objects.bulk_create(
                    StoriesToRegion(region_id=region, story=stories) for region in regions
                )
            if removed_region_ids:
                StoriesToRegion.objects.filter(
                    story=stories, region_id__in=removed_region_ids
                ).delete()

        stories.save()
    return stories
