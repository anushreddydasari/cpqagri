from db import crops, quotes
from bson import ObjectId

def apply_discount_for_crop(crop_doc, quantity):
    """
    Given a crop document and requested quantity, return total price and applied discount %.
    crop_doc example:
    {
      "_id": ObjectId(...),
      "name": "Rice",
      "base_price": 5000,
      "season": "Kharif",
      "discount_rules": [
        {"min_crops": 2, "discount_percent": 5},
        {"min_crops": 3, "discount_percent": 10}
      ]
    }
    """
    base = float(crop_doc.get("base_price", 0)) * quantity
    discount = 0.0
    # find best applicable discount (largest min_crops <= quantity)
    rules = crop_doc.get("discount_rules", []) or []
    applicable = [r for r in rules if quantity >= int(r.get("min_crops", 0))]
    if applicable:
        # pick the rule with highest min_crops (or highest discount_percent)
        best = max(applicable, key=lambda r: (int(r.get("min_crops",0)), float(r.get("discount_percent",0))))
        discount = float(best.get("discount_percent", 0))
    discount_amount = base * (discount / 100.0)
    final = base - discount_amount
    return {"base": base, "discount_percent": discount, "discount_amount": discount_amount, "final": final}

def calculate_quote(items):
    """
    items: list of {"crop_id": "...", "quantity": n}
    returns breakdown and totals
    """
    total_base = 0.0
    total_discount = 0.0
    total_final = 0.0
    breakdown = []
    for it in items:
        crop = crops.find_one({"_id": ObjectId(it["crop_id"])})
        if not crop:
            raise ValueError(f"Crop {it['crop_id']} not found")
        res = apply_discount_for_crop(crop, it["quantity"])
        breakdown.append({
            "crop_id": str(crop.get("_id")),
            "name": crop.get("name"),
            "quantity": it["quantity"],
            "base": res["base"],
            "discount_percent": res["discount_percent"],
            "discount_amount": res["discount_amount"],
            "final": res["final"]
        })
        total_base += res["base"]
        total_discount += res["discount_amount"]
        total_final += res["final"]
    return {
        "breakdown": breakdown,
        "total_base": total_base,
        "total_discount": total_discount,
        "total_final": total_final
    }