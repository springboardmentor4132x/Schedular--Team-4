from motor.motor_asyncio import AsyncIOMotorClient

from app.config import settings


client = AsyncIOMotorClient(
    settings.MONGO_URL
)


database = client[
    settings.MONGO_DATABASE
]


def get_mongo():

    return database