from channels.consumer import SyncConsumer
from django.db.models import Q
from firebase_admin.messaging import (
    Message,
    Notification,
    MulticastMessage,
    AndroidConfig,
    APNSConfig,
    APNSPayload,
    Aps,
    send_each_for_multicast,
    send
)

from order.models import Order
from user.models import CustomFCMDevice, User



class FirebaseConsumer(SyncConsumer):
    def __init__(self):
        super().__init__()

    def courier_new_order_notification(self, message=None):
        message = Message(
            notification=Notification(title="Новый заказ", body="Новый заказ"),
            # data={
            #     "title": f"Новый заказ №{order_id}",
            #     "body": "У вас новый заказ!",
            #     "order_id": str(message["order_id"])
            # }
        )

        couriers = CustomFCMDevice.objects.filter(app_name="courier", active=True)
        print(f"[DEBUG] Found {couriers.count()} courier devices")
        
        response = couriers.send_message(message)
        invalid_ids = response.deactivated_registration_ids

        if invalid_ids:
            CustomFCMDevice.objects.filter(registration_id__in=invalid_ids).delete()

    def institution_new_order_notification(self, message):
        try:
            order = Order.objects.get(pk=message["order_id"])
            
            new_devices = CustomFCMDevice.objects.filter(
                Q(
                    Q(
                        user__worker_branch__institution_branch__in=order.item_groups.all().values_list(
                            "institution_branch", flat=True
                        )
                    )
                    | Q(
                        user__institution_admin__in=order.item_groups.all().values_list(
                            "institution", flat=True
                        )
                    )
                    | Q(
                        user__institution_owner__in=order.item_groups.all().values_list(
                            "institution", flat=True
                        )
                    )
                ),
                active=True,
            )
            
            (f"[DEBUG] Found {new_devices.count()} devices")
            
            msg = Message(
                    data={
                        "title": "Новый заказ",
                        "body": "У вас новый заказ!",
                        "order_id": str(message["order_id"]),
                        "sound": "new_order_2.mp3"  # можно передать, если потребуется использовать имя в iOS, например
                    },
                android=AndroidConfig(
                    priority='high',
                    data={
                        'order_id': str(message["order_id"]),
                    }
                ),
                apns=APNSConfig(
                    headers={"apns-priority": "10"},
                    payload=APNSPayload(
                        aps=Aps(
                            content_available=True,
                            sound="level_up.caf"
                        ),
                        data={
                            'order_id': str(message["order_id"]),
                        }
                    )
                )
            )
            res = new_devices.send_message(msg)
            print(f"[DEBUG] FCM response: {res}")
            invalid_ids = res.deactivated_registration_ids

            if invalid_ids:
                CustomFCMDevice.objects.filter(registration_id__in=invalid_ids).delete()

        except Exception as e:
            import traceback
            print("[ERROR] Failed to send FCM notification", e)
            print(traceback.format_exc())

    def institution_courier_accept_notification(self, message):
        order = Order.objects.get(pk=message["order_id"])
        
        new_devices = CustomFCMDevice.objects.filter(
            Q(
                Q(
                    user__worker_branch__in=order.item_groups.all().values_list(
                        "institution_branch", flat=True
                    )
                )
                | Q(
                    user__institution_admin__in=order.item_groups.all().values_list(
                        "institution", flat=True
                    )
                )
                | Q(
                    user__institution_owner__in=order.item_groups.all().values_list(
                        "institution", flat=True
                    )
                )
            ),
            active=True,
        )
        message = Message(
            # notification=Notification(title=f"Заказ №{message['order_id']} принят курьером", body=""),
            data={
                "title": f"Заказ №{message['order_id']} принят курьером",
                "body": "",
                "order_id": str(message["order_id"])
            }
        )
        
        response = new_devices.send_message(message)

        print(response)
        invalid_ids = response.deactivated_registration_ids

        if invalid_ids:
            CustomFCMDevice.objects.filter(registration_id__in=invalid_ids).delete()

    def institution_cancel_notification(self, message):
        order = Order.objects.get(pk=message["order_id"])
        
        new_devices = CustomFCMDevice.objects.filter(
            Q(
                Q(
                    user__worker_branch__in=order.item_groups.all().values_list(
                        "institution_branch", flat=True
                    )
                )
                | Q(
                    user__institution_admin__in=order.item_groups.all().values_list(
                        "institution", flat=True
                    )
                )
                | Q(
                    user__institution_owner__in=order.item_groups.all().values_list(
                        "institution", flat=True
                    )
                )
            ),
            active=True,
        )
        
        message = Message(
            # notification=Notification(title=f"Заказ №{message['order_id']} отменен", body=""),
            data={
                "title": f"Заказ №{message['order_id']} отменен",
                "body": "",
                "order_id": str(message["order_id"])
            }
        )
        
        response = new_devices.send_message(message)

        print(response)

        invalid_ids = response.deactivated_registration_ids

        if invalid_ids:
            CustomFCMDevice.objects.filter(registration_id__in=invalid_ids).delete()

    def order_courier_ready_notification(self, message):
        order = Order.objects.get(pk=message["order_id"])
        
        if order.courier:
            new_devices = CustomFCMDevice.objects.filter(
                active=True,
                user=order.courier.user
            )

            message = Message(
                notification=Notification(title=f"Заказ №{message['order_id']} готов и ждет вас", body=f"Заказ №{message['order_id']} готов и ждет вас"),
            )

            response = new_devices.send_message(message)
            invalid_ids = response.deactivated_registration_ids

            if invalid_ids:
                CustomFCMDevice.objects.filter(registration_id__in=invalid_ids).delete()

    def send_notification(self, message=None):

        order = Order.objects.get(pk=message["order_id"])
        new_devices = CustomFCMDevice.objects.filter(user=order.customer, active=True)
        
        response = new_devices.send_message(
            Message(
                notification=Notification(title=message["title"], body=message["body"]),
                data={"order_id": str(message["order_id"])},
            ),
        )

        invalid_ids = response.deactivated_registration_ids

        if invalid_ids:
            CustomFCMDevice.objects.filter(registration_id__in=invalid_ids).delete()

def chunked(iterable, n):
    for i in range(0, len(iterable), n):
        yield iterable[i:i + n]

def send_notification_to_all(title, body, data=None, app="client"):
    app_list = {"client": "uz.yesexpress.client.yes_express", "courier": "uz.yesexpress.courier", "vendor": "com.yesexpressvendor"}
    devices = CustomFCMDevice.objects.filter(active=True)
    
    if devices.exists():
        tokens = devices.values_list('registration_id', flat=True).distinct()
        failed_tokens = []
        success_tokens = []
        for chunk in chunked(tokens, 500):
            multicast_message = MulticastMessage(
                notification=Notification(title=title, body=body),
                data={"app_id": app_list[app], **(data or {})},
                tokens=chunk,
            )
            response = send_each_for_multicast(multicast_message)
        
            for idx, res in enumerate(response.responses):
                if not res.success:
                    failed_tokens.append(tokens[idx])
                else:
                    success_tokens.append(tokens[idx])
            CustomFCMDevice.objects.filter(registration_id__in=failed_tokens).update(active=False)
            
        return {"status": "ok", "data": {"success": len(success_tokens), "fail": len(failed_tokens)}, "error": ""}
    else:
        return {"status": "error", "data": [], "error": "Aktiv token yo'q"}
        
    
def send_notification_by_phone_number(phone_number, title, body, data=None, app="client"):
    try:
        app_list = {"client": "uz.yesexpress.client.yes_express", "courier": "uz.yesexpress.courier", "vendor": "com.yesexpressvendor"}
        user = User.objects.filter(phone_number=phone_number).first() or User.objects.filter(pk=phone_number).first()
        device = CustomFCMDevice.objects.filter(user=user, active=True).first()
        if device:
            message = Message(
                notification=Notification(
                    title=title,
                    body=body,
                ),
                data={"app_id": app_list[app], **(data or {})},
                token=device.registration_id,
            )
            response = send(message)
            return {"status": "ok", "data": {"success": 1, "fail": 0}, "error": ""}
        else:
            return {"status": "error", "data": [], "error": "Aktiv token yo'q"}

    except User.DoesNotExist:
        return "Telefon raqamiga mos foydalanuvchi topilmadi."