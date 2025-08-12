import streamlit as st
from db import farmers_col, crops_col, quotes_col
from cpq import calculate_price
from datetime import datetime

st.title("CPQ Agri Application")

menu = ["Add Farmer", "Add Crop", "Get Quote"]
choice = st.sidebar.selectbox("Select Action", menu)

if choice == "Add Farmer":
    st.header("Add a New Farmer")
    farmer_name = st.text_input("Farmer Name")
    if st.button("Add Farmer"):
        if not farmer_name:
            st.error("Please enter farmer name")
        else:
            existing = farmers_col.find_one({"name": farmer_name})
            if existing:
                st.warning(f"Farmer '{farmer_name}' already exists.")
            else:
                farmers_col.insert_one({"name": farmer_name})
                st.success(f"Farmer '{farmer_name}' added successfully!")

elif choice == "Add Crop":
    st.header("Add Crop for Farmer")

    # Get list of farmers for dropdown
    farmers = list(farmers_col.find({}, {"name": 1}))
    farmer_names = [f['name'] for f in farmers]

    if not farmer_names:
        st.warning("No farmers found! Please add a farmer first.")
    else:
        selected_farmer = st.selectbox("Select Farmer", farmer_names)
        crop_name = st.text_input("Crop Name")
        base_price = st.number_input("Base Price (₹)", min_value=0.0, format="%.2f")
        discounts = st.text_input("Discounts (e.g. 2:5,3:10)")

        if st.button("Add Crop"):
            if not crop_name:
                st.error("Please enter crop name")
            else:
                discount_rules = []
                if discounts:
                    parts = discounts.split(',')
                    for part in parts:
                        try:
                            min_crops, disc = part.split(':')
                            discount_rules.append({"min_crops": int(min_crops), "discount_percent": float(disc)})
                        except Exception:
                            st.warning(f"Ignored invalid discount format: {part}")

                farmer = farmers_col.find_one({"name": selected_farmer})
                crops_col.insert_one({
                    "farmer_id": farmer["_id"],
                    "name": crop_name,
                    "base_price": base_price,
                    "discount_rules": discount_rules
                })
                st.success(f"Crop '{crop_name}' added for farmer '{selected_farmer}'.")

elif choice == "Get Quote":
    st.header("Get Quote")

    # Fetch farmers for selection
    farmers = list(farmers_col.find({}, {"name": 1}))
    farmer_names = [f['name'] for f in farmers]

    if not farmer_names:
        st.warning("No farmers found! Please add a farmer first.")
    else:
        selected_farmer = st.selectbox("Select Farmer", farmer_names)
        farmer = farmers_col.find_one({"name": selected_farmer})

        crops = list(crops_col.find({"farmer_id": farmer["_id"]}, {"name": 1}))
        crop_names = [c['name'] for c in crops]

        if not crop_names:
            st.warning("No crops found for this farmer! Please add crops first.")
        else:
            selected_crop = st.selectbox("Select Crop", crop_names)
            crop = crops_col.find_one({"farmer_id": farmer["_id"], "name": selected_crop})

            crop_count = st.number_input("Enter Crop Count", min_value=1, step=1)

            if st.button("Calculate Quote"):
                final_price, discount = calculate_price(crop["base_price"], crop_count, crop.get("discount_rules", []))

                # Save quote in DB
                quote = {
                    "farmer_id": farmer["_id"],
                    "crop_name": selected_crop,
                    "crop_count": crop_count,
                    "final_price": final_price,
                    "discount_percent": discount,
                    "created_at": datetime.utcnow()
                }
                quotes_col.insert_one(quote)

                st.success(f"Quote for {crop_count} '{selected_crop}' crops: ₹{final_price:.2f} (Discount Applied: {discount}%)")
