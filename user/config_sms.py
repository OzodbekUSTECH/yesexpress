from django.conf import settings


class Config:
    URL = settings.PLAY_MOBILE_SETTINGS["API_URL"]
    LOGIN = settings.PLAY_MOBILE_SETTINGS["LOGIN"]
    PASSWORD = settings.PLAY_MOBILE_SETTINGS["PASSWORD"]
    NICKNAME = settings.PLAY_MOBILE_SETTINGS["ORIGINATOR"]
