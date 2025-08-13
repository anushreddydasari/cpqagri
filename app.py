import streamlit as st
from db import farmers_col, crops_col, quotes_col
from cpq import calculate_price
from datetime import datetime
from utils import render_template_to_html
from uuid import uuid4

st.title("CPQ Agri Application")

menu = ["Add Farmer", "Add Crop", "Get Quote", "Lease Agreement PDF"]
choice = st.sidebar.selectbox("Select Action", menu)


def _suggest_base_price(crop_name: str, farmer_id):
    """Suggest a base price using historical data. Priority: farmer-specific, then global."""
    try:
        # Farmer-specific history
        farmer_prices = list(crops_col.find(
            {"farmer_id": farmer_id, "name": {"$regex": f"^{crop_name}$", "$options": "i"}},
            {"base_price": 1}
        ))
        candidate_prices = [p.get("base_price") for p in farmer_prices if isinstance(p.get("base_price"), (int, float)) and p.get("base_price") > 0]
        if candidate_prices:
            return sum(candidate_prices) / len(candidate_prices)

        # Global history (all farmers)
        global_prices = list(crops_col.find(
            {"name": {"$regex": f"^{crop_name}$", "$options": "i"}},
            {"base_price": 1}
        ))
        candidate_prices = [p.get("base_price") for p in global_prices if isinstance(p.get("base_price"), (int, float)) and p.get("base_price") > 0]
        if candidate_prices:
            return sum(candidate_prices) / len(candidate_prices)
    except Exception:
        pass
    return None

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
    farmer_names = [f.get('name') for f in farmers if f.get('name')]

    if not farmer_names:
        st.warning("No farmers found! Please add a farmer first.")
    else:
        selected_farmer = st.selectbox("Select Farmer", farmer_names)
        crop_name = st.text_input("Crop Name")
        # Suggest base price when crop name changes
        if "_last_crop_name" not in st.session_state:
            st.session_state._last_crop_name = ""
        if crop_name and crop_name != st.session_state._last_crop_name:
            st.session_state._last_crop_name = crop_name
            farmer = farmers_col.find_one({"name": selected_farmer})
            suggestion = _suggest_base_price(crop_name, farmer["_id"]) if farmer else None
            if suggestion is not None:
                st.session_state._base_price_suggestion = float(suggestion)
        # Use suggestion if available; user can overwrite
        default_base = st.session_state.get("_base_price_suggestion", 0.0)
        base_price = st.number_input("Base Price (₹)", min_value=0.0, format="%.2f", value=float(default_base))
        if st.session_state.get("_base_price_suggestion"):
            st.caption(f"Suggested from history: ₹{st.session_state._base_price_suggestion:,.2f} (editable)")
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
    farmer_names = [f.get('name') for f in farmers if f.get('name')]

    if not farmer_names:
        st.warning("No farmers found! Please add a farmer first.")
    else:
        selected_farmer = st.selectbox("Select Farmer", farmer_names)
        farmer = farmers_col.find_one({"name": selected_farmer})

        crops = list(crops_col.find({"farmer_id": farmer["_id"]}, {"name": 1}))
        crop_names = [c.get('name') for c in crops if c.get('name')]

        if not crop_names:
            st.warning("No crops found for this farmer! Please add crops first.")
        else:
            selected_crop = st.selectbox("Select Crop", crop_names)
            crop = crops_col.find_one({"farmer_id": farmer["_id"], "name": selected_crop})

            crop_count = st.number_input("Enter Crop Count", min_value=1, step=1)

            buyer_name = st.text_input("Buyer Name (for PDF)")
            valid_until = st.date_input("Valid Until (for PDF)")

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

                # Prepare PDF context and provide download
                from uuid import uuid4
                import tempfile, os
                quote_id = f"Q-{datetime.utcnow().strftime('%Y%m%d')}-{str(uuid4())[:6].upper()}"
                breakdown = [{
                    "name": selected_crop,
                    "quantity": crop_count,
                    "base": float(crop["base_price"]),
                    "discount_percent": float(discount),
                    "discount_amount": float((crop["base_price"] * crop_count) - final_price),
                    "final": float(final_price)
                }]
                total_base = float(crop["base_price"] * crop_count)
                total_discount = float(total_base - final_price)
                total_final = float(final_price)
                context = {
                    "quote_id": quote_id,
                    "date": datetime.utcnow().date().isoformat(),
                    "farmer": selected_farmer,
                    "buyer": buyer_name or "",
                    "breakdown": breakdown,
                    "total_base": f"{total_base:,.2f}",
                    "total_discount": f"{total_discount:,.2f}",
                    "total_final": f"{total_final:,.2f}",
                    "valid_until": valid_until.isoformat()
                }

                html_str = render_template_to_html('quote.html', context)
                st.download_button(
                    label="Download Quote (HTML)",
                    data=html_str,
                    file_name=f"{quote_id}.html",
                    mime="text/html"
                )

