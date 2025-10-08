import requests
from shapely.geometry.point import Point
from shapely.geometry.polygon import Polygon

from address.models import Address, Region
from crm.api.institution.services import create_institution_default_schedule
from institution.models import Institution, InstitutionBranch
from order.distance_calculator import calculate_distance
from order.exceptions import CantFindSuitableBranchError
from product.models import OptionItem, Product, ProductCategory, ProductOption, ProductToBranch
from django.core.files.base import ContentFile

from django.db.models import Q

def get_region_by_coordinates(lat, long):
    user_point = Point(lat, long)
    regions = Region.objects.all()
    for region in regions:
        polygon_points = region.points
        if polygon_points:
            polygon = Polygon(polygon_points)
            if polygon.contains(user_point):
                return region
    return None


def find_suitable_branch(institution: Institution, source_address: Address):
    branches = (
        InstitutionBranch.objects.get_available()
        .with_is_open_by_schedule()
        .filter(institution=institution, is_open=True, address__isnull=False, is_open_by_schedule=True)
        .select_related("address")
    )
    # for branch in branches.values("id", "name", "is_open_by_schedule", "is_open"):
    #     print(branch)
        
    if not branches:
        return False
        
    for branch in branches:
        branch.calculated_distance = calculate_distance(source_address, branch.address)
        
    closest_branch = min(branches, key=lambda branch: branch.calculated_distance)
    return closest_branch

def find_another_branch(institution: Institution, source_address: Address):

    branches = (
        InstitutionBranch.objects
        .filter(institution=institution, is_open=True, is_active=True, address__isnull=False)
        .select_related("address")
    )
    if not branches:
        branches = (
            InstitutionBranch.objects
            .filter(institution=institution, address__isnull=False)
            .select_related("address")
        )
    
    for branch in branches:
        branch.calculated_distance = calculate_distance(source_address, branch.address)

    closest_branch =  min(branches, key=lambda branch: branch.calculated_distance)
    return closest_branch

def seed_institution_branch(institution: Institution, data):
    branch = InstitutionBranch.objects.filter(places_id=data['id'])
    if not branch.exists():

        region = Region.objects.filter(name="Самарканд").first()
        adres = Address.objects.create(region=region, street=data['address'], reference_point="", latitude=39.653342, longitude=66.97984)
        branch = InstitutionBranch.objects.create(
            institution=institution,
            name=data['title'],
            legal_name="",
            inn="",
            pinfl="",
            phone_number="",
            address=adres,
            is_available=True,
            places_id=data['id'],
            region_branch=region
        )

        create_institution_default_schedule(branch)
        return True
    else:
        return True

def seed_category(institution, data):
    # print("created category")
    exist = ProductCategory.objects.filter(institution=institution, uuid=data['id'])
    if not exist.exists():
        res = ProductCategory.objects.create(
            uuid=data['id'],
            name=data['name'],
            position=1,
            institution=institution
        )
        return res
    else:
        pass
        # print("BOR ", data['name'])

def get_image(url):
    response = requests.get(url)
    if response.status_code == 200:
        image_name = url.split("/")[-1]
        return image_name, response.content
    return None

def seed_products(institution, branch, data):
    cat = ProductCategory.objects.filter(institution=institution, uuid=data['categoryId']).first()
    if cat:
        serviceCodesUz = data['serviceCodesUz']
        product = Product.objects.filter(uuid=data['id']).first()
        if not product:
            try:    
                product = Product.objects.create(
                    uuid=data['id'],
                    name=data['name'],
                    description=data['description'],
                    short_description="",
                    status="active",
                    price=data['price'],
                    commission=18,
                    spic_id=serviceCodesUz.get('mxikCodeUz', 0),
                    package_code=serviceCodesUz.get('packageCodeUz', 0),
                    vat=12,
                    category=cat,
                    institution=institution,
                    is_available=True
                )
                image, response = get_image(data['images'][0]['url'])
                if image is not None:
                    product.image.save(image, ContentFile(response), save=True)

                if data.get('modifierGroups'):
                    modifierGroups = data['modifierGroups']
                    for modifierGroup in modifierGroups:
                        if not ProductOption.objects.filter(uuid=modifierGroup.get('id', None)).exists():
                            option = ProductOption.objects.create(
                                uuid=modifierGroup.get('id', None),
                                title=modifierGroup['name'],
                                is_required=False,
                                product=product
                            )
                            modifiers = modifierGroup['modifiers']
                            for modifier in modifiers:
                                if not OptionItem.objects.filter(uuid=modifier['id']).exists():
                                    OptionItem.objects.create(
                                        uuid=modifier['id'],
                                        title=modifier['name'],
                                        option=option,
                                        adding_price=modifier['price'],
                                        is_default=True
                                    )
                branch = InstitutionBranch.objects.get(places_id=branch)  # mavjud branch
                if not ProductToBranch.objects.filter(product=product, institution_branches=branch).exists():
                    # print("OKOKOKOKO")
                    ProductToBranch.objects.create(
                        product=product,
                        institution_branches=branch,
                        is_available=True
                    )
                return product
            except Exception as e:
                print("EXP error", e)
            return "ok"
        else:
            branch = InstitutionBranch.objects.get(places_id=branch)  # mavjud branch
            if not ProductToBranch.objects.filter(product=product, institution_branches=branch).exists():
                # print("OKOKOKOKO")
                ProductToBranch.objects.create(
                    product=product,
                    institution_branches=branch,
                    is_available=True
                )
