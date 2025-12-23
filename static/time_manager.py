"""
time_manager.py - مدیریت زمان روز بعد برای کاربران
"""

import json
import os
import time
from datetime import datetime, timedelta


class TimeManager:
    """مدیریت زمان دسترسی به روز بعد"""

    def __init__(self):
        self.data_dir = "data"
        self.time_file = os.path.join(self.data_dir, "user_next_day_times.json")
        self.lock_file = os.path.join(self.data_dir, "daily_locks.json")
        os.makedirs(self.data_dir, exist_ok=True)

    def _load_json(self, file_path):
        """بارگذاری فایل JSON"""
        if os.path.exists(file_path):
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except:
                return {}
        return {}

    def _save_json(self, file_path, data):
        """ذخیره فایل JSON"""
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def get_next_day_time(self, user_id, topic_id):
        """دریافت زمان فعال شدن روز بعد"""
        data = self._load_json(self.time_file)
        user_key = f"{user_id}_{topic_id}"
        return data.get(user_key, 0)

    def set_next_day_time(self, user_id, topic_id, hours=24):
        """تنظیم زمان برای روز بعد"""
        data = self._load_json(self.time_file)
        user_key = f"{user_id}_{topic_id}"

        next_time = time.time() + (hours * 3600)
        data[user_key] = next_time

        self._save_json(self.time_file, data)
        return next_time

    def can_access_next_day(self, user_id, topic_id):
        """بررسی آیا کاربر می‌تواند روز بعد را ببیند"""
        next_time = self.get_next_day_time(user_id, topic_id)
        current_time = time.time()

        # اگر زمان گذشته یا اولین بار است
        if current_time >= next_time or next_time == 0:
            return True, 0

        # زمان باقیمانده
        remaining = next_time - current_time
        return False, remaining

    def reset_user_time(self, user_id, topic_id):
        """بازنشانی زمان کاربر (برای شروع مجدد)"""
        data = self._load_json(self.time_file)
        user_key = f"{user_id}_{topic_id}"

        if user_key in data:
            del data[user_key]
            self._save_json(self.time_file, data)

        return True

    def format_next_time(self, timestamp):
        """فرمت کردن زمان برای نمایش"""
        if timestamp == 0:
            return "همین حالا"

        dt = datetime.fromtimestamp(timestamp)
        persian_time = dt.strftime("%H:%M")

        # اضافه کردن تاریخ
        today = datetime.now().date()
        target_date = dt.date()

        if target_date == today:
            return f"امروز ساعت {persian_time}"
        elif target_date == today + timedelta(days=1):
            return f"فردا ساعت {persian_time}"
        else:
            return f"ساعت {persian_time}"

    def format_remaining_time(self, seconds):
        """فرمت کردن زمان باقیمانده"""
        if seconds <= 0:
            return "همین حالا"

        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)

        if hours > 0 and minutes > 0:
            return f"{hours} ساعت و {minutes} دقیقه"
        elif hours > 0:
            return f"{hours} ساعت"
        else:
            return f"{minutes} دقیقه"

    def get_daily_lock(self, user_id, topic_id):
        """دریافت قفل روزانه"""
        data = self._load_json(self.lock_file)
        user_key = f"{user_id}_{topic_id}"
        return data.get(user_key, {})

    def set_daily_lock(self, user_id, topic_id, day_number):
        """تنظیم قفل روزانه"""
        data = self._load_json(self.lock_file)
        user_key = f"{user_id}_{topic_id}"

        data[user_key] = {
            "last_day": day_number,
            "last_access": time.time(),
            "date": datetime.now().strftime("%Y-%m-%d")
        }

        self._save_json(self.lock_file, data)
        return True

    def check_daily_access(self, user_id, topic_id):
        """بررسی دسترسی روزانه - اصلاح شده"""
        lock_data = self.get_daily_lock(user_id, topic_id)

        if not lock_data:
            return True, 0  # اولین دسترسی

        last_date = lock_data.get("date", "")
        current_date = datetime.now().strftime("%Y-%m-%d")

        # اگر تاریخ امروز است و قبلاً دسترسی داشته
        if last_date == current_date:
            last_day = lock_data.get("last_day", 0)
            return False, last_day

        return True, 0


# نمونه جهانی
time_manager = TimeManager()