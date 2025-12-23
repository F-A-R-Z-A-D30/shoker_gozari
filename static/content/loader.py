"""
سیستم لود محتوای ۴ هفته‌ای - نسخه سازگار با ربات
هر موضوع پیشرفت مستقل خود را دارد
"""

import importlib
import json
import os
from typing import Dict, Any, List

# ساختار ۸ موضوع اصلی
TOPICS = {
    1: {
        "name": "سلامتی و تندرستی",
        "folder": "health_wellness",
        "emoji": "💚",
        "color": "#2ecc71",
        "description": "شکرگزاری برای سلامت کامل جسم و روان",
        "author_quote": "سلامتی بزرگترین هدیه خداوند است - راندا برن"
    },
    2: {
        "name": "خانواده و روابط",
        "folder": "family_relationships",
        "emoji": "👨‍👩‍👧‍👦",
        "color": "#e74c3c",
        "description": "شکرگزاری برای پیوندهای انسانی ارزشمند",
        "author_quote": "خانواده بزرگترین موهبت زندگی است - راندا برن"
    },
    3: {
        "name": "ثروت و فراوانی",
        "folder": "wealth_abundance",
        "emoji": "💰",
        "color": "#f1c40f",
        "description": "شکرگزاری برای نعمت‌های مالی و فراوانی",
        "author_quote": "ثروت واقعی فراوانی در تمام زمینه‌های زندگی است - راندا برن"
    },
    4: {
        "name": "شادی و آرامش",
        "folder": "happiness_peace",
        "emoji": "😊",
        "color": "#3498db",
        "description": "شکرگزاری برای لحظات شاد و صلح درون",
        "author_quote": "شادی حقیقی از درون می‌جوشد - راندا برن"
    },
    5: {
        "name": "اهداف و موفقیت",
        "folder": "goals_success",
        "emoji": "🎯",
        "color": "#e67e22",
        "description": "شکرگزاری برای رشد، پیشرفت و دستاوردها",
        "author_quote": "هر هدفی با اولین قدم شروع می‌شود - راندا برن"
    },
    6: {
        "name": "زندگی مطلوب",
        "folder": "quality_life",
        "emoji": "🏠",
        "color": "#9b59b6",
        "description": "شکرگزاری برای امکانات و رفاه زندگی",
        "author_quote": "زندگی هدیه‌ای است که باید قدرش را بدانیم - راندا برن"
    },
    7: {
        "name": "طبیعت و کائنات",
        "folder": "nature_universe",
        "emoji": "🌿",
        "color": "#27ae60",
        "description": "شکرگزاری برای زیبایی‌های آفرینش",
        "author_quote": "طبیعت بهترین معلم شکرگزاری است - راندا برن"
    },
    8: {
        "name": "عشق و معنویت",
        "folder": "love_spirituality",
        "emoji": "💖",
        "color": "#e84393",
        "description": "شکرگزاری برای عشق الهی و رشد معنوی",
        "author_quote": "عشق قدرتمندترین نیروی جهان است - راندا برن"
    }
}

WEEK_THEMES = {
    1: {
        "title": "مبتدی: پایه شکرگزاری",
        "description": "آشنایی با قدرت شکرگزاری",
        "quote": "شکرگزاری ساده‌ترین راه برای جذب خوبی‌هاست - راندا برن"
    },
    2: {
        "title": "متوسط: عمق بخشیدن",
        "description": "عمیق‌تر شدن در تمرین شکرگزاری",
        "quote": "هر چه عمیق‌تر شکرگزاری کنید، معجزه بزرگ‌تری رخ می‌دهد - راندا برن"
    },
    3: {
        "title": "پیشرفته: تحول ذهنی",
        "description": "تغییر الگوهای فکری با شکرگزاری",
        "quote": "ذهن شکرگزار، ذهن فراوانی است - راندا برن"
    },
    4: {
        "title": "استادی: سبک زندگی",
        "description": "تبدیل شکرگزاری به سبک زندگی",
        "quote": "شما تبدیل به آنچه شکرگزارش هستید، می‌شوید - راندا برن"
    }
}


# ==================== مدیریت پیشرفت ====================
class UserProgressManager:
    """مدیریت پیشرفت کاربران"""

    def __init__(self):
        self.progress_dir = "data/user_progress"
        os.makedirs(self.progress_dir, exist_ok=True)

    def get_user_file(self, user_id):
        """آدرس فایل پیشرفت کاربر"""
        return os.path.join(self.progress_dir, f"{user_id}.json")

    def get_topic_progress(self, user_id, topic_id):
        """دریافت پیشرفت یک موضوع برای کاربر"""
        file_path = self.get_user_file(user_id)

        if os.path.exists(file_path):
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    topic_key = str(topic_id)
                    if topic_key in data:
                        return data[topic_key]
            except:
                pass

        # پیش‌فرض: هر موضوع از روز ۱ شروع می‌شود
        return {
            "current_day": 1,
            "started": False,
            "completed_days": []
        }

    def set_topic_day(self, user_id, topic_id, day_number):
        """تنظیم روز فعلی برای یک موضوع"""
        file_path = self.get_user_file(user_id)

        # بارگذاری داده‌های موجود
        data = {}
        if os.path.exists(file_path):
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
            except:
                data = {}

        # به روز رسانی
        topic_key = str(topic_id)
        if topic_key not in data:
            data[topic_key] = {}

        day_number = max(1, min(28, day_number))  # محدود به ۱-۲۸

        data[topic_key]["current_day"] = day_number
        data[topic_key]["started"] = True
        data[topic_key].setdefault("completed_days", [])

        # ذخیره
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

        return day_number

    def complete_day(self, user_id, topic_id, day_number):
        """علامت‌گذاری روز به عنوان تکمیل شده"""
        progress = self.get_topic_progress(user_id, topic_id)

        if day_number not in progress.get("completed_days", []):
            file_path = self.get_user_file(user_id)

            # بارگذاری داده‌های موجود
            data = {}
            if os.path.exists(file_path):
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                except:
                    data = {}

            # به روز رسانی
            topic_key = str(topic_id)
            if topic_key not in data:
                data[topic_key] = progress

            completed_days = data[topic_key].get("completed_days", [])
            if day_number not in completed_days:
                completed_days.append(day_number)
                data[topic_key]["completed_days"] = completed_days

            # روز بعدی
            next_day = min(day_number + 1, 28)
            data[topic_key]["current_day"] = next_day

            # ذخیره
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)

            return True

        return False


