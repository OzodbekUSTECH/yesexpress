from django import forms
from django.contrib.auth.forms import UserCreationForm, PasswordChangeForm
from django.forms import Form, DateField, DateInput, inlineformset_factory

from address.models import Address
from courier.models import DeliverySettings, Courier
from institution.models import Institution
from order.models import PAYMENT_METHODS
from product.models import Product, ProductCategory, ProductOption, OptionItem
from user.models import User


class InstitutionForm(forms.ModelForm):
    class Meta:
        model = Institution
        fields = [
            "logo",
            "image",
            "description_ru",
            "description_uz",
            "description_en",
            "phone_number",
            "start_time",
            "end_time",
            "max_delivery_time",
            "min_delivery_time",
        ]


class InstitutionAddressForm(forms.ModelForm):
    class Meta:
        model = Address
        fields = ["street", "reference_point", "latitude", "longitude"]


class InstitutionAdminForm(UserCreationForm):
    class Meta:
        model = User
        fields = ["phone_number", "first_name", "last_name", "password1", "password2"]


class ProductForm(forms.ModelForm):
    class Meta:
        model = Product
        fields = [
            "image",
            "name_ru",
            "name_uz",
            "name_en",
            "description_uz",
            "description_ru",
            "description_en",
            "status",
            "price",
            "category",
        ]


class CategoryForm(forms.ModelForm):
    class Meta:
        model = ProductCategory
        fields = ["name_ru", "name_uz", "name_en", "position", "institution"]


class DeliverySettingsForm(forms.ModelForm):
    class Meta:
        model = DeliverySettings
        fields = ["min_distance", "min_delivery_price", "price_per_km"]


class ChangePasswordForm(PasswordChangeForm):
    old_password = forms.CharField(
        widget=forms.PasswordInput(attrs={"class": "form-control"}), label="Старый пароль"
    )
    new_password1 = forms.CharField(
        widget=forms.PasswordInput(attrs={"class": "form-control"}), label="Новый пароль"
    )
    new_password2 = forms.CharField(
        widget=forms.PasswordInput(attrs={"class": "form-control"}), label="Подтверждение пароля"
    )


class InstitutionOrderReportFilterForm(Form):
    date_range_after = DateField(
        widget=DateInput(attrs={"class": "form-control", "type": "date"}),
        label="от",
        required=False,
    )
    date_range_before = DateField(
        widget=DateInput(attrs={"class": "form-control", "type": "date"}),
        label="до",
        required=False,
    )


class OrderFilterForm(forms.Form):
    payment_methods = [("", "--------")] + list(PAYMENT_METHODS)

    statuses = (
        ("", "--------"),
        ("created", "создан"),
        ("pending", "ожидает оплаты"),
        ("accepted", "принят и готовится"),
        ("rejected", "отменен"),
        ("ready", "готов"),
        ("shipped", "в пути"),
        ("closed", "закрыт"),
    )

    f_created_at_after = forms.DateField(
        widget=forms.DateInput(attrs={"class": "vDateField", "type": "date"}),
        label="от",
        required=False,
    )
    f_created_at_before = forms.DateField(
        widget=forms.DateInput(attrs={"class": "vDateField", "type": "date"}),
        label="до",
        required=False,
    )
    status = forms.ChoiceField(
        widget=forms.Select(), choices=statuses, required=False, label="Статус"
    )
    institution = forms.ModelChoiceField(
        queryset=Institution.objects.all(), required=False, label="Заведение"
    )
    payment_method = forms.ChoiceField(
        choices=payment_methods, required=False, label="Метод оплаты"
    )


form_control_text_input = forms.TextInput(attrs={"class": "form-control"})
form_control_number_input = forms.NumberInput(attrs={"class": "form-control"})


class CourierUpdateForm(forms.ModelForm):
    passport_series = forms.CharField(widget=form_control_text_input, label="Серия паспорта")
    transport = forms.ChoiceField(
        label="Транспорт",
        widget=forms.Select(attrs={"class": "form-control"}),
        choices=Courier.Transport.choices,
    )
    balance = forms.IntegerField(
        label="Баланс",
        widget=forms.NumberInput(attrs={"class": "form-control disabled"}),
        disabled=True,
    )
    status = forms.ChoiceField(
        label="Статус",
        widget=forms.Select(attrs={"class": "form-control disabled"}),
        disabled=True,
        choices=Courier.Status.choices,
    )

    class Meta:
        model = Courier
        fields = "passport_series", "transport", "balance", "status"


class OptionForm(forms.ModelForm):
    class Meta:
        model = ProductOption
        fields = "title_ru", "title_en", "title_uz", "is_required"
        widgets = {
            "title_ru": form_control_text_input,
            "title_uz": form_control_text_input,
            "title_en": form_control_text_input,
        }


OptionItemFormSet = inlineformset_factory(
    ProductOption,
    OptionItem,
    extra=0,
    fields=["title_ru", "title_uz", "title_en", "adding_price"],
    widgets={
        "title_ru": form_control_text_input,
        "title_uz": form_control_text_input,
        "title_en": form_control_text_input,
        "adding_price": form_control_number_input,
    },
)
