from motor.motor_asyncio import AsyncIOMotorClient
from config import MONGO_URI, MONGO_DB_NAME

client = AsyncIOMotorClient(MONGO_URI)
db     = client[MONGO_DB_NAME]

quotes_collection    = db["quotes"]
shipments_collection = db["shipments"]