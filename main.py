import click
from db import farmers_col, crops_col, quotes_col
from cpq import calculate_price
from datetime import datetime


@click.group()
def cli():
    pass

@cli.command()
def add_farmer():
    """Add a new farmer interactively"""
    farmer_name = click.prompt("Enter farmer name")
    existing = farmers_col.find_one({"name": farmer_name})
    if existing:
        click.echo(f"Farmer '{farmer_name}' already exists.")
        return
    farmers_col.insert_one({"name": farmer_name})
    click.echo(f"Farmer '{farmer_name}' added.")

@cli.command()
def add_crop():
    """Add crop with base price and discount tiers for a farmer interactively"""
    farmer_name = click.prompt("Enter farmer name")
    farmer = farmers_col.find_one({"name": farmer_name})
    if not farmer:
        click.echo("Farmer not found! Add farmer first.")
        return
    
    crop_name = click.prompt("Enter crop name")
    base_price = click.prompt("Enter base price", type=float)
    discounts = click.prompt("Enter discounts (format: 2:5,3:10), or leave blank", default="", show_default=False)

    discount_rules = []
    if discounts:
        parts = discounts.split(',')
        for part in parts:
            try:
                min_crops, disc = part.split(':')
                discount_rules.append({"min_crops": int(min_crops), "discount_percent": float(disc)})
            except Exception:
                click.echo(f"Invalid discount format for part '{part}', skipping.")

    crops_col.insert_one({
        "farmer_id": farmer["_id"],
        "name": crop_name,
        "base_price": base_price,
        "discount_rules": discount_rules
    })
    click.echo(f"Crop '{crop_name}' added for farmer '{farmer_name}'.")

@cli.command()
def get_quote():
    """Calculate quote for given crop count interactively"""
    farmer_name = click.prompt("Enter farmer name")
    farmer = farmers_col.find_one({"name": farmer_name})
    if not farmer:
        click.echo("Farmer not found!")
        return
    
    crop_name = click.prompt("Enter crop name")
    crop = crops_col.find_one({"farmer_id": farmer["_id"], "name": crop_name})
    if not crop:
        click.echo("Crop not found!")
        return
    
    crop_count = click.prompt("Enter crop count", type=int)
    
    final_price, discount = calculate_price(crop["base_price"], crop_count, crop.get("discount_rules", []))
    
    # Save quote in DB
    quote = {
        "farmer_id": farmer["_id"],
        "crop_name": crop_name,
        "crop_count": crop_count,
        "final_price": final_price,
        "discount_percent": discount,
        "created_at": datetime.utcnow()
    }
    quotes_col.insert_one(quote)

    click.echo(f"Quote for {crop_count} '{crop_name}' crops: ₹{final_price:.2f} (Discount Applied: {discount}%)")
from utils import parse_discount_rules, format_currency
discount_rules = parse_discount_rules("2:5,3:10")
print(discount_rules)
# Output: [{'min_crops': 2, 'discount_percent': 5}, {'min_crops': 3, 'discount_percent': 10}]

price_str = format_currency(12345.678)
print(price_str)
# Output: ₹12,345.68   

if __name__ == "__main__":
    cli()
