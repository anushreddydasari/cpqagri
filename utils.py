# utils.py

def parse_discount_rules(discount_str):
    """
    Parse discount string like "2:5,3:10" into list of dicts:
    [{"min_crops": 2, "discount_percent": 5}, {"min_crops": 3, "discount_percent": 10}]
    """
    rules = []
    if discount_str:
        parts = discount_str.split(',')
        for part in parts:
            try:
                min_crops, disc = part.split(':')
                rules.append({"min_crops": int(min_crops), "discount_percent": float(disc)})
            except Exception:
                # You can log or print warning here if you want
                pass
    return rules


def format_currency(amount):
    """Format float as currency string with ₹ symbol."""
    return f"₹{amount:,.2f}"
