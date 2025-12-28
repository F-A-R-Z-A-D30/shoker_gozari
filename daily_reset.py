import os
from pymongo import MongoClient
from datetime import datetime, timedelta

class DailyResetManager:
    def __init__(self):
        # اتصال به دیتابیس
        mongo_uri = os.getenv("MONGO_URI")
        self.client = MongoClient(mongo_uri)
        self.db = self.client['gratitude_bot'] 
        self.collection = self.db['daily_access']

    def can_access_today(self, user_id, topic_id):
        """بررسی می‌کند آیا کاربر امروز اجازه دسترسی دارد یا خیر"""
        now = datetime.now() + timedelta(hours=3, minutes=30) # تنظیم ساعت به وقت ایران
        # ساعت ۶ صبح امروز را پیدا می‌کنیم
        today_6am = now.replace(hour=6, minute=0, second=0, microsecond=0)
        
        # اگر الان قبل از ۶ صبح است، بازنشانی مربوط به ۶ صبح دیروز است
        if now < today_6am:
            reset_time = today_6am - timedelta(days=1)
        else:
            reset_time = today_6am

        last_access = self.collection.find_one({
            "user_id": str(user_id),
            "topic_id": int(topic_id)
        })

        if not last_access:
            return True, today_6am

        # اگر آخرین دسترسی قبل از ساعت ۶ صبح اخیر بوده، پس مجاز است
        if last_access['access_time'] < reset_time:
            return True, today_6am
        
        return False, today_6am + timedelta(days=1)

    def record_access(self, user_id, topic_id, day_number):
        """ثبت زمان دسترسی کاربر"""
        now = datetime.now() + timedelta(hours=3, minutes=30)
        self.collection.update_one(
            {"user_id": str(user_id), "topic_id": int(topic_id)},
            {"$set": {
                "access_time": now,
                "day_number": day_number
            }},
            upsert=True
        )

    def get_access_info(self, user_id, topic_id):
        """همان تابعی که رباتت دنبالش می‌گردد و خطا می‌دهد"""
        can_access, next_reset = self.can_access_today(user_id, topic_id)
        
        # محاسبه زمان باقی‌مانده به زبان ساده
        now = datetime.now() + timedelta(hours=3, minutes=30)
        remaining = next_reset - now
        hours, remainder = divmod(remaining.seconds, 3600)
        minutes, _ = divmod(remainder, 60)
        
        return {
            "has_access": can_access,
            "next_reset_human": next_reset.strftime("%H:%M"),
            "remaining_text": f"{hours} ساعت و {minutes} دقیقه",
            "last_day": 0 # این مقدار در دیتابیس اصلی لودر مدیریت می‌شود
        }

    def reset_user_access(self, user_id, topic_id):
        """برای شروع مجدد موضوع"""
        self.collection.delete_one({"user_id": str(user_id), "topic_id": int(topic_id)})

# ایجاد یک نمونه برای استفاده در ربات
daily_reset = DailyResetManager()

