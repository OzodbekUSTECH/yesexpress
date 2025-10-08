from django.db.models import Model, Manager, When, Case, Value


class OrderManager(Manager):
    def sorted_by_condition(self):
        return self.get_queryset().order_by(
            Case(  # сначала по статусам
                When(status="pre-order", then=Value(1)),
                When(status="created", then=Value(2)),
                When(status="pending", then=Value(3)),
                When(status="accepted", then=Value(4)),
                When(status="ready", then=Value(5)),
                default=Value(10),
            ),
            "-updated_at",  # потом по времени обновления
        )
