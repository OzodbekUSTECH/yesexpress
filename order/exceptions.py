from core.exceptions import ApplicationError


class CantFindSuitableBranchError(ApplicationError):
    default_message = "Не удалось найти подходящий филиал"
