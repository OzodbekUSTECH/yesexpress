from datetime import datetime
from address.models import Address
from base.enums import DayOfWeekChoices
from courier.services import get_delivery_settings
from institution.models import Institution, InstitutionBranch, InstitutionBranchSchedule
from institution.services import find_another_branch, find_suitable_branch
from order.exceptions import CantFindSuitableBranchError
from order.feedback.models import InstitutionFeedback
from order.services import calculate_delivering_sum
from rest_framework import serializers
from django.db.models import OuterRef, Subquery, Avg, Case, When, Value, Exists, BooleanField, IntegerField
from django.db.models.functions import Coalesce

from .models import Banner


class InstitutionShortSerializer(serializers.ModelSerializer):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._delivery_settings = get_delivery_settings()
        
    rating = serializers.ReadOnlyField()
    delivery_price = serializers.IntegerField(allow_null=True, default=None)
    is_open_by_schedule = serializers.ReadOnlyField()
    # has_active_branch = serializers.ReadOnlyField()
    # has_active_branch_weight = serializers.ReadOnlyField()
    is_open = serializers.ReadOnlyField()

    def to_representation(self, instance):
        lat = self.context.get("lat")
        long = self.context.get("long")
        address = Address(latitude=lat, longitude=long)

        if instance.rating is not None:
            instance.rating = round(float(instance.rating), 1)
        # return rep
        if not lat or not long:
            return super().to_representation(instance)

        if address:
            try:
                weekday = DayOfWeekChoices.get_value_by_number(datetime.now().weekday())
                branch = find_suitable_branch(instance, address)
                
                if not branch:
                    is_open_by_schedule = False
                    branch = find_another_branch(instance, address)
                else:
                    is_open_by_schedule = branch.is_open_by_schedule
                               
                schedule = InstitutionBranchSchedule.objects.get(institution=branch, day_of_week=weekday)

                delivery_settings = self._delivery_settings
                if instance.delivery_by_own:
                    delivery_settings = getattr(instance, "delivery_settings", None)

                delivery_price = int(
                    calculate_delivering_sum(
                        instance, address, branch=branch, global_delivery_settings=delivery_settings
                    )
                )
                instance.address = branch.address
                instance.delivery_price = delivery_price
                instance.start_time = schedule.start_time
                instance.end_time = schedule.end_time
                instance.is_open_by_schedule = is_open_by_schedule
                instance.min_order_amount = branch.min_order_amount
                instance.package_addition_amount = branch.package_addition_amount
                instance.package_amount = branch.package_amount
                
                

                if branch.is_open == False or schedule.is_active == False:
                    instance.is_open = False
                    if getattr(instance, "has_active_branch"):
                        setattr(instance, "has_active_branch", False)
                    
                if getattr(instance, "has_active_branch", False):
                    instance.is_available = True
                    
            except InstitutionBranchSchedule.DoesNotExist:
                print("No schedule found for", instance.name, instance.start_time, instance.end_time)
            except CantFindSuitableBranchError:
                print("CantFindSuitableBranchError", instance.name, instance.start_time, instance.end_time)
                pass
        return super().to_representation(instance)

    class Meta:
        model = Institution
        fields = [
            "id",
            "name",
            "image",
            "logo",
            "start_time",
            "is_open",
            "is_open_by_schedule",
            "min_delivery_time",
            "max_delivery_time",
            "delivery_price",
            "rating",
        ]

class BannerSerializer(serializers.ModelSerializer):
    img_type = serializers.CharField(read_only=True)
    institutions = serializers.SerializerMethodField()

    def to_representation(self, instance):
        representation = super().to_representation(instance)
        image_file_name: str = representation["img_ru"]
        if (
            image_file_name.endswith(".jpg")
            or image_file_name.endswith(".jpeg")
            or image_file_name.endswith(".png")
            or image_file_name.endswith(".gif")
        ):
            representation["file_type"] = "image"
        else:
            representation["file_type"] = "video"

        return representation
    
    def get_institutions(self, obj):
        rating_subquery = InstitutionFeedback.objects.filter(
            institution=OuterRef("pk")
        ).values("institution").annotate(
            avg_rating=Avg("value")
        ).values("avg_rating")
        
        qs = Institution.objects.filter(
            id__in=obj.restaurants.values_list('id', flat=True)
        ).annotate(
            rating=Subquery(rating_subquery),
            has_active_branch=Case(
                When(
                    is_open=True,
                    then=Exists(
                        InstitutionBranch.objects.get_available().filter(
                            institution=OuterRef("pk"), is_open=True, is_active=True
                        )
                    ),
                ),
                default=Value(False),
                output_field=BooleanField(),
            ),
            is_open_by_schedule=Case(
                When(
                    is_open=True,
                    then=Exists(
                        InstitutionBranch.objects.with_is_open_by_schedule().filter(
                            institution=OuterRef("pk"), is_open_by_schedule=True, is_open=True, is_active=True
                        )
                    ),
                ),
                default=Value(False),
                output_field=BooleanField(),
            ),
            has_active_branch_weight=Case(
                When(has_active_branch=True, then=Value(0)),
                default=Value(1),
                output_field=IntegerField()
            ),
            is_open_weight=Case(
                When(is_open_by_schedule=True, then=Value(0)),
                default=Value(1),
                output_field=IntegerField()
            ),
        ).order_by(
            "has_active_branch_weight",
            "is_open_weight",
            Coalesce("position", Value(999999))
        )

        return InstitutionShortSerializer(qs, many=True, context=self.context).data

    class Meta:
        model = Banner
        fields = [
            "img_ru",
            "img_uz",
            "img_en",
            "is_active",
            "position",
            "img_type",
            "start_date",
            "end_date",
            "title_ru",
            "title_uz",
            "title_en",
            "description",
            "category",
            "restaurants",
            "institutions",
        ]
        read_only_fields = ["img_type"]
