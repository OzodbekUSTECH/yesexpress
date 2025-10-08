from order.promo_codes.models import PromoCodeUsage, PromoCode


class PromoCodeService:
    def __init__(self, promo_code: PromoCode):
        self.promo_code = promo_code

    def get_sum(self):
        return self.promo_code.sum

    def get_min_order_sum(self):
        return self.promo_code.min_order_sum

    def use(self, user, order):
        promo = PromoCode.objects.filter(code=self.promo_code, is_active=True, status='active')
        if promo:
            PromoCodeUsage.objects.create(user=user, promo_code=self.promo_code, order=order)
        # if self.promo_code.revokable:
            # self.promo_code.is_active = False
            # self.promo_code.save()
