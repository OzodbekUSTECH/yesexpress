from drf_yasg import openapi

MULTIPOINT_RESPONSE_BODY = {
    200: openapi.Response(
        description="Successful response",
        examples={
            "application/json": {
                "id": 1,
                "name": "string",
                "polygon": {
                    "type": "Polygon",
                    "coordinates": [[[0.1, 0.2], [0.2, 0.2], [0.3, 0.2], [0.4, 0.2], [0.5, 0.2]]],
                },
            }
        },
    )
}

MULTIPOINT_REQUEST_BODY = openapi.Schema(
    properties={
        "name": openapi.Schema(type=openapi.TYPE_STRING),
        "polygon": openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                "type": openapi.Schema(
                    type=openapi.TYPE_STRING,
                    default="Polygon",
                    description="type of coordinates, for now it's Multipoint, you should use it",
                ),
                "coordinates": openapi.Schema(
                    type=openapi.TYPE_ARRAY,
                    items=openapi.Schema(
                        description="In this array should be arrays of two floats(numbers) which represents Multipoint structure",
                        type=openapi.TYPE_ARRAY,
                        items=openapi.Schema(
                            type=openapi.TYPE_ARRAY,
                            items=openapi.Schema(
                                type=openapi.TYPE_NUMBER, format=openapi.FORMAT_FLOAT
                            ),
                        ),
                    ),
                ),
            },
        ),
    },
    type=openapi.TYPE_OBJECT,
)
