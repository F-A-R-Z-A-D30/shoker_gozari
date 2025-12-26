import importlib
import json
import os
from typing import Dict, Any, List
from pymongo import MongoClient

# --- اتصال به MongoDB ---
MONGO_URI = os.getenv("MONGO_URI")
client = MongoClient(MONGO_URI)
db = client['shoker_gozari_db']
users_col = db['users_progress']

TOPICS = {
    1: {
        "name": "سلامتی و تندرستی", 
        "folder": "health_wellness", 
        "emoji": "💚", 
        "color": "#2ecc71", 
        "image": "assets/health.png",
        "description": "📈 <b>سلامت کامل جسم و روان</b>\nشکرگزاری برای نعمت سلامتی که زندگی را ممکن می‌کند."
    },
    2: {
        "name": "خانواده و روابط", 
        "folder": "family_relationships", 
        "emoji": "👨‍👩‍👧‍👦", 
        "color": "#e74c3c", 
        "image": "assets/family.png",
        "description": "❤️ <b>پیوندهای انسانی ارزشمند</b>\nقدردانی از عشق و حمایت اطرافیان."
    },
    3: {
        "name": "ثروت و فراوانی", 
        "folder": "wealth_abundance", 
        "emoji": "💰", 
        "color": "#f1c40f", 
        "image": "assets/wealth.png",
        "description": "🌟 <b>نعمت‌های مالی و فراوانی</b>\nشکرگزاری برای رفاه و امنیت اقتصادی."
    },
    4: {
        "name": "شادی و آرامش", 
        "folder": "happiness_peace", 
        "emoji": "😊", 
        "color": "#3498db", 
        "image": "assets/happiness.png",
        "description": "✨ <b>لحظات شاد و صلح درون</b>\nقدردانی از آرامش و شادی‌های کوچک زندگی."
    },
    5: {
        "name": "اهداف و موفقیت", 
        "folder": "goals_success", 
        "emoji": "🎯", 
        "color": "#e67e22", 
        "image": "assets/goals.png",
        "description": "🚀 <b>رشد، پیشرفت و دستاوردها</b>\nشکرگزاری برای هر قدم به سوی هدف."
    },
    6: {
        "name": "زندگی مطلوب", 
        "folder": "quality_life", 
        "emoji": "🏠", 
        "color": "#9b59b6", 
        "image": "assets/quality.png",
        "description": "🏡 <b>امکانات و رفاه زندگی</b>\nقدردانی از خانه، شغل و امکانات رفاهی."
    },
    7: {
        "name": "طبیعت و کائنات", 
        "folder": "nature_universe", 
        "emoji": "🌿", 
        "color": "#27ae60", 
        "image": "assets/nature.png",
        "description": "🌍 <b>زیبایی‌های آفرینش</b>\nشکرگزاری برای طبیعت، هوا و آب."
    },
    8: {
        "name": "عشق و معنویت", 
        "folder": "love_spirituality", 
        "emoji": "💖", 
        "color": "#e84393", 
        "image": "assets/love.png",
        "description": "🙏 <b>عشق الهی و رشد معنوی</b>\nقدردانی از عشق درون و معنویت زندگی."
    }
}

WEEK_THEMES = {
    1: {
        "title": "🏁 <b>مبتدی: پایه شکرگزاری</b>",
        "quote": "📖 <i>«شکرگزاری ساده‌ترین راه برای جذب خوبی‌هاست.»</i>\n   - راندا برن"
    },
    2: {
        "title": "📈 <b>متوسط: عمق بخشیدن</b>",
        "quote": "💎 <i>«هر چه عمیق‌تر شکرگزاری کنید، معجزه بزرگ‌تری رخ می‌دهد.»</i>\n   - راندا برن"
    },
    3: {
        "title": "🚀 <b>پیشرفته: تحول ذهنی</b>",
        "quote": "🧠 <i>«ذهن شکرگزار، ذهن فراوانی است.»</i>\n   - راندا برن"
    },
    4: {
        "title": "👑 <b>استادی: سبک زندگی</b>",
        "quote": "🌟 <i>«شما تبدیل به آنچه شکرگزارش هستید، می‌شوید.»</i>\n   - راندا برن"
    }
}

