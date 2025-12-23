"""
test_daily_reset.py - تست سیستم ساعت ۶ صبح
"""

from daily_reset import daily_reset
from datetime import datetime, timedelta


def test_scenarios():
    print("🧪 تست سیستم ساعت ۶ صبح")
    print("=" * 40)

    user_id = "test_user"
    topic_id = 1

    # سناریو ۱: اولین دسترسی
    print("\n۱️⃣ اولین دسترسی:")
    can_access, next_reset = daily_reset.can_access_today(user_id, topic_id)
    print(f"   می‌تواند دسترسی داشته باشد: {can_access}")
    print(f"   زمان بازنشانی بعدی: {datetime.fromtimestamp(next_reset).strftime('%H:%M')}")

    # سناریو ۲: ثبت دسترسی ساعت ۵:۵۹
    print("\n۲️⃣ ثبت دسترسی ساعت ۵:۵۹:")
    # شبیه‌سازی زمان
    test_time = datetime.now().replace(hour=5, minute=59, second=0, microsecond=0)
    # در واقعیت از time.time() استفاده می‌شود

    daily_reset.record_access(user_id, topic_id, 1)
    can_access, next_reset = daily_reset.can_access_today(user_id, topic_id)
    print(f"   می‌تواند دسترسی داشته باشد: {can_access}")

    # سناریو ۳: دریافت اطلاعات
    print("\n۳️⃣ اطلاعات کامل دسترسی:")
    info = daily_reset.get_access_info(user_id, topic_id)
    for key, value in info.items():
        print(f"   {key}: {value}")

    # سناریو ۴: بازنشانی
    print("\n۴️⃣ بازنشانی دسترسی:")
    daily_reset.reset_user_access(user_id, topic_id)
    can_access, next_reset = daily_reset.can_access_today(user_id, topic_id)
    print(f"   می‌تواند دسترسی داشته باشد: {can_access} (باید True باشد)")

    print("\n✅ تست کامل شد!")


if __name__ == "__main__":
    test_scenarios()