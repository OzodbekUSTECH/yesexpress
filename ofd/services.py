import json
import os
import subprocess
import uuid
from datetime import datetime

import pytz
import requests
from cryptography import x509
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.x509.oid import NameOID
from django.conf import settings
from django.db import transaction

from common.models import Settings
from ofd.exceptions import ReceiptDataSigningError
from ofd.models import OFDReceipt, OFDCertificate
from order.models import OrderItem
from payment.models import Payment


def get_ofd_receipt_type_code(receipt_type: OFDReceipt.ReceiptTypes):
    receipt_type_str_to_code = {
        OFDReceipt.ReceiptTypes.SALE: 0,
        OFDReceipt.ReceiptTypes.PREPAYMENT: 1,
        OFDReceipt.ReceiptTypes.CREDIT: 2,
    }
    return receipt_type_str_to_code.get(receipt_type, None)


class CSRCertificateRegistrator:
    def _generate_csr(self, company_name, user_id):
        # Генерация приватного ключа RSA 2048
        private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)

        # Сохранение приватного ключа
        with open("user-etp.key", "wb") as key_file:
            key_file.write(
                private_key.private_bytes(
                    encoding=serialization.Encoding.PEM,
                    format=serialization.PrivateFormat.TraditionalOpenSSL,
                    encryption_algorithm=serialization.NoEncryption(),
                )
            )

        csr = (
            x509.CertificateSigningRequestBuilder()
            .subject_name(
                x509.Name(
                    [
                        x509.NameAttribute(NameOID.COMMON_NAME, company_name),
                        x509.NameAttribute(NameOID.USER_ID, user_id),
                    ]
                )
            )
            .sign(private_key, hashes.SHA256())
        )

        # Сохранение CSR в файл
        with open("user-etp.csr", "wb") as csr_file:
            csr_file.write(csr.public_bytes(serialization.Encoding.PEM))

        return "user-etp.csr"


class OFDReceiptService:
    OFD_URL = settings.OFD_URL
    OFD_CERT = settings.OFD_CERT

    def __init__(self, payment: Payment):
        self.payment = payment
        self.certificate = OFDCertificate.get_active_certificate()

    def create_sale_receipt(self):
        """Отправляет чек продажи в ОФД и сохраняет ответ"""

        if not self.certificate:
            return None

        if self.payment.ofd_receipts.filter(
            receipt_type=OFDReceipt.ReceiptTypes.SALE,
            refund_receipt__isnull=True,
        ).exists():
            return None

        with transaction.atomic():
            prepayment_receipt = self.payment.ofd_receipts.filter(
                receipt_type=OFDReceipt.ReceiptTypes.PREPAYMENT,
            ).first()

            receipt = OFDReceipt.objects.create(
                payment=self.payment,
                receipt_type=OFDReceipt.ReceiptTypes.SALE,
                certificate=self.certificate,
                advance_contract_id=prepayment_receipt.advance_contract_id
                if prepayment_receipt
                else None,
            )
            receipt_data = self._generate_sale_receipt_json(receipt_seq=receipt.receipt_seq)

            try:
                response_data = self._send_request(receipt_data)
            except ReceiptDataSigningError:
                transaction.set_rollback(True)
                return None
            except requests.RequestException as e:
                print(f"Ошибка запроса: {e}")
                transaction.set_rollback(True)
                return None

            print(response_data)
            if response_data.get("Code") == 0:  # Успешный ответ
                receipt.receipt_seq = response_data["ReceiptSeq"]
                receipt.terminal_id = response_data["TerminalID"]
                receipt.fiscal_sign = response_data["FiscalSign"]
                receipt.qr_code_url = response_data["QRCodeURL"]
                receipt.receipt_date = self._convert_to_datetime(response_data.get("DateTime"))
                receipt.save()
                return receipt
            else:
                print(f"Ошибка ОФД: {response_data}")
                transaction.set_rollback(True)
                return None

    def create_refund_receipt(self, refunding_receipt: OFDReceipt):
        if not self.certificate:
            return None

        with transaction.atomic():
            # sale_receipt = self.payment.ofd_receipts.select_for_update().filter(
            #     receipt_type=OFDReceipt.ReceiptTypes.SALE,
            #     refund_receipt__isnull=True
            # ).first()
            # print(sale_receipt)

            if refunding_receipt.refund_receipt:
                return None

            if refunding_receipt.payment != self.payment:
                return None

            refund_receipt = OFDReceipt.objects.create(
                payment=self.payment,
                receipt_type=OFDReceipt.ReceiptTypes.REFUND,
                certificate=self.certificate,
                advance_contract_id=refunding_receipt.advance_contract_id,
            )

            if refunding_receipt.receipt_type == OFDReceipt.ReceiptTypes.SALE:
                receipt_data = self._generate_sale_receipt_json(
                    receipt_seq=refund_receipt.receipt_seq,
                    contract_id=refund_receipt.advance_contract_id,
                    is_refund=True,
                    refunding_receipt=refunding_receipt,
                )
            elif refunding_receipt.receipt_type == OFDReceipt.ReceiptTypes.PREPAYMENT:
                receipt_data = self._generate_prepayment_receipt_json(
                    receipt_seq=refund_receipt.receipt_seq,
                    contract_id=refunding_receipt.advance_contract_id,
                    is_refund=True,
                    refunding_receipt=refunding_receipt,
                )
            else:
                receipt_data = None

            try:
                response_data = self._send_request(receipt_data)
            except ReceiptDataSigningError:
                transaction.set_rollback(True)
                return None
            except requests.RequestException as e:
                print(f"Ошибка запроса: {e}")
                transaction.set_rollback(True)
                return None

            print(response_data)
            if response_data.get("Code") == 0:  # Успешный ответ
                refund_receipt.receipt_seq = response_data["ReceiptSeq"]
                refund_receipt.terminal_id = response_data["TerminalID"]
                refund_receipt.fiscal_sign = response_data["FiscalSign"]
                refund_receipt.qr_code_url = response_data["QRCodeURL"]
                refund_receipt.receipt_date = self._convert_to_datetime(
                    response_data.get("DateTime")
                )
                refund_receipt.save()

                refunding_receipt.refund_receipt = refund_receipt
                refunding_receipt.save()
                return refund_receipt
            else:
                print(f"Ошибка ОФД: {response_data}")
                transaction.set_rollback(True)
                return None

    def create_prepayment_receipt(self):
        if not self.certificate:
            return None

        with transaction.atomic():
            if self.payment.ofd_receipts.filter(
                receipt_type=OFDReceipt.ReceiptTypes.SALE,
                refund_receipt__isnull=True,
            ).exists():
                return None

            existed_prepayment_receipt = self.payment.ofd_receipts.filter(
                receipt_type=OFDReceipt.ReceiptTypes.PREPAYMENT,
                refund_receipt__isnull=True,
            ).first()

            contract_id = (
                existed_prepayment_receipt.advance_contract_id
                if existed_prepayment_receipt
                else uuid.uuid4()
            )

            receipt = OFDReceipt.objects.create(
                payment=self.payment,
                receipt_type=OFDReceipt.ReceiptTypes.PREPAYMENT,
                certificate=self.certificate,
                advance_contract_id=contract_id,
            )
            receipt_data = self._generate_prepayment_receipt_json(
                receipt_seq=receipt.receipt_seq, contract_id=contract_id
            )

            try:
                response_data = self._send_request(receipt_data)
            except ReceiptDataSigningError:
                transaction.set_rollback(True)
                return None
            except requests.RequestException as e:
                print(f"Ошибка запроса: {e}")
                transaction.set_rollback(True)
                return None

            print(response_data)
            if response_data.get("Code") == 0:  # Успешный ответ
                receipt.receipt_seq = response_data["ReceiptSeq"]
                receipt.terminal_id = response_data["TerminalID"]
                receipt.fiscal_sign = response_data["FiscalSign"]
                receipt.qr_code_url = response_data["QRCodeURL"]
                receipt.receipt_date = self._convert_to_datetime(response_data.get("DateTime"))
                receipt.save()

                return receipt
            else:
                print(f"Ошибка ОФД: {response_data}")
                transaction.set_rollback(True)
                return None

    def create_credit_receipt(self):
        if not self.certificate:
            return None

        with transaction.atomic():
            sale_receipt = self.payment.ofd_receipts.filter(
                receipt_type=OFDReceipt.ReceiptTypes.SALE,
                refund_receipt__isnull=True,
            ).first()
            if not sale_receipt:
                sale_receipt = self.create_sale_receipt()

            receipt = OFDReceipt.objects.create(
                payment=self.payment,
                receipt_type=OFDReceipt.ReceiptTypes.CREDIT,
                certificate=self.certificate,
            )
            receipt_data = self._generate_credit_receipt_json(
                receipt_seq=receipt.receipt_seq, sale_receipt=sale_receipt
            )

            try:
                response_data = self._send_request(receipt_data)
            except ReceiptDataSigningError:
                transaction.set_rollback(True)
                return None
            except requests.RequestException as e:
                print(f"Ошибка запроса: {e}")
                transaction.set_rollback(True)
                return None

            print(response_data)
            if response_data.get("Code") == 0:  # Успешный ответ
                receipt.receipt_seq = response_data["ReceiptSeq"]
                receipt.terminal_id = response_data["TerminalID"]
                receipt.fiscal_sign = response_data["FiscalSign"]
                receipt.qr_code_url = response_data["QRCodeURL"]
                receipt.receipt_date = self._convert_to_datetime(response_data.get("DateTime"))
                receipt.save()

                return receipt
            else:
                print(f"Ошибка ОФД: {response_data}")
                transaction.set_rollback(True)
                return None

    def _send_request(self, receipt_data):
        print(receipt_data)
        try:
            signed_receipt = self._sign_receipt_data(receipt_data)
        except Exception as e:
            print(f"Ошибка при подписании: {e}")
            raise ReceiptDataSigningError
            # transaction.set_rollback(True)
            # return None

        headers = {"Content-Type": "application/octet-stream"}
        try:
            response = requests.post(
                self.OFD_URL, headers=headers, data=signed_receipt, verify=False
            )
            response_data = response.json()
            return response_data
        except requests.RequestException as e:
            print(f"Ошибка запроса: {e}")
            raise e

    def _sign_receipt_data(self, receipt_data):
        """Подписывает JSON с чеком с помощью OpenSSL"""
        json_file = "receipt.json"
        signed_file = "receipt.p7b"
        # private_key = "certs/user-etp.key"
        # cert_file = "certs/user-etp.crt"
        private_key = "certs/yes-user.key"
        cert_file = self.certificate.certificate_path

        # Записываем JSON в файл
        with open(json_file, "w", encoding="utf-8") as f:
            json.dump(receipt_data, f, ensure_ascii=False, indent=4)

        # Подписываем JSON с помощью OpenSSL
        cmd = [
            "openssl",
            "cms",
            "-sign",
            "-nodetach",
            "-binary",
            "-in",
            json_file,
            "-outform",
            "der",
            "-out",
            signed_file,
            "-nocerts",
            "-signer",
            cert_file,
            "-inkey",
            private_key,
        ]

        try:
            subprocess.run(cmd, check=True)
        except subprocess.CalledProcessError as e:
            os.remove(json_file)
            raise Exception(f"Ошибка при подписании: {e}")

        # Читаем подписанный файл
        with open(signed_file, "rb") as f:
            signed_data = f.read()

        # Удаляем временные файлы
        os.remove(json_file)
        os.remove(signed_file)

        return signed_data

    def _generate_sale_receipt_json(
        self, receipt_seq, contract_id=None, is_refund=False, refunding_receipt: OFDReceipt = None
    ):
        response = self._generate_receipt_json(
            receipt_type=OFDReceipt.ReceiptTypes.SALE,
            receipt_seq=receipt_seq,
            is_refund=is_refund,
            refunding_receipt=refunding_receipt,
        )

        if contract_id:
            response["AdvanceContractID"] = str(contract_id)

        if is_refund:
            response["RefundInfo"]["FiscalSign"] = refunding_receipt.fiscal_sign
        return response

    def _generate_prepayment_receipt_json(
        self, receipt_seq, contract_id, is_refund=False, refunding_receipt: OFDReceipt = None
    ):
        response = self._generate_receipt_json(
            receipt_type=OFDReceipt.ReceiptTypes.PREPAYMENT,
            receipt_seq=receipt_seq,
            is_refund=is_refund,
            refunding_receipt=refunding_receipt,
        )

        response["AdvanceContractID"] = str(contract_id)
        print(response)

        return response

    def _generate_credit_receipt_json(
        self, receipt_seq, sale_receipt, is_refund=False, refunding_receipt: OFDReceipt = None
    ):
        response = self._generate_receipt_json(
            receipt_type=OFDReceipt.ReceiptTypes.CREDIT,
            receipt_seq=receipt_seq,
            is_refund=is_refund,
            refunding_receipt=refunding_receipt,
        )

        response["SaleReceiptInfo"] = {
            "TerminalID": sale_receipt.terminal_id,
            "ReceiptSeq": str(sale_receipt.receipt_seq),
            "DateTime": sale_receipt.receipt_date.astimezone(
                pytz.timezone("Asia/Tashkent")
            ).strftime("%Y%m%d%H%M%S"),
            "FiscalSign": sale_receipt.fiscal_sign,
        }
        print(response)

        return response

    def _generate_receipt_json(
        self, receipt_type, receipt_seq, is_refund=False, refunding_receipt: OFDReceipt = None
    ):
        items = self._generate_items_data()
        response = {
            "ReceiptSeq": int(receipt_seq),
            "IsRefund": 1 if is_refund else 0,
            "Items": items,
            "ReceivedCash": int(self.payment.amount * 100)
            if self.payment.payment_method == "cash"
            else 0,
            "ReceivedCard": int(self.payment.amount * 100)
            if self.payment.payment_method != "cash"
            else 0,
            "TotalVAT": sum(item["VAT"] for item in items),
            "Time": self.payment.created_at.astimezone(pytz.timezone("Asia/Tashkent")).strftime(
                "%Y-%m-%d %H:%M:%S"
            ),
            "ReceiptType": get_ofd_receipt_type_code(receipt_type),  # 0 - продажа
        }

        if is_refund:
            response["RefundInfo"] = {
                "TerminalID": refunding_receipt.terminal_id,
                "ReceiptSeq": str(refunding_receipt.receipt_seq),
                "DateTime": refunding_receipt.receipt_date.astimezone(
                    pytz.timezone("Asia/Tashkent")
                ).strftime("%Y%m%d%H%M%S"),
            }

        return response

    def _generate_items_data(self):
        app_settings = Settings.load()
        order = self.payment.order
        order_items = OrderItem.objects.filter(order_item_group__order=order)
        institution = order.item_groups.first().institution if order.item_groups.exists() else None
        branch = order.item_groups.first().institution_branch if order.item_groups.exists() else None
        institution_tin = institution.inn if institution and institution.inn else None

        items = []

        for item in order_items:
            items.append(
                {
                    "Name": item.product.name,
                    "SPIC": item.product.spic_id,
                    "PackageCode": item.product.package_code,
                    "GoodPrice": int(item.price * 100),
                    "Price": int(item.total_sum * 100),
                    "VAT": int(item.total_sum * item.product.vat / (item.product.vat + 100)) * 100,
                    "VATPercent": item.product.vat,
                    "Amount": item.count * 1000,
                    "OwnerType": 0,
                    "Discount": 0,
                    "CommissionInfo": {
                        "TIN": institution_tin
                    }
                }
            )
        if order.package_quantity > 0:
            items.append(
                {
                    "Name": "Пакет",
                    "SPIC": branch.package_spic_id,
                    "PackageCode": branch.package_code,
                    "GoodPrice": int(branch.package_amount) * 100,
                    "Price": int(order.package_quantity * branch.package_amount) * 100,
                    "VAT": int(
                        branch.package_amount
                        * branch.package_vat
                        / (branch.package_vat + 100)
                    )
                    * 100,
                    "VATPercent": int(branch.package_vat),
                    "Amount": 1000,
                    "OwnerType": 0,
                    "Discount": 0,
                    "CommissionInfo": {
                        "TIN": institution_tin
                    }
                }
            )
        items.append(
            {
                "Name": "Доставка еды",
                "SPIC": settings.DELIVERY_SPIC,
                "PackageCode": settings.DELIVERY_PACKAGE_CODE,
                "GoodPrice": int(order.delivering_sum) * 100,
                "Price": int(order.delivering_sum) * 100,
                "VAT": int(
                    order.delivering_sum
                    * app_settings.delivery_service_vat_percent
                    / (app_settings.delivery_service_vat_percent + 100)
                )
                * 100,
                "VATPercent": int(app_settings.delivery_service_vat_percent),
                "Amount": 1000,
                "OwnerType": 2,
                "Discount": 0,
                "CommissionInfo": {
                    "TIN": settings.STIR
                }
            }
        )
        return items

    def _convert_to_datetime(self, date_str):
        return datetime.strptime(date_str, "%Y%m%d%H%M%S")
