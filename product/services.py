def get_product_price_display(product):
    options_sum = 0
    for option in product.options.all():
        if option.is_required:
            min_ = min([item.adding_price for item in option.items.all()])
            options_sum += min_

    return product.price + options_sum
