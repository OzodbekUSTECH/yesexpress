# Данных полей уже не существует, закоммичено

# from address.models import Address, Region
# from order.distance_calculator import calculate_distance
#
#
# def validate_region(longitude, latitude):
#     regions = Region.objects.select_related('center')
#     address = Address(longitude=longitude, latitude=latitude)
#     for region in regions:
#         if region.center:
#             distance = calculate_distance(address, region.center)
#             if distance < region.radius:
#                 return True
#     return False
