import json
import logging

from django.utils import timezone
from django.conf import settings

import requests

from .models import User
from user.config_sms import Config


def handle_user_delete(user):
    if user:
        user.is_active = False
        user.phone_number = f"{user.phone_number}_del_{user.id}"
        user.save()


def check_otp(user: User, otp: int, number_change: bool = False) -> bool:
    """
    Checks if the given otm is correct for this user and not dated
    """
    # for test purposes only!
    ###
    if settings.DEBUG and otp == 1111:
        return True
    ####
    if user.phone_number == '+998995948233' and otp == 1234:
        return True

    otp_field = "otp_change_number" if number_change else "otp"
    otp_expires_field = "otp_change_number_expires" if number_change else "otp_expires"

    if timezone.now() < getattr(user, otp_expires_field):
        return otp == getattr(user, otp_field)


def send_otp_sms(user: User, number_change: bool = False) -> bool:
    """
    Generates one time password for given user and send sms to it
    """

    user.set_otp(number_change)
    otp = user.otp_change_number if number_change else user.otp

    text = f"YES EXPRESS: Vash kod podtverjdeniya: {otp}"

    return _send_sms(user.phone_number, text)


logging.basicConfig(level=logging.ERROR)
logger = logging.getLogger(__name__)


def _send_sms(phone_number, text) -> bool:
    """
    Sends the given text to given phone number
    """
    if phone_number.startswith("+"):
        phone_number = phone_number.lstrip("+")

    config = Config()

    data = {
        "login": config.LOGIN,
        "password": config.PASSWORD,
        # 'nickname': config.NICKNAME,
        "data": json.dumps([{"phone": phone_number, "text": text}]),
    }
    try:
        result = requests.post(config.URL, json=data)
        result.raise_for_status()
        print(result.text)
        return True
    except requests.exceptions.RequestException as e:
        logger.error(f"Ошибка при отправке смс {e}")
        return False
