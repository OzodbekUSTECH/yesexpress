import os
import requests
import redis

import pytz
import random
from datetime import datetime, timedelta

def create_random_date():

    tz = pytz.timezone("Asia/Tashkent")

    now = datetime.now(tz)

    minutes_to_add = random.choice([15, 20, 25])

    new_time = now + timedelta(minutes=minutes_to_add)

    print(new_time.isoformat())
    return new_time.isoformat()

class rkeeperAPI:
    BASE_URL = "https://yesexpress.burgerandco.deliveryhub.uz"
    TOKEN_EXPIRE_SECONDS = 3600
    
    def __init__(self, endpoint_url, client_id, client_secret):
        print(os.getenv("REDIS_HOST"), os.getenv("REDIS_PORT"))
        self.endpoint_url = endpoint_url or self.BASE_URL
        self.client_id = client_id
        self.client_secret = client_secret
        self.TOKEN_KEY = f"{client_id}_{client_secret}"
        self.redis = redis.StrictRedis(host=os.getenv("REDIS_HOST"), port=os.getenv("REDIS_PORT"), db=0, decode_responses=True)
        self.token = None 

    def _get_headers(self):
        if not self.token:
            self.get_token()
        return {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json"
        }

    def get_token(self):
        token = self.redis.get(self.TOKEN_KEY)
        if token:
            print("REDISDAN TOKEN ---------------------------", token)
            self.token = token
            return token
        
        url = f"{self.endpoint_url}/security/oauth/token"
        data = {
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "grant_type": "client_credentials"
        }
        headers = {"Content-Type": "application/x-www-form-urlencoded"}
        response = requests.post(url, data=data, headers=headers)
        response.raise_for_status()
        
        response_data = response.json()
        token = response_data["access_token"]
        expires_in = response_data.get("expires_in", self.TOKEN_EXPIRE_SECONDS)

        # Redisga tokenni saqlaymiz
        self.redis.set(self.TOKEN_KEY, token, ex=expires_in - 60)  # xavfsizlik uchun 1 daqiqa kamroq
        self.token = token
        return token

    def get_restaurants(self):
        url = f"{self.endpoint_url}/restaurants"
        response = requests.get(url, headers=self._get_headers())
        return response.json()

    def get_menu(self, restaurant_id):
        url = f"{self.endpoint_url}/menu/{restaurant_id}/composition"
        headers = self._get_headers()
        headers["Accept"] = "application/vnd.eats.menu.composition.v2+json"
        response = requests.get(url, headers=headers)
        json_data = response.json()
        return json_data

    def get_stop_list(self, restaurant_id):
        url = f"{self.endpoint_url}/menu/{restaurant_id}/availability"
        response = requests.get(url, headers=self._get_headers())
        return response.json()

    def create_order(self, order_data):
        url = f"{self.endpoint_url}/order"
        response = requests.post(url, json=order_data, headers=self._get_headers())
        return response.json()

    def get_order_info(self, order_id):
        url = f"{self.endpoint_url}/order/{order_id}"
        response = requests.get(url, headers=self._get_headers())
        return response.json()

    def get_order_status(self, order_id):
        url = f"{self.endpoint_url}/order/{order_id}/status"
        response = requests.get(url, headers=self._get_headers())
        return response.json()

    def cancel_order(self, order_id, eats_id, comment):
        url = f"{self.endpoint_url}/order/{order_id}"
        payload = {
            "eatsId": eats_id,
            "comment": comment
        }
        response = requests.delete(url, json=payload, headers=self._get_headers())
        return response.json()


    def make_order(self, order):
        item_groups = order.item_groups.first()
        branch = item_groups.institution_branch
        restaurant_id = branch.places_id
        courier = order.courier
        payment_type = "CARD" if order.payment_method == 'payme' else "CASH"
        items = []
        all_items = item_groups.items.all()
        for item in all_items:
            _item = {"id": str(item.product.uuid), "modifications": [], "price": item.product.price, "quantity": len(all_items), "promos": [], "name": item.product.name_ru}
            for option in item.options.all():
                _item['modifications'].append({"id":  str(option.uuid), "name": option.title_ru, "quantity": len(all_items), "price": option.adding_price})
            items.append(_item)


        _order = {
            "discriminator": "yesexpress",
            "comment": order.note,
            "eatsId": str(order.id),
            "restaurantId": restaurant_id,
            "deliveryInfo": {
                "clientName": courier.user.first_name,
                "phoneNumber": courier.user.phone_number,
                "courierArrivementDate": create_random_date()
            },
            "paymentInfo": {
                "itemsCost": order.products_sum,
                "paymentType": payment_type
            },
            "items": items,
            "promos": [],
            "persons": 0
        }
        print(_order)
        response = self.create_order(_order)
        if response and isinstance(response, dict):
            order.uuid = response.get('orderId', None)
            order.save()
