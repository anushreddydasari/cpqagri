import streamlit as st
from db import farmers_col, crops_col, quotes_col


def render_manage_data() -> None:
	st.header("Manage Data")

	tab1, tab2 = st.tabs(["Delete Farmer", "Delete Crop"])

	with tab1:
		st.subheader("Delete Farmer")
		farmers = list(farmers_col.find({}, {"name": 1}))
		farmer_names = [f.get('name') for f in farmers if f.get('name')]
		if not farmer_names:
			st.info("No farmers to delete.")
		else:
			selected_farmer = st.selectbox("Select Farmer to delete", farmer_names, key="del_farmer")
			cascade = st.checkbox("Also delete this farmer's crops and quotes", value=True)
			if st.button("Delete Farmer"):
				farmer = farmers_col.find_one({"name": selected_farmer})
				if farmer:
					farmers_col.delete_one({"_id": farmer["_id"]})
					deleted_crops = 0
					deleted_quotes = 0
					if cascade:
						deleted_crops = crops_col.delete_many({"farmer_id": farmer["_id"]}).deleted_count
						deleted_quotes = quotes_col.delete_many({"farmer_id": farmer["_id"]}).deleted_count
					st.success(f"Deleted farmer '{selected_farmer}'. Removed {deleted_crops} crops and {deleted_quotes} quotes.")
				else:
					st.warning("Farmer not found.")

	with tab2:
		st.subheader("Delete Crop")
		farmers = list(farmers_col.find({}, {"name": 1}))
		farmer_names = [f.get('name') for f in farmers if f.get('name')]
		if not farmer_names:
			st.info("No farmers found.")
		else:
			selected_farmer = st.selectbox("Select Farmer", farmer_names, key="crop_farmer_for_delete")
			farmer = farmers_col.find_one({"name": selected_farmer})
			crops = list(crops_col.find({"farmer_id": farmer["_id"]}, {"name": 1})) if farmer else []
			crop_names = [c.get('name') for c in crops if c.get('name')]
			if not crop_names:
				st.info("No crops for this farmer.")
			else:
				selected_crop = st.selectbox("Select Crop to delete", crop_names, key="del_crop")
				also_quotes = st.checkbox("Also delete quotes for this crop", value=True)
				if st.button("Delete Crop"):
					crops_col.delete_one({"farmer_id": farmer["_id"], "name": selected_crop})
					dq = 0
					if also_quotes:
						dq = quotes_col.delete_many({"farmer_id": farmer["_id"], "crop_name": selected_crop}).deleted_count
					st.success(f"Deleted crop '{selected_crop}' for '{selected_farmer}'. Removed {dq} quotes.")


