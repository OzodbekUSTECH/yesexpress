import base64
import re
from datetime import datetime

from django.conf import settings
from django.core.files.base import ContentFile
from django.utils import timezone
from rest_framework import serializers


def get_regex_validator(regex, error_message="The value {value} does not match regex {regex}"):
    def validator(value):
        if not re.match(regex, value):
            raise serializers.ValidationError(error_message.format(regex=regex, value=value))

    return validator


def get_phone_number_field():
    regex_validator = get_regex_validator(
        regex=settings.PHONE_NUMBER_REGEX_PATTERN,
        error_message="The value is not valid phone number",
    )
    return serializers.CharField(
        max_length=13,
        min_length=13,
        validators=[regex_validator],
    )


class Base64FileField(serializers.FileField):
    def to_internal_value(self, data):
        if isinstance(data, str) and data.startswith("data:"):
            # base64 encoded file - decode
            format, filestr = data.split(";base64,")  # format ~= data:image/X, filestr ~= base64
            ext = format.split("/")[-1]  # guess file extension
            if ext == "svg+xml":
                ext = "svg"
            date = datetime.now(tz=timezone.get_current_timezone()).strftime("%d.%m.%Y_%H-%M")
            data = ContentFile(base64.b64decode(filestr), name=f"{date}." + ext)

        return super(Base64FileField, self).to_internal_value(data)


class DynamicFieldsSerializerMixin:
    def __init__(self, *args, **kwargs):
        fields = kwargs.pop("fields", None)
        exclude = kwargs.pop("exclude", None)

        super().__init__(*args, **kwargs)

        if fields is not None:
            allowed = set(fields)
            existing = set(self.fields.keys())
            for field_name in existing - allowed:
                self.fields.pop(field_name)

        if exclude is not None:
            not_allowed = set(exclude)
            for field_name in not_allowed:
                self.fields.pop(field_name)


class DynamicFieldsModelSerializer(serializers.ModelSerializer):
    def __init__(self, *args, **kwargs):
        fields = kwargs.pop("fields", None)
        exclude = kwargs.pop("exclude", None)

        super().__init__(*args, **kwargs)

        if fields is not None:
            allowed = set(fields)
            existing = set(self.fields.keys())
            for field_name in existing - allowed:
                self.fields.pop(field_name)

        if exclude is not None:
            not_allowed = set(exclude)
            for field_name in not_allowed:
                self.fields.pop(field_name)


class DynamicDepthSerializer(serializers.ModelSerializer):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.Meta.depth = self.context.get("depth", 0)


class MultiLanguageFieldSerializerMixin:
    def get_field_names(self, declared_fields, info):
        language_options = [item[0] for item in settings.LANGUAGES]
        model = getattr(self.Meta, "model")
        trans_fields = model.i18n.field.fields
        fields = super().get_field_names(declared_fields, info)
        for field in trans_fields:
            if field in fields:
                fields.remove(field)
                fields += [f"{field}_{lang}" for lang in language_options]
        return fields

    # def to_representation(self, instance):
    #     ret = super().to_representation(instance)
    #     ret = {
    #         key.replace('_ru', '').replace('_uz', '').replace('_en', ''): value
    #         for key, value in ret.items()
    #     }
    #     return ret