class UserProgressManager:
    def get_topic_progress(self, user_id, topic_id):
        user_data = users_col.find_one({"user_id": str(user_id)})
        topic_key = str(topic_id)
        if user_data and "topics" in user_data and topic_key in user_data["topics"]:
            return user_data["topics"][topic_key]
        return {"current_day": 1, "started": False, "completed_days": []}

    def set_topic_day(self, user_id, topic_id, day_number):
        day_number = max(1, min(28, day_number))
        topic_key = str(topic_id)
        users_col.update_one(
            {"user_id": str(user_id)}, 
            {"$set": {
                f"topics.{topic_key}.current_day": day_number, 
                f"topics.{topic_key}.started": True
            }}, 
            upsert=True
        )
        return day_number

    def complete_day(self, user_id, topic_id, day_number):
        topic_key = str(topic_id)
        next_day = min(day_number + 1, 28)
        users_col.update_one(
            {"user_id": str(user_id)}, 
            {
                "$addToSet": {f"topics.{topic_key}.completed_days": day_number}, 
                "$set": {f"topics.{topic_key}.current_day": next_day}
            }, 
            upsert=True
        )
        return True

def get_week_info(day_number: int):
    week_number = ((day_number - 1) // 7) + 1
    day_in_week = ((day_number - 1) % 7) + 1
    return week_number, day_in_week

def load_day_content(topic_id: int, day_number: int, user_id: str = None) -> Dict[str, Any]:
    if topic_id not in TOPICS: 
        topic_id = 1
    
    if user_id:
        day_number = UserProgressManager().set_topic_day(user_id, topic_id, day_number)

    topic = TOPICS[topic_id]
    week_number, day_in_week = get_week_info(day_number)
    
    module_path = f"content.{topic['folder']}.week_{week_number}"
    
    try:
        module = importlib.import_module(module_path)
        day_data = getattr(module, f"day_{day_in_week}")
        week_info = getattr(module, "WEEK_INFO", WEEK_THEMES.get(week_number, {}))

        return {
            "success": True,
            "topic_id": topic_id,
            "topic_name": topic["name"],
            "topic_emoji": topic["emoji"],
            "topic_description": topic.get("description", ""),
            "topic_color": topic["color"],
            "day_number": day_number,
            "week_number": week_number,
            "day_in_week": day_in_week,
            "week_title": week_info.get("title", "🧘‍♂️ <b>تمرین روزانه شکرگزاری</b>"),
            "author_quote": week_info.get("quote", "💫 <i>«شکرگزاری کلید تحول زندگی است.»</i>"),
            "intro": day_data.get("intro", "🌟 امروز را با شکرگزاری شروع می‌کنیم..."),
            "items": day_data.get("items", []),
            "exercise": day_data.get("exercise", "📝 تمرین امروز را با دقت انجام دهید.")
        }
    except ModuleNotFoundError as e:
        print(f"❌ <b>خطا در بارگذاری محتوا:</b> {e}")
        return {
            "success": False,
            "error_message": "⚠️ محتوای مورد نظر موقتاً در دسترس نیست.",
            "topic_name": topic["name"],
            "topic_emoji": topic["emoji"],
            "topic_description": topic.get("description", ""),
            "day_number": day_number,
            "week_title": "🔄 <b>در حال آماده‌سازی محتوا</b>",
            "author_quote": "✨ <i>«صبر و شکرگزاری، هر دو لازمند.»</i>",
            "items": [
                "✅ ۱. برای سلامتی خود شکرگزار باشید",
                "✅ ۲. برای خانواده و دوستان شکرگزار باشید", 
                "✅ ۳. برای شغلتان شکرگزار باشید",
                "✅ ۴. برای خانه‌تان شکرگزار باشید",
                "✅ ۵. برای غذایی که می‌خورید شکرگزار باشید",
                "✅ ۶. برای هوای پاک شکرگزار باشید",
                "✅ ۷. برای فرصت‌های زندگی شکرگزار باشید",
                "✅ ۸. برای چالش‌های رشد‌دهنده شکرگزار باشید",
                "✅ ۹. برای تجربیات ارزشمند شکرگزار باشید",
                "✅ ۱۰. برای همین لحظه زندگی شکرگزار باشید"
            ],
            "exercise": "📖 این ۱۰ مورد را در دفتر شکرگزاری خود بنویسید و هر کدام را با احساس قدردانی تکرار کنید."
        }
    except Exception as e:
        print(f"⚠️ <b>خطای عمومی:</b> {e}")
        return {
            "success": False,
            "topic_name": topic["name"],
            "topic_emoji": topic["emoji"],
            "day_number": day_number,
            "week_title": "⚡ <b>تمرین اضطراری شکرگزاری</b>",
            "items": ["🌟 امروز ۱۰ بار جمله «خدایا شکرت» را با احساس عمیق تکرار کنید."],
            "exercise": "🙏 این تمرین ساده را با تمام وجود انجام دهید."
        }

def load_past_day_content(topic_id: int, day_number: int, user_id: str = None) -> Dict[str, Any]:
    """لود محتوای روزهای گذشته برای مرور (بدون محدودیت زمانی و بدون به‌روزرسانی روز جاری کاربر)"""
    if topic_id not in TOPICS: 
        topic_id = 1

    topic = TOPICS[topic_id]
    week_number, day_in_week = get_week_info(day_number)
    
    module_path = f"content.{topic['folder']}.week_{week_number}"
    
    try:
        module = importlib.import_module(module_path)
        day_data = getattr(module, f"day_{day_in_week}")
        week_info = getattr(module, "WEEK_INFO", WEEK_THEMES.get(week_number, {}))

        return {
            "success": True,
            "topic_id": topic_id,
            "topic_name": topic["name"],
            "topic_emoji": topic["emoji"],
            "topic_description": topic.get("description", ""),
            "topic_color": topic["color"],
            "day_number": day_number,
            "week_number": week_number,
            "day_in_week": day_in_week,
            "week_title": week_info.get("title", "🧘‍♂️ <b>مرور تمرین گذشته</b>"),
            "author_quote": week_info.get("quote", "💫 <i>«مرور شکرگزاری‌ها، معجزه را تازه می‌کند.»</i>"),
            "intro": day_data.get("intro", "🌟 امروز را با مرور شکرگزاری‌های گذشته آغاز می‌کنیم..."),
            "items": day_data.get("items", []),
            "exercise": day_data.get("exercise", "📝 این تمرین را یکبار دیگر با دقت مرور کنید.")
        }
    except ModuleNotFoundError as e:
        print(f"❌ <b>خطا در بارگذاری محتوای گذشته:</b> {e}")
        return {
            "success": False,
            "error_message": "⚠️ محتوای مورد نظر برای مرور موقتاً در دسترس نیست.",
            "topic_name": topic["name"],
            "topic_emoji": topic["emoji"],
            "day_number": day_number,
            "week_title": "🔄 <b>مرور تمرین گذشته</b>",
            "author_quote": "✨ <i>«حتی خاطره شکرگزاری هم برکت دارد.»</i>",
            "items": ["🌟 امروز ۱۰ مورد از شکرگزاری‌های گذشته خود را مرور کنید."],
            "exercise": "🙏 با احساس قدردانی، روزهای گذشته را مرور کنید."
        }
    except Exception as e:
        print(f"⚠️ <b>خطای عمومی در مرور گذشته:</b> {e}")
        return {
            "success": False,
            "topic_name": topic["name"],
            "topic_emoji": topic["emoji"],
            "day_number": day_number,
            "week_title": "⚡ <b>مرور اضطراری</b>",
            "items": ["🌟 امروز ۱۰ بار جمله «خدایا شکرت» را با احساس عمیق تکرار کنید."],
            "exercise": "🙏 این تمرین ساده را با تمام وجود انجام دهید."
        }

# --- توابعی که در polling_bot.py استفاده می‌شوند ---
def complete_day_for_user(user_id, topic_id, day_number):
    return UserProgressManager().complete_day(user_id, topic_id, day_number)

def get_all_topics():
    return [{"id": tid, **info} for tid, info in TOPICS.items()]

def get_topic_by_id(topic_id):
    return {"id": topic_id, **TOPICS[topic_id]} if topic_id in TOPICS else None

def get_user_topic_progress(user_id, topic_id):
    return UserProgressManager().get_topic_progress(user_id, topic_id)

def start_topic_for_user(user_id, topic_id):
    return load_day_content(topic_id, 1, user_id)