# ==================== توابع اصلی ====================
def get_week_info(day_number: int):
    """تبدیل شماره روز به اطلاعات هفته"""
    if day_number < 1:
        day_number = 1
    elif day_number > 28:
        day_number = 28

    week_number = ((day_number - 1) // 7) + 1
    day_in_week = ((day_number - 1) % 7) + 1
    return week_number, day_in_week


def load_day_content(topic_id: int, day_number: int, user_id: str = None) -> Dict[str, Any]:
    """
    لود محتوای یک روز خاص
    اگر user_id داده شود، از پیشرفت کاربر استفاده می‌کند
    """

    # اعتبارسنجی
    if topic_id not in TOPICS:
        topic_id = 1

    if day_number < 1 or day_number > 28:
        day_number = 1

    # اگر user_id داریم، از پیشرفت کاربر استفاده می‌کنیم
    if user_id:
        progress_manager = UserProgressManager()
        # ابتدا روز کاربر را تنظیم می‌کنیم
        day_number = progress_manager.set_topic_day(user_id, topic_id, day_number)

    topic = TOPICS[topic_id]
    week_number, day_in_week = get_week_info(day_number)
    week_theme = WEEK_THEMES.get(week_number, WEEK_THEMES[1])

    print(f"\n📖 بارگذاری محتوا:")
    print(f"  کاربر: {user_id or 'میهمان'}")
    print(f"  موضوع: {topic['name']} (ID: {topic_id})")
    print(f"  روز: {day_number} (هفته {week_number}, روز {day_in_week} از هفته)")

    # مسیر ماژول
    module_path = f"content.{topic['folder']}.week_{week_number}"

    try:
        # بارگذاری ماژول
        module = importlib.import_module(module_path)

        # پیدا کردن روز
        day_key = f"day_{day_in_week}"

        if hasattr(module, day_key):
            day_content = getattr(module, day_key)
            print(f"✅ {day_key} از هفته {week_number} بارگذاری شد")
        else:
            # اگر روز مورد نظر پیدا نشد
            print(f"⚠️  {day_key} یافت نشد، day_1 بارگذاری می‌شود")
            day_key = "day_1"
            day_content = getattr(module, "day_1")

        # ساخت پاسخ
        result = {
            "success": True,
            "topic_id": topic_id,
            "topic_name": topic["name"],
            "topic_emoji": topic["emoji"],
            "topic_color": topic["color"],
            "day_number": day_number,
            "week_number": week_number,
            "day_in_week": day_in_week,
            "week_title": week_theme["title"],
            "week_description": week_theme["description"],
            "week_quote": week_theme["quote"],
            "author_quote": topic.get("author_quote", ""),
            "title": day_content.get("title", f"روز {day_number}: تمرین {topic['name']}"),
            "intro": day_content.get("intro", ""),
            "items": day_content.get("items", []),
            "exercise": day_content.get("exercise", ""),
            "affirmation": day_content.get("affirmation", ""),
            "reflection": day_content.get("reflection", "")
        }

        return result

    except ModuleNotFoundError:
        print(f"❌ ماژول {module_path} یافت نشد")
        return get_fallback_content(topic_id, day_number)
    except Exception as e:
        print(f"❌ خطا: {str(e)}")
        return get_fallback_content(topic_id, day_number)


def get_fallback_content(topic_id: int, day_number: int):
    """محتوای پیش‌فرض"""
    topic = TOPICS.get(topic_id, TOPICS[1])
    week_number, day_in_week = get_week_info(day_number)
    week_theme = WEEK_THEMES.get(week_number, WEEK_THEMES[1])

    return {
        "success": False,
        "topic_id": topic_id,
        "topic_name": topic["name"],
        "topic_emoji": topic["emoji"],
        "day_number": day_number,
        "week_number": week_number,
        "week_title": week_theme["title"],
        "week_quote": week_theme["quote"],
        "author_quote": topic.get("author_quote", ""),
        "title": f"روز {day_number}: تمرین {topic['name']}",
        "intro": f"امروز روز {day_in_week} از هفته {week_number} است. روی {topic['name']} تمرکز کنید.",
        "items": [
            f"شکرگزاری برای {topic['name']} - مورد ۱",
            f"قدردانی برای نعمت {topic['name']} - مورد ۲",
            f"سپاسگزاری از خدا برای {topic['name']} - مورد ۳",
            f"تشکر برای تجربه {topic['name']} - مورد ۴",
            f"قدردانی برای برکت {topic['name']} - مورد ۵",
            f"شکر برای معجزه {topic['name']} - مورد ۶",
            f"سپاس برای فرصت تجربه {topic['name']} - مورد ۷",
            f"تشکر برای رشد در {topic['name']} - مورد ۸",
            f"قدردانی برای درس‌های {topic['name']} - مورد ۹",
            f"شکرگزاری برای کامل شدن در {topic['name']} - مورد ۱۰"
        ],
        "exercise": "هر مورد را با احساس عمیق بخوانید و ۳۰ ثانیه برای آن شکرگزاری کنید.",
        "affirmation": f"من عمیقاً شکرگزار {topic['name']} در زندگی‌ام هستم.",
        "reflection": f"امروز فرصتی است برای عمیق‌تر شدن در {topic['name']}.",
        "is_fallback": True
    }


def complete_day_for_user(user_id: str, topic_id: int, day_number: int) -> bool:
    """تکمیل روز برای کاربر"""
    progress_manager = UserProgressManager()
    return progress_manager.complete_day(user_id, topic_id, day_number)


def get_all_topics():
    """دریافت لیست همه موضوعات"""
    return [
        {
            "id": topic_id,
            "name": info["name"],
            "emoji": info["emoji"],
            "color": info["color"],
            "description": info["description"],
            "author_quote": info.get("author_quote", "")
        }
        for topic_id, info in TOPICS.items()
    ]


def get_topic_by_id(topic_id):
    """دریافت اطلاعات یک موضوع"""
    if topic_id in TOPICS:
        info = TOPICS[topic_id]
        return {
            "id": topic_id,
            "name": info["name"],
            "emoji": info["emoji"],
            "color": info["color"],
            "description": info["description"],
            "author_quote": info.get("author_quote", "")
        }
    return None


def get_user_topic_progress(user_id: str, topic_id: int):
    """دریافت پیشرفت کاربر در یک موضوع"""
    progress_manager = UserProgressManager()
    return progress_manager.get_topic_progress(user_id, topic_id)


def start_topic_for_user(user_id: str, topic_id: int):
    """شروع یک موضوع برای کاربر از روز اول"""
    progress_manager = UserProgressManager()
    progress_manager.set_topic_day(user_id, topic_id, 1)
    return load_day_content(topic_id, 1, user_id)


# ==================== تست ====================
if __name__ == "__main__":
    print("🧪 تست loader.py")
    print("=" * 50)

    # تست توابع اصلی
    print("\n1. لیست موضوعات:")
    topics = get_all_topics()
    for topic in topics:
        print(f"   {topic['emoji']} {topic['name']} (ID: {topic['id']})")

    print("\n2. اطلاعات موضوع ۱:")
    topic_info = get_topic_by_id(1)
    print(f"   نام: {topic_info['name']}")
    print(f"   نقل قول: {topic_info['author_quote']}")

    print("\n3. بارگذاری محتوای روز ۱ موضوع ۱:")
    content = load_day_content(1, 1, "test_user")
    print(f"   عنوان: {content['title']}")
    print(f"   آیتم‌ها: {len(content['items'])} مورد")

    print("\n4. پیشرفت کاربر test_user در موضوع ۱:")
    progress = get_user_topic_progress("test_user", 1)
    print(f"   روز فعلی: {progress['current_day']}")
    print(f"   شروع شده: {progress['started']}")

    print("\n✅ تست کامل شد!")