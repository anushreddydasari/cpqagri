# cpq.py

def calculate_price(base_price, crop_count, discount_rules):
    """
    Calculate total price applying tiered discounts.
    discount_rules = list of dicts like:
    [{'min_crops': 2, 'discount_percent': 5}, {'min_crops': 3, 'discount_percent': 10}]
    """
    total = base_price * crop_count
    applicable_discount = 0

    # Find highest discount applicable based on crop_count
    for rule in discount_rules:
        if crop_count >= rule['min_crops']:
            if rule['discount_percent'] > applicable_discount:
                applicable_discount = rule['discount_percent']

    discount_amount = total * (applicable_discount / 100)
    final_price = total - discount_amount
    return final_price, applicable_discount
