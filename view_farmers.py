from db import farmers_col

farmers = list(farmers_col.find())
print(f"Found {len(farmers)} farmers in DB.")
if farmers:
    print("Farmers:")
    for farmer in farmers:
        print(farmer)
else:
    print("No farmers found.")
