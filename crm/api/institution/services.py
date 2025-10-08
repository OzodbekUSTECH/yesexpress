import base.enums
from base.helpers import set_obj_deleted
from institution.models import Institution, InstitutionBranch, InstitutionBranchSchedule
from user.services import handle_user_delete


def handle_institution_delete(institution: Institution, user):
    set_obj_deleted(institution, user)
    handle_user_delete(institution.admin)
    handle_user_delete(institution.owner)


def create_institution_default_schedule(institution_branch: InstitutionBranch):
    days_of_week = base.enums.DayOfWeekChoices.values
    for day in days_of_week:
        InstitutionBranchSchedule.objects.get_or_create(
            institution=institution_branch, day_of_week=day
        )


def create_or_update_institution_schedule_days(
    institution_branch: InstitutionBranch,
    days_of_week,
    start_time,
    end_time,
):
    for day in days_of_week:
        InstitutionBranchSchedule.objects.update_or_create(
            institution=institution_branch,
            day_of_week=day,
            defaults={"start_time": start_time, "end_time": end_time},
        )
