from pymongo import MongoClient
from pymongo import ASCENDING, DESCENDING
from typing import TypedDict, List, Optional, Any
from datetime import datetime

MONGO_URI = "mongodb+srv://anushreddydasari:anush@study.fsazs.mongodb.net/"

client = MongoClient(MONGO_URI)
db = client['agr_cpq']  # your database name

farmers_col = db['farmers']
crops_col = db['crops']
quotes_col = db['quotes']


# -----------------------------
# Document "schemas" (static typing only)
# -----------------------------

class DiscountRule(TypedDict):
    min_crops: int
    discount_percent: float


class FarmerDoc(TypedDict, total=False):
    name: str


class CropDoc(TypedDict, total=False):
    farmer_id: Any  # ObjectId
    name: str
    base_price: float
    discount_rules: List[DiscountRule]


class QuoteDoc(TypedDict, total=False):
    farmer_id: Any  # ObjectId
    crop_name: str
    crop_count: int
    final_price: float
    discount_percent: float
    seller_email: Optional[str]
    buyer_email: Optional[str]
    created_at: datetime


def ensure_indexes() -> None:
    """Create helpful indexes (no-ops if they already exist)."""
    try:
        farmers_col.create_index([("name", ASCENDING)], name="uix_farmers_name", unique=True)
    except Exception:
        pass

    try:
        crops_col.create_index([("farmer_id", ASCENDING), ("name", ASCENDING)], name="uix_crops_farmer_name", unique=True)
        crops_col.create_index([("name", ASCENDING)], name="ix_crops_name")
    except Exception:
        pass

    try:
        quotes_col.create_index([("farmer_id", ASCENDING), ("created_at", DESCENDING)], name="ix_quotes_farmer_created")
        quotes_col.create_index([("crop_name", ASCENDING)], name="ix_quotes_crop")
    except Exception:
        pass


# Ensure indexes at import time
ensure_indexes()
