import os
from pymongo import MongoClient

# دریافت لینک از رندر (که قبلاً ست کردی)
MONGO_URI = os.getenv("MONGO_URI")
client = MongoClient(MONGO_URI)
db = client['shoker_gozari_db']
users_col = db['users']

def get_user_day(user_id, topic_id):
    """خواندن روزِ کاربر از دیتابیس"""
    user = users_col.find_one({"user_id": str(user_id)})
    if user and "progress" in user:
        return user["progress"].get(topic_id, 1)
    return 1

def save_user_day(user_id, topic_id, day_number):
    """ذخیره روزِ جدید در دیتابیس"""
    users_col.update_one(
        {"user_id": str(user_id)},
        {"$set": {f"progress.{topic_id}": day_number}},
        upsert=True
    )
