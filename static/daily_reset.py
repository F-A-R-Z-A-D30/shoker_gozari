"""
daily_reset.py - سیستم بازنشانی روزانه ساعت ۶ صبح
"""

import json
import os
import time
from datetime import datetime, timedelta
from typing import Tuple, Optional


class DailyResetManager:
    """مدیریت دسترسی روزانه بر اساس ساعت ۶ صبح"""

    def __init__(self, reset_hour: int = 6):
        """
        Args:
            reset_hour: ساعت بازنشانی روزانه (پیش‌فرض: 6 صبح)
        """
        self.reset_hour = reset_hour
        self.data_dir = "data/daily_reset"
        self.access_file = os.path.join(self.data_dir, "user_access.json")
        os.makedirs(self.data_dir, exist_ok=True)

    def _load_data(self):
        """بارگذاری داده‌های دسترسی"""
        if os.path.exists(self.access_file):
            try:
                with open(self.access_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except:
                return {}
        return {}

    def _save_data(self, data):
        """ذخیره داده‌های دسترسی"""
        with open(self.access_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def _get_user_key(self, user_id: str, topic_id: int) -> str:
        """ساخت کلید کاربر"""
        return f"{user_id}_{topic_id}"

    def _get_next_reset_time(self) -> float:
        """محاسبه زمان بازنشانی بعدی (ساعت ۶ صبح)"""
        now = datetime.now()

        # ساعت ۶ صبح امروز
        today_6am = now.replace(hour=self.reset_hour, minute=0, second=0, microsecond=0)

        # اگر الان بعد از ۶ صبح هستیم، بازنشانی فردا ساعت ۶
        if now >= today_6am:
            tomorrow = now + timedelta(days=1)
            next_reset = tomorrow.replace(hour=self.reset_hour, minute=0, second=0, microsecond=0)
            return next_reset.timestamp()

        # اگر الان قبل از ۶ صبح هستیم، بازنشانی امروز ساعت ۶
        return today_6am.timestamp()

    def _get_reset_time_for_date(self, target_date: datetime) -> float:
        """دریافت زمان بازنشانی برای تاریخ مشخص"""
        return target_date.replace(hour=self.reset_hour, minute=0, second=0, microsecond=0).timestamp()

    def can_access_today(self, user_id: str, topic_id: int) -> Tuple[bool, Optional[float]]:
        """
        بررسی آیا کاربر می‌تواند امروز محتوا ببیند

        Returns:
            tuple: (می‌تواند دسترسی داشته باشد, زمان بازنشانی بعدی)
        """
        data = self._load_data()
        user_key = self._get_user_key(user_id, topic_id)

        now = datetime.now()
        current_time = now.timestamp()

        # اگر کاربر اولین بار است
        if user_key not in data:
            return True, self._get_next_reset_time()

        user_data = data[user_key]
        last_access_time = user_data.get("last_access", 0)

        # اگر هیچ دسترسی قبلی نداشته
        if last_access_time == 0:
            return True, self._get_next_reset_time()

        # تبدیل زمان‌ها به datetime برای مقایسه
        last_access_dt = datetime.fromtimestamp(last_access_time)
        now_dt = datetime.fromtimestamp(current_time)

        # ساعت ۶ صبح امروز
        today_6am = now_dt.replace(hour=self.reset_hour, minute=0, second=0, microsecond=0)

        # بررسی ۱: اگر آخرین دسترسی قبل از ساعت ۶ صبح امروز بود
        if last_access_dt < today_6am:
            # و الان بعد از ۶ صبح هستیم
            if now_dt >= today_6am:
                return True, self._get_next_reset_time()
            else:
                # هنوز به ۶ صبح نرسیده
                return False, today_6am.timestamp()

        # بررسی ۲: اگر آخرین دسترسی بعد از ساعت ۶ صبح امروز بود
        # باید تا ساعت ۶ صبح فردا صبر کند
        tomorrow_6am = today_6am + timedelta(days=1)
        return False, tomorrow_6am.timestamp()

    def record_access(self, user_id: str, topic_id: int, day_number: int):
        """ثبت دسترسی کاربر به یک روز"""
        data = self._load_data()
        user_key = self._get_user_key(user_id, topic_id)

        current_time = time.time()

        if user_key not in data:
            data[user_key] = {}

        data[user_key].update({
            "last_access": current_time,
            "last_day": day_number,
            "last_access_human": datetime.fromtimestamp(current_time).strftime("%Y-%m-%d %H:%M:%S"),
            "next_reset_at": self._get_next_reset_time(),
            "next_reset_human": datetime.fromtimestamp(self._get_next_reset_time()).strftime("%Y-%m-%d %H:%M:%S")
        })

        self._save_data(data)

    def get_remaining_time(self, user_id: str, topic_id: int) -> Tuple[float, str]:
        """
        دریافت زمان باقیمانده تا روز جدید

        Returns:
            tuple: (ثانیه‌های باقیمانده, فرمت خوانا)
        """
        can_access, next_reset = self.can_access_today(user_id, topic_id)

        if can_access:
            return 0, "همین حالا"

        current_time = time.time()
        remaining = next_reset - current_time

        if remaining <= 0:
            return 0, "همین حالا"

        return remaining, self._format_remaining_time(remaining)

    def _format_remaining_time(self, seconds: float) -> str:
        """فرمت کردن زمان باقیمانده به صورت خوانا"""
        if seconds <= 0:
            return "همین حالا"

        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)

        if hours > 0 and minutes > 0:
            return f"{hours} ساعت و {minutes} دقیقه"
        elif hours > 0:
            return f"{hours} ساعت"
        elif minutes > 0:
            return f"{minutes} دقیقه"
        else:
            return "کمتر از یک دقیقه"

    def get_access_info(self, user_id: str, topic_id: int) -> dict:
        """دریافت اطلاعات کامل دسترسی کاربر"""
        data = self._load_data()
        user_key = self._get_user_key(user_id, topic_id)

        if user_key not in data:
            return {
                "has_access": True,
                "message": "اولین دسترسی",
                "next_reset": self._get_next_reset_time(),
                "next_reset_human": datetime.fromtimestamp(self._get_next_reset_time()).strftime("%H:%M")
            }

        user_data = data[user_key]
        can_access, next_reset = self.can_access_today(user_id, topic_id)
        remaining_seconds, remaining_text = self.get_remaining_time(user_id, topic_id)

        return {
            "has_access": can_access,
            "last_access": user_data.get("last_access_human", "نامشخص"),
            "last_day": user_data.get("last_day", 0),
            "next_reset": next_reset,
            "next_reset_human": datetime.fromtimestamp(next_reset).strftime("%H:%M"),
            "remaining_seconds": remaining_seconds,
            "remaining_text": remaining_text,
            "can_access_now": can_access
        }

    def reset_user_access(self, user_id: str, topic_id: int):
        """بازنشانی دسترسی کاربر (برای تست یا شروع مجدد)"""
        data = self._load_data()
        user_key = self._get_user_key(user_id, topic_id)

        if user_key in data:
            del data[user_key]
            self._save_data(data)

        return True


# نمونه جهانی برای استفاده در کل برنامه
daily_reset = DailyResetManager(reset_hour=6)  # ساعت ۶ صبح