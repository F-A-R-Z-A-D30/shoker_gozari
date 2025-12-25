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
    1: {"name": "سلامتی و تندرستی", "folder": "health_wellness", "emoji": "💚", "color": "#2ecc71", "image": "assets/health.png"},
    2: {"name": "خانواده و روابط", "folder": "family_relationships", "emoji": "👨‍👩‍👧‍👦", "color": "#e74c3c", "image": "assets/family.png"},
    3: {"name": "ثروت و فراوانی", "folder": "wealth_abundance", "emoji": "💰", "color": "#f1c40f", "image": "assets/wealth.png"},
    4: {"name": "شادی و آرامش", "folder": "happiness_peace", "emoji": "😊", "color": "#3498db", "image": "assets/happiness.png"},
    5: {"name": "اهداف و موفقیت", "folder": "goals_success", "emoji": "🎯", "color": "#e67e22", "image": "assets/goals.png"},
    6: {"name": "زندگی مطلوب", "folder": "quality_life", "emoji": "🏠", "color": "#9b59b6", "image": "assets/quality.png"},
    7: {"name": "طبیعت و کائنات", "folder": "nature_universe", "emoji": "🌿", "color": "#27ae60", "image": "assets/nature.png"},
    8: {"name": "عشق و معنویت", "folder": "love_spirituality", "emoji": "💖", "color": "#e84393", "image": "assets/love.png"}
}

WEEK_THEMES = {
    1: {"title": "مبتدی: پایه شکرگزاری"},
    2: {"title": "متوسط: عمق بخشیدن"},
    3: {"title": "پیشرفته: تحول ذهنی"},
    4: {"title": "استادی: سبک زندگی"}
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
    
    # تنظیم مسیر دقیق بر اساس ساختار پوشه‌های محتوا در ریشه پروژه
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
            "day_number": day_number,
            "week_title": week_info.get("title", "تمرین روزانه"),
            "author_quote": week_info.get("quote", "شکرگزاری کلید فراوانی است."),
            "intro": day_data.get("intro", ""),
            "items": day_data.get("items", []),
            "exercise": day_data.get("exercise", "")
        }
    except Exception as e:
        print(f"❌ Error loading {module_path}: {e}")
        return {
            "success": False,
            "topic_name": topic["name"],
            "topic_emoji": topic["emoji"],
            "day_number": day_number,
            "week_title": "آموزش شکرگزاری",
            "items": ["۱۰ مورد شکرگزاری در دفتر خود بنویسید."],
            "exercise": "تمرین امروز را با تمرکز انجام دهید."
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
    """این همان تابعی است که خطای ImportError می‌داد"""
    return load_day_content(topic_id, 1, user_id)
