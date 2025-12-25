import importlib
import json
import os
from typing import Dict, Any, List
from pymongo import MongoClient

# --- اتصال به MongoDB ---
MONGO_URI = os.getenv("MONGO_URI")
if not MONGO_URI:
    print("❌ خطای بحرانی: MONGO_URI در متغیرهای محیطی یافت نشد!")

client = MongoClient(MONGO_URI)
db = client['shoker_gozari_db']
users_col = db['users_progress']

TOPICS = {
    1: {"name": "سلامتی و تندرستی", "folder": "health_wellness", "emoji": "💚", "color": "#2ecc71", "description": "شکرگزاری برای سلامت کامل جسم و روان", "author_quote": "سلامتی بزرگترین هدیه خداوند است - راندا برن", "image": "assets/health.png"},
    2: {"name": "خانواده و روابط", "folder": "family_relationships", "emoji": "👨‍👩‍👧‍👦", "color": "#e74c3c", "description": "شکرگزاری برای پیوندهای انسانی ارزشمند", "author_quote": "خانواده بزرگترین موهبت زندگی است - راندا برن", "image": "assets/family.png"},
    3: {"name": "ثروت و فراوانی", "folder": "wealth_abundance", "emoji": "💰", "color": "#f1c40f", "description": "شکرگزاری برای نعمت‌های مالی و فراوانی", "author_quote": "ثروت واقعی فراوانی در تمام زمینه‌های زندگی است - راندا برن", "image": "assets/wealth.png"},
    4: {"name": "شادی و آرامش", "folder": "happiness_peace", "emoji": "😊", "color": "#3498db", "description": "شکرگزاری برای لحظات شاد و صلح درون", "author_quote": "شادی حقیقی از درون می‌جوشد - راندا برن", "image": "assets/happiness.png"},
    5: {"name": "اهداف و موفقیت", "folder": "goals_success", "emoji": "🎯", "color": "#e67e22", "description": "شکرگزاری برای رشد، پیشرفت و دستاوردها", "author_quote": "هر هدفی با اولین قدم شروع می‌شود - راندا برن", "image": "assets/goals.png"},
    6: {"name": "زندگی مطلوب", "folder": "quality_life", "emoji": "🏠", "color": "#9b59b6", "description": "شکرگزاری برای امکانات و رفاه زندگی", "author_quote": "زندگی هدیه‌ای است که باید قدرش را بدانیم - راندا برن", "image": "assets/quality.png"},
    7: {"name": "طبیعت و کائنات", "folder": "nature_universe", "emoji": "🌿", "color": "#27ae60", "description": "شکرگزاری برای زیبایی‌های آفرینش", "author_quote": "طبیعت بهترین معلم شکرگزاری است - راندا برن", "image": "assets/nature.png"},
    8: {"name": "عشق و معنویت", "folder": "love_spirituality", "emoji": "💖", "color": "#e84393", "description": "شکرگزاری برای عشق الهی و رشد معنوی", "author_quote": "عشق قدرتمندترین نیروی جهان است - راندا برن", "image": "assets/love.png"}
}

WEEK_THEMES = {
    1: {"title": "مبتدی: پایه شکرگزاری", "description": "آشنایی با قدرت شکرگزاری", "quote": "شکرگزاری ساده‌ترین راه برای جذب خوبی‌هاست - راندا برن"},
    2: {"title": "متوسط: عمق بخشیدن", "description": "عمیق‌تر شدن در تمرین شکرگزاری", "quote": "هر چه عمیق‌تر شکرگزاری کنید، معجزه بزرگ‌تری رخ می‌دهد - راندا برن"},
    3: {"title": "پیشرفته: تحول ذهنی", "description": "تغییر الگوهای فکری با شکرگزاری", "quote": "ذهن شکرگزار، ذهن فراوانی است - راندا برن"},
    4: {"title": "استادی: سبک زندگی", "description": "تبدیل شکرگزاری به سبک زندگی", "quote": "شما تبدیل به آنچه شکرگزارش هستید، می‌شوید - راندا برن"}
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
        users_col.update_one({"user_id": str(user_id)}, {"$set": {f"topics.{topic_key}.current_day": day_number, f"topics.{topic_key}.started": True}}, upsert=True)
        return day_number

    def complete_day(self, user_id, topic_id, day_number):
        topic_key = str(topic_id)
        next_day = min(day_number + 1, 28)
        users_col.update_one({"user_id": str(user_id)}, {"$addToSet": {f"topics.{topic_key}.completed_days": day_number}, "$set": {f"topics.{topic_key}.current_day": next_day}}, upsert=True)
        return True

def get_week_info(day_number: int):
    week_number = ((day_number - 1) // 7) + 1
    day_in_week = ((day_number - 1) % 7) + 1
    return week_number, day_in_week

def load_day_content(topic_id: int, day_number: int, user_id: str = None) -> Dict[str, Any]:
    if topic_id not in TOPICS: topic_id = 1
    if user_id:
        day_number = UserProgressManager().set_topic_day(user_id, topic_id, day_number)

    topic = TOPICS[topic_id]
    week_number, day_in_week = get_week_info(day_number)
    week_theme = WEEK_THEMES.get(week_number, WEEK_THEMES[1])
    
    # اصلاح مسیر لود کردن محتوا بر اساس ساختار static/content
    module_path = f"static.content.{topic['folder']}.week_{week_number}"

    try:
        module = importlib.import_module(module_path)
        day_key = f"day_{day_in_week}"
        day_content = getattr(module, day_key)
        return {
            "success": True, "topic_id": topic_id, "topic_name": topic["name"],
            "topic_emoji": topic["emoji"], "topic_color": topic["color"],
            "day_number": day_number, "week_title": week_theme["title"],
            "author_quote": topic.get("author_quote", ""),
            "intro": day_content.get("intro", ""), "items": day_content.get("items", []),
            "exercise": day_content.get("exercise", "")
        }
    except Exception as e:
        print(f"❌ Error loading {module_path}: {e}")
        # رفع باگ KeyError با اضافه کردن week_title به خروجی خطا
        return {
            "success": False, 
            "topic_name": topic["name"], 
            "topic_emoji": topic["emoji"], 
            "day_number": day_number, 
            "week_title": week_theme["title"], # اضافه شد
            "items": ["۱۰ مورد شکرگزاری در دفتر خود بنویسید."], 
            "exercise": "تمرین امروز را با تمرکز انجام دهید."
        }

def complete_day_for_user(user_id: str, topic_id: int, day_number: int): return UserProgressManager().complete_day(user_id, topic_id, day_number)
def get_all_topics(): return [{"id": tid, **info} for tid, info in TOPICS.items()]
def get_topic_by_id(topic_id): return {"id": topic_id, **TOPICS[topic_id]} if topic_id in TOPICS else None
def get_user_topic_progress(user_id, topic_id): return UserProgressManager().get_topic_progress(user_id, topic_id)
def start_topic_for_user(user_id, topic_id): return load_day_content(topic_id, 1, user_id)
