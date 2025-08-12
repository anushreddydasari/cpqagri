from pymongo import MongoClient

MONGO_URI = "mongodb+srv://anushreddydasari:anush@study.fsazs.mongodb.net/"

client = MongoClient(MONGO_URI)
db = client['agr_cpq']  # your database name

farmers_col = db['farmers']
crops_col = db['crops']
quotes_col = db['quotes']
