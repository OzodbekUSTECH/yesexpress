from math import cos, asin, sqrt


def calculate_distance(address_1, address_2):
    p = 0.017453292519943295
    a = (
        0.5
        - cos((float(address_1.latitude) - float(address_2.latitude)) * p) / 2
        + cos(float(address_2.latitude) * p)
        * cos(float(address_1.latitude) * p)
        * (1 - cos((float(address_1.longitude) - float(address_2.longitude)) * p))
        / 2
    )
    distance = 12742 * asin(sqrt(a))
    return distance
