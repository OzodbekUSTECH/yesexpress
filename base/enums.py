from django.db import models


class DayOfWeekChoices(models.TextChoices):
    MONDAY = ("MONDAY", "Понедельник")
    TUESDAY = ("TUESDAY", "Вторник")
    WEDNESDAY = ("WEDNESDAY", "Среда")
    THURSDAY = ("THURSDAY", "Четверг")
    FRIDAY = ("FRIDAY", "Пятница")
    SATURDAY = ("SATURDAY", "Суббота")
    SUNDAY = ("SUNDAY", "Воскресенье")

    @staticmethod
    def get_value_by_number(number: int):
        day_to_number_map = {
            0: DayOfWeekChoices.MONDAY,
            1: DayOfWeekChoices.TUESDAY,
            2: DayOfWeekChoices.WEDNESDAY,
            3: DayOfWeekChoices.THURSDAY,
            4: DayOfWeekChoices.FRIDAY,
            5: DayOfWeekChoices.SATURDAY,
            6: DayOfWeekChoices.SUNDAY,
        }
        if number not in day_to_number_map.keys():
            return None
        return day_to_number_map[number]
