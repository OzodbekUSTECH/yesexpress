from datetime import datetime

from django.db import models
from django.db.models import When, Case, F, Value, Q, OuterRef, ExpressionWrapper, Exists, BooleanField
from django.db.models.functions import Cast, Sin, Cos, Radians
from django.forms import FloatField

from modeltrans.manager import MultilingualQuerySet

from base.enums import DayOfWeekChoices
from base.managers import FlagsQuerySet
from django.db.models import FloatField
from django.db.models.functions import Sqrt, ASin


class InstitutionQuerySet(MultilingualQuerySet):
    def with_is_open_by_schedule(self, now=None):
        if not now:
            now = datetime.now().time()

        return self.annotate(
            is_open_by_schedule=Case(
                When(
                    start_time__lt=F("end_time"),
                    then=Case(
                        When(start_time__lt=now, end_time__gt=now, then=True),
                        default=False,
                        output_field=models.BooleanField(),
                    ),
                ),
                default=Case(
                    When(Q(start_time__lt=now) | Q(end_time__gt=now), then=True),
                    default=False,
                    output_field=models.BooleanField(),
                ),
                output_field=models.BooleanField(),
            ),
        )

    def get_available(self):
        return self.filter(is_deleted=False, is_active=True)

    def get_active(self):
        return self.filter(is_active=True)

    def get_not_deleted(self):
        return self.filter(is_deleted=False)


class InstitutionManager(models.Manager):
    def get_queryset(self):
        return InstitutionQuerySet(self.model)


class InstitutionBranchManager(FlagsQuerySet):
    def with_is_open_by_schedule(self, now=None):
        from institution.models import InstitutionBranchSchedule

        if not now:
            now = datetime.now()

        current_time = now.time()
        weekday = DayOfWeekChoices.get_value_by_number(now.weekday())
        normal_hours = InstitutionBranchSchedule.objects.filter(
            institution_id=OuterRef("pk"),
            is_active=True,
            day_of_week=weekday,
            start_time__lt=F('end_time'),
            start_time__lte=current_time,
            end_time__gte=current_time,
        )

        # Подзапрос для ночных графиков (start > end, например 22:00 - 06:00)
        overnight_hours = InstitutionBranchSchedule.objects.filter(
            institution_id=OuterRef("pk"),
            is_active=True,
            day_of_week=weekday,
            start_time__gt=F('end_time'),
        ).filter(
            Q(start_time__lte=current_time) | Q(end_time__gte=current_time)
        )

        return self.annotate(
            is_open_by_schedule=Case(
                When(Exists(normal_hours), then=True),
                When(Exists(overnight_hours), then=True),
                default=False,
                output_field=BooleanField(),
            )
        )

    def with_distance(self, latitude, longitude):
        earth_radius_km = 6371.0

        # Перевод широты и долготы в радианы
        rad_lat = Radians(Value(latitude, output_field=FloatField()))
        rad_long = Radians(Value(longitude, output_field=FloatField()))
        rad_obj_lat = Radians(Cast(F("address__latitude"), output_field=FloatField()))
        rad_obj_long = Radians(Cast(F("address__longitude"), output_field=FloatField()))

        # Разница координат
        dlat = rad_obj_lat - rad_lat
        dlong = rad_obj_long - rad_long

        # Формула Haversine
        a = Sin(dlat / 2) ** 2 + Cos(rad_lat) * Cos(rad_obj_lat) * Sin(dlong / 2) ** 2
        c = 2 * ASin(Sqrt(a))

        # Вычисление расстояния
        distance_expression = ExpressionWrapper(earth_radius_km * c, output_field=FloatField())

        return self.annotate(distance=distance_expression)

