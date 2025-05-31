from pymongo import MongoClient

MONGO_URI = "mongodb://gab_lead:jGQMefKw4RFr2mwS@ac-sjeeoxf-shard-00-00.t2s7w4o.mongodb.net:27017,ac-sjeeoxf-shard-00-01.t2s7w4o.mongodb.net:27017,ac-sjeeoxf-shard-00-02.t2s7w4o.mongodb.net:27017/?ssl=true&replicaSet=atlas-sjeeoxf-shard-0&authSource=admin&retryWrites=true&w=majority"

try:
    client = MongoClient(
        MONGO_URI,
        serverSelectionTimeoutMS=15000,  # wait 15 seconds for response
        socketTimeoutMS=20000,
        connectTimeoutMS=20000
    )
    client.admin.command("ping")
    print("✅ Connected to MongoDB!")
except Exception as e:
    print("❌ MongoDB connection failed:", e)
