import json

from django.core.exceptions import ValidationError
from django.contrib.gis.geos import GEOSGeometry, GEOSException
from django.contrib.gis.gdal import GDALException
from django.utils.translation import gettext_lazy as _
from rest_framework_gis import serializers as gis_serializers
from rest_framework import serializers


class GisFieldCustom(gis_serializers.GeometryField):
    def to_internal_value(self, value):
        if value == "" or value is None:
            return value
        if isinstance(value, GEOSGeometry):
            # value already has the correct representation
            return value
        if isinstance(value, dict):
            coordinates = value["coordinates"]
            coordinates[0].append(coordinates[0][0])
            value["coordinates"] = coordinates
            value = json.dumps(value)
        try:
            return GEOSGeometry(value)
        except GEOSException:
            raise ValidationError(
                _(
                    "Invalid format: string or unicode input unrecognized as GeoJSON, WKT EWKT or HEXEWKB."
                )
            )
        except (ValueError, TypeError, GDALException) as e:
            raise ValidationError(_("Unable to convert to python object: {}".format(str(e))))


class PrimaryKeyRelatedFieldByUser(serializers.PrimaryKeyRelatedField):
    def get_queryset(self):
        query_set = super().get_queryset()
        request = self.context.get("request")

        return query_set.filter(owner=request.user)
