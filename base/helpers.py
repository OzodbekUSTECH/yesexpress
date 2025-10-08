from django.utils import timezone


def set_obj_deleted(obj, user):
    obj.is_active = False
    obj.is_deleted = True
    obj.deleted_at = timezone.now()
    obj.deleted_user = user
    obj.save()
