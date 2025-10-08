class ApplicationError(Exception):
    default_message = "Ошибка приложения"

    def __init__(self, message=None, extra=None):
        super().__init__(message)

        if message is not None:
            self.message = message
        else:
            self.message = self.default_message

        self.extra = extra or {}
