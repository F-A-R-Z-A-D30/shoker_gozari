"""
daily_reset.py - سیستم بازنشانی روزانه ساعت ۶ صبح متصل به MongoDB
"""

import os
import time
from datetime import datetime, timedelta
from typing import Tuple, Optional
from pymongo import MongoClient

# --- اتصال به MongoDB ---
MONGO_URI = os.getenv("MONGO_URI")

client = MongoClient(MONGO_URI)
db = client['shoker_gozari_db']
access_col = db['daily_access']

class DailyResetManager:
    """مدیریت دسترسی روزانه بر اساس ساعت ۶ صبح در دیتابیس ابری"""

    def __init__(self, reset_hour: int = 6):
        self.reset_hour = reset_hour

    def _get_user_key(self, user_id: str, topic_id: int) -> str:
        """ساخت کلید یکتا برای ترکیب کاربر و موضوع"""
        return f"{user_id}_{topic_id}"

    def _get_next_reset_time(self) -> float:
        """محاسبه زمان دقیق بازنشانی بعدی (ساعت ۶ صبح)"""
        now = datetime.now()
        today_6am = now.replace(hour=self.reset_hour, minute=0, second=0, microsecond=0)

        if now >= today_6am:
            next_reset = (now + timedelta(days=1)).replace(hour=self.reset_hour, minute=0, second=0, microsecond=0)
            return next_reset.timestamp()
        
        return today_6am.timestamp()

    def can_access_today(self, user_id: str, topic_id: int) -> Tuple[bool, Optional[float]]:
        """بررسی امکان دسترسی کاربر به محتوای جدید"""
        user_key = self._get_user_key(user_id, topic_id)
        user_data = access_col.find_one({"user_key": user_key})

        if not user_data:
            return True, self._get_next_reset_time()

        last_access_time = user_data.get("last_access", 0)
        last_access_dt = datetime.fromtimestamp(last_access_time)
        now_dt = datetime.now()
        today_6am = now_dt.replace(hour=self.reset_hour, minute=0, second=0, microsecond=0)

        # اگر آخرین بار قبل از ۶ صبح امروز دسترسی داشته
        if last_access_dt < today_6am:
            if now_dt >= today_6am:
                return True, self._get_next_reset_time()
            else:
                return False, today_6am.timestamp()

        # اگر آخرین بار همین امروز (بعد از ۶ صبح) بوده، باید تا فردا صبر کند
        tomorrow_6am = today_6am + timedelta(days=1)
        return False, tomorrow_6am.timestamp()

    def record_access(self, user_id: str, topic_id: int, day_number: int):
        """ثبت زمان دسترسی کاربر در دیتابیس"""
        user_key = self._get_user_key(user_id, topic_id)
        current_time = time.time()
        next_reset = self._get_next_reset_time()

        access_col.update_one(
            {"user_key": user_key},
            {"$set": {
                "user_id": str(user_id),
                "topic_id": topic_id,
                "last_access": current_time,
                "last_day": day_number,
                "last_access_human": datetime.fromtimestamp(current_time).strftime("%Y-%m-%d %H:%M:%S"),
                "next_reset_at": next_reset,
                "next_reset_human": datetime.fromtimestamp(next_reset).strftime("%Y-%m-%d %H:%M:%S")
            }},
            upsert=True
        )

    def get_remaining_time(self, user_id: str, topic_id: int) -> Tuple[float, str]:
        """محاسبه زمان باقیمانده به صورت ثانیه و متن فارسی"""
        can_access, next_reset = self.can_access_today(user_id, topic_id)
        if can_access:
            return 0, "همین حالا"

        remaining = next_reset - time.time()
        return remaining, self._format_remaining_time(remaining)

    def _format_remaining_time(self, seconds: float) -> str:
        if seconds <= 0: return "همین حالا"
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        
        if hours > 0:
            return f"{hours} ساعت و {minutes} دقیقه"
        return f"{minutes} دقیقه"

    def reset_user_access(self, user_id: str, topic_id: int):
        """پاک کردن رکورد دسترسی برای تست یا رفع مشکل"""
        user_key = self._get_user_key(user_id, topic_id)
        access_col.delete_one({"user_key": user_key})
        return True

# ایجاد آبجکت اصلی برای استفاده در ربات
daily_reset = DailyResetManager(reset_hour=6)
