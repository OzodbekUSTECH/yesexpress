from rest_framework import serializers
from rest_framework.exceptions import ValidationError
from .models import Address


class AddressSerializer(serializers.ModelSerializer):
    # def validate(self, attrs):
    #     if not validate_region(attrs['longitude'], attrs['latitude']):
    #         raise ValidationError(code='invalid_region', detail='invalid_region')
    #     return super().validate(attrs)

    class Meta:
        model = Address
        fields = [
            "id",
            "name",
            "region",
            "street",
            "flat_number",
            "floor",
            "longitude",
            "latitude",
            "is_current",
            "reference_point",
        ]
        
    def create(self, validated_data):
        if validated_data.get('is_current', False):
            user = self.context.get('request').user
            if user and user.is_authenticated:
                Address.objects.filter(is_current=True, customer=user).update(is_current=False)
                return super().create(validated_data)
        return super().create(validated_data)   
    
    def update(self, instance, validated_data):
        is_current = validated_data.get('is_current')

        if is_current is True:
            user = self.context.get('request').user
            if user and user.is_authenticated:
                Address.objects.filter(is_current=True, customer=user).exclude(pk=instance.pk).update(is_current=False)

        instance.is_current = validated_data.get('is_current', instance.is_current)
        instance.save()
        return instance

class InstitutionAddressSerializer(serializers.ModelSerializer):
    class Meta:
        model = Address
        fields = ["id", "longitude", "latitude"]