elif choice == "Lease Agreement PDF":
    st.header("Generate Lease Agreement (PDF)")

    st.subheader("Parties")
    col1, col2 = st.columns(2)
    with col1:
        lessor_name = st.text_input("Lessor Name")
        lessor_address = st.text_input("Lessor Address")
        lessor_contact = st.text_input("Lessor Contact")
        lessor_id_type = st.text_input("Lessor ID Type", value="Aadhaar")
        lessor_id_number = st.text_input("Lessor ID Number")
    with col2:
        lessee_name = st.text_input("Lessee Name")
        lessee_address = st.text_input("Lessee Address")
        lessee_contact = st.text_input("Lessee Contact")
        lessee_id_type = st.text_input("Lessee ID Type", value="Aadhaar")
        lessee_id_number = st.text_input("Lessee ID Number")

    st.subheader("Property & Term")
    village = st.text_input("Village")
    taluka = st.text_input("Taluka")
    district = st.text_input("District")
    state = st.text_input("State")
    parcel_id = st.text_input("Survey/Plot No.")
    area_acres = st.number_input("Area (acres)", min_value=0.0, format="%.2f")
    col3, col4, col5 = st.columns(3)
    with col3:
        term_start = st.date_input("Start Date")
    with col4:
        term_end = st.date_input("End Date")
    with col5:
        duration_text = st.text_input("Duration (e.g., 12 months)")
    possession_date = st.date_input("Possession/Handover Date")

    st.subheader("Crop Details")
    crops_raw = st.text_area("Enter crops (one per line: Crop,Variety,Season,Acreage)")

    st.subheader("Financials")
    amount_original = st.number_input("Agreed Lease Amount (₹)", min_value=0.0, format="%.2f")
    discount_percent = st.number_input("Discount (%)", min_value=0.0, max_value=100.0, format="%.2f")
    discount_amount = amount_original * (discount_percent / 100.0)
    amount_final = max(0.0, amount_original - discount_amount)

    st.subheader("Payment Schedule (up to 3 entries)")
    ps = []
    for i in range(1, 4):
        with st.expander(f"Payment {i}"):
            due = st.date_input(f"Due Date {i}")
            amt = st.number_input(f"Amount {i} (₹)", min_value=0.0, format="%.2f")
            method = st.text_input(f"Method {i}", value="NEFT")
            notes = st.text_input(f"Notes {i}", value="")
            if amt > 0:
                ps.append({
                    "due_date": due.isoformat(),
                    "amount": float(amt),
                    "method": method,
                    "notes": notes or None
                })

    st.subheader("Terms")
    irrigation_clause = st.text_input("Irrigation Clause", value="Irrigation from existing source; electricity charges on actuals, payable by Lessee.")
    termination_notice_days = st.number_input("Termination notice (days)", min_value=0, value=30, step=1)
    additional_clauses = st.text_area("Additional Clauses (optional)", value="")

    st.subheader("Witnesses")
    w1_name = st.text_input("Witness 1 Name")
    w1_address = st.text_input("Witness 1 Address")
    w1_id_type = st.text_input("Witness 1 ID Type", value="Aadhaar")
    w1_id_number = st.text_input("Witness 1 ID Number")
    w2_name = st.text_input("Witness 2 Name")
    w2_address = st.text_input("Witness 2 Address")
    w2_id_type = st.text_input("Witness 2 ID Type", value="Aadhaar")
    w2_id_number = st.text_input("Witness 2 ID Number")

    signature_date = st.date_input("Signature Date")

    if st.button("Generate Document"):
        agreement_id = f"LEASE-{datetime.utcnow().strftime('%Y%m%d')}-{str(uuid4())[:6].upper()}"
        crops_list = []
        if crops_raw:
            for line in crops_raw.splitlines():
                parts = [p.strip() for p in line.split(',')]
                if len(parts) >= 4:
                    try:
                        acreage = float(parts[3])
                    except Exception:
                        acreage = 0.0
                    crops_list.append({
                        "name": parts[0],
                        "variety": parts[1],
                        "season": parts[2],
                        "acreage": acreage
                    })

        context = {
            "agreement_id": agreement_id,
            "agreement_date": datetime.utcnow().date().isoformat(),
            "lessor": {
                "name": lessor_name,
                "address": lessor_address,
                "contact": lessor_contact,
                "id_type": lessor_id_type,
                "id_number": lessor_id_number
            },
            "lessee": {
                "name": lessee_name,
                "address": lessee_address,
                "contact": lessee_contact,
                "id_type": lessee_id_type,
                "id_number": lessee_id_number
            },
            "property": {
                "village": village,
                "taluka": taluka,
                "district": district,
                "state": state,
                "parcel_id": parcel_id,
                "area_acres": area_acres
            },
            "term": {
                "start_date": term_start.isoformat(),
                "end_date": term_end.isoformat(),
                "duration_text": duration_text
            },
            "possession_date": possession_date.isoformat() if possession_date else None,
            "crops": crops_list,
            "amounts": {
                "original": float(amount_original),
                "discount_percent": float(discount_percent),
                "discount_amount": float(discount_amount),
                "final": float(amount_final)
            },
            "payment_schedule": ps,
            "irrigation_clause": irrigation_clause,
            "termination_notice_days": int(termination_notice_days),
            "additional_clauses": additional_clauses or None,
            "witnesses": [
                {"name": w1_name, "address": w1_address, "id_type": w1_id_type, "id_number": w1_id_number},
                {"name": w2_name, "address": w2_address, "id_type": w2_id_type, "id_number": w2_id_number},
            ],
            "signature_date": signature_date.isoformat(),
        }

        html_str = render_template_to_html('lease.html', context)
        st.download_button(
            label="Download Lease Agreement (HTML)",
            data=html_str,
            file_name=f"{agreement_id}.html",
            mime="text/html"
        )
