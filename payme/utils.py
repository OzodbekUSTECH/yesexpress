import json
from functools import cache
import requests

from payme.models import PaymePayment
from tuktuk.settings import PAYME_SETTINGS, PAYME_TEST

@cache
def _get_auth_header(is_test = False):

    x_auth_header = f"{PAYME_SETTINGS['merchant_id']}:{PAYME_SETTINGS['key']}"
    if is_test:
        x_auth_header = f"{PAYME_TEST['merchant_id']}:{PAYME_TEST['key']}"
    return {"X-Auth": x_auth_header}

def _create_receipt(session, order, items: list[dict]):
    
    if order.discount_sum > 0:
        detail = {
            "receipt_type": 0,
            "items": items,
            "discount": {
                "title": "Скидка/Промокод",
                "price": order.discount_sum * 100,
            },
        }
    else:
        detail = {"receipt_type": 0, "items": items}
    data = {
        "id": order.id,
        "method": "receipts.create",
        "params": {
            "amount": order.total_sum * 100,
            "account": {"order_id": order.id},
            "detail": detail,
        },
    }
    payment, create=PaymePayment.objects.get_or_create(order=order, total_sum=order.total_sum)
    if int(payment.status) == 4:
        return False

    response = session.post(
        PAYME_SETTINGS["api_url"], data=json.dumps(data), headers=_get_auth_header()
    )
    response_json = response.json()
    print(data, response_json)
    
    if 'result' in response_json:
        payment.create_receipt_request=data
        payment.create_receipt_response=response_json
        payment.receipt_id = response_json['result']['receipt']['_id']
        payment.status = response_json['result']['receipt']['state']
        payment.save()
        
        order.receipt_id=payment.receipt_id
        order.save()
    
    return response_json


def _pay_receipt(session, receipt_id, token):
    data = {
        "id": 1,
        "method": "receipts.pay",
        "params": {"id": receipt_id, "token": token},
    }

    response = session.post(
        PAYME_SETTINGS["api_url"], data=json.dumps(data), headers=_get_auth_header()
    )
    response_json = response.json()
        

    payment = PaymePayment.objects.get(receipt_id=receipt_id)
    payment.pay_receipt_request = data
    payment.pay_receipt_response = response_json
    if 'result' in response_json:
        payment.status = response_json['result']['receipt']['state']
    payment.save()
    
    return response


def make_payment(session, order, token, items: list[dict]):
    session.headers.update(_get_auth_header())
    receipt_creation_response = _create_receipt(session, order, items)
    if receipt_creation_response == False:
        return {'status': 'success', 'message': 'Transaction exists'}
    
    creation_response_data = receipt_creation_response["result"]
    receipt = creation_response_data["receipt"]

    receipt_id = receipt["_id"]
    receipt_paying_response = _pay_receipt(session, receipt_id, token)
    receipt_paying_response_data = receipt_paying_response.json()

    if "error" in receipt_paying_response_data:
        return {'status': 'error', 'message': receipt_paying_response_data['error']['message']}

    paying_response_data = receipt_paying_response_data["result"]

    receipt = paying_response_data["receipt"]
    receipt_state = receipt["state"]
    

    if receipt_paying_response.status_code == 200 and receipt_state == 4:
        order.is_paid = True
        order.status = "accepted"
        order.receipt_id = receipt_id
        order.save()
        # notify(order)

    return {'status': 'success'}


def confirm_payment(receipt_id):
    payload = {"id": 1, "method": "receipts.confirm_hold", "params": {"id": receipt_id}}

    response = requests.post(
        url=PAYME_SETTINGS["api_url"], data=json.dumps(payload), headers=_get_auth_header()
    )
    response_json = response.json()
    
    payment = PaymePayment.objects.filter(receipt_id=receipt_id).first()
    if payment:
        payment.confirm_request = payload
        payment.confirm_response = response_json
        payment.save()


def cancel_payment(receipt_id):
    payload = {"id": 1, "method": "receipts.cancel", "params": {"id": receipt_id}}

    response = requests.post(
        url=PAYME_SETTINGS["api_url"], data=json.dumps(payload), headers=_get_auth_header()
    )
    
    response_json = response.json()
    payment = PaymePayment.objects.filter(receipt_id=receipt_id).first()
    if payment:
        payment.cancel_request = payload
        payment.cancel_response = response_json
        if 'result' in response_json:
            payment.status = response_json['result']['receipt']['state']
        payment.save()

class PaymeApiClient:
    def __init__(self):
        self.base_url = PAYME_SETTINGS["api_url"]
        self.session = requests.Session()
        # self.session.headers.update(_get_auth_header(is_test=True))
        self.session.headers.update({"X-Auth": PAYME_SETTINGS['merchant_id']})

    def add_new_card(self, number: str, expire: str) -> dict | None:
        payload = {
            'id': 1,
            'method': 'cards.create',
            'params': {
                'card': {
                    'number': number,
                    'expire': expire
                },
                'save': True
            }
        }
        response = self.session.post(self.base_url, json=payload)
        if response.ok:
            res = response.json()
            return res['result']['card']['token']
        return None

    def verify_token(self, token: str) -> dict | None:
        payload = {
            'id': 1,
            'method': 'cards.get_verify_code',
            'params': {
                'token': token
            }
        }
        response = self.session.post(self.base_url, json=payload)
        if response.ok:
            res = response.json()
            return res['result']
        return None

    def verify_phone_number(self, code: str, token: str) -> dict | None:
        payload = {
            'id': 123,
            'method': 'cards.verify',
            'params': {
                'token': token,
                'code': code
            }
        }
        response = self.session.post(self.base_url, json=payload)
        return response.json() if response.ok else None
