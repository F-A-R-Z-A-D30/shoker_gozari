import sys
import os

# تنظیم مسیرها برای پیدا کردن loader.py در ریشه پروژه
current_dir = os.path.dirname(os.path.abspath(__file__))
root_path = os.path.dirname(current_dir)
if root_path not in sys.path:
    sys.path.insert(0, root_path)

# مدیریت هوشمند وارد کردن لودر
try:
    from loader import get_all_topics, load_day_content
except ImportError:
    try:
        from static.content.loader import get_all_topics, load_day_content
    except ImportError:
        try:
            import loader
            get_all_topics = loader.get_all_topics
            load_day_content = loader.load_day_content
        except Exception as e:
            print(f"❌ GraphicsHandler could not import loader: {e}")

class GraphicsHandler:

    @staticmethod
    def create_beautiful_message(topic_name, day_number, user_progress=None):
        """ساخت پیام گرافیکی زیبا برای یک روز با فرمت HTML بله"""
        topics = get_all_topics()
        topic_id = None
        
        # پیدا کردن ID موضوع بر اساس نام
        for topic in topics:
            if topic["name"] in topic_name:
                topic_id = topic["id"]
                break

        if not topic_id:
            return "❌ موضوع مورد نظر یافت نشد."

        content = load_day_content(topic_id, day_number)
        if not content:
            return "❌ محتوای مورد نظر یافت نشد."

        emoji = content.get("topic_emoji", "✨")
        topic_emoji = emoji * 3

        is_completed = False
        if user_progress and "completed_days" in user_progress:
            is_completed = day_number in user_progress["completed_days"]

        # استخراج داده‌ها با استفاده از .get برای جلوگیری از KeyError
        t_name = content.get('topic_name', 'موضوع')
        w_title = content.get('week_title', 'تمرین روزانه')
        a_quote = content.get('author_quote') or content.get('week_quote', 'شکرگزاری کلید فراوانی است.')
        intro_text = content.get('intro', '')

        message = f"""
{topic_emoji}
<b>{t_name}</b>
📅 روز {day_number} از ۲۸ • {w_title}

📖 <i>{a_quote}</i>

{intro_text}
──────────────
{emoji} <b>۱۰ شکرگزاری امروز:</b>
"""
        # اضافه کردن لیست موارد
        items = content.get("items", [])
        for i, item in enumerate(items[:10], 1):
            message += f"\n{i}. {item}"

        message += "\n──────────────\n"

        if content.get('exercise'):
            message += f"💡 <b>تمرین امروز:</b>\n{content['exercise']}\n\n"

        if is_completed:
            message += "✅ <b>این روز با موفقیت تکمیل شده است.</b>"
        else:
            message += f"🌟 پس از خواندن، دکمه 'امروز شکرگزار بودم' را بزنید."

        return message

    @staticmethod
    def create_categories_keyboard():
        """ساخت کیبورد اصلی موضوعات (Reply Keyboard)"""
        topics = get_all_topics()
        keyboard = {"keyboard": [], "resize_keyboard": True}

        row = []
        for i, topic in enumerate(topics):
            row.append(f"{topic['emoji']} {topic['name']}")
            if (i + 1) % 2 == 0:
                keyboard["keyboard"].append(row)
                row = []
        if row:
            keyboard["keyboard"].append(row)

        keyboard["keyboard"].append(["📊 پیشرفت کلی", "❓ راهنما"])
        keyboard["keyboard"].append(["👨‍💻 ارتباط با من"])
        return keyboard

    @staticmethod
    def create_day_inline_keyboard(topic_id, day_number, is_completed=False):
        """ساخت دکمه‌های شیشه‌ای زیر هر تمرین"""
        topics = get_all_topics()
        topic_emoji = "🙏"
        for topic in topics:
            if topic["id"] == topic_id:
                topic_emoji = topic["emoji"]
                break

        keyboard = {"inline_keyboard": []}

        button_text = "✅ این روز ثبت شده" if is_completed else f"{topic_emoji} امروز شکرگزار بودم"
        
        keyboard["inline_keyboard"].append([
            {
                "text": button_text,
                "callback_data": f"complete_{topic_id}_{day_number}"
            }
        ])

        keyboard["inline_keyboard"].append([
            {"text": "📊 پیشرفت موضوع", "callback_data": f"progress_{topic_id}"},
            {"text": "🎯 موضوعات دیگر", "callback_data": "categories"}
        ])

        return keyboard

    @staticmethod
    def create_main_menu_keyboard():
        """منوی اصلی پایین صفحه"""
        return {
            "keyboard": [
                ["🎯 موضوعات شکرگزاری"],
                ["📊 پیشرفت کلی", "❓ راهنما"],
                ["👨‍💻 ارتباط با من"]
            ],
            "resize_keyboard": True
        }

    @staticmethod
    def create_welcome_message(first_name=""):
        return f"""
✨✨✨
<b>سلام! به ربات معجزه شکرگزاری خوش آمدید</b>

📖 بر اساس کتاب معجزه شکرگزاری اثر راندا برن

👨‍💻 <b>توسعه‌دهنده: فرزاد قجری</b>
من باور دارم شکرگزاری می‌تواند زندگی را متحول کند. این ربات هدیه‌ای است برای تمرکز بر داشته‌هایمان.

💫 <b>۸ حوزه اصلی زندگی:</b>
از سلامتی و روابط تا ثروت و معنویت.

<b>بیایید شروع کنیم!</b>
"""

    @staticmethod
    def create_help_message():
        return """
❓ <b>راهنمای استفاده</b>

۱. یک موضوع انتخاب کنید.
۲. هر روز ۱۰ مورد شکرگزاری مخصوص دریافت می‌کنید.
۳. بعد از مطالعه، حتماً دکمه <b>امروز شکرگزار بودم</b> را بزنید.
۴. هر ۲۴ ساعت (ساعت ۶ صبح) تمرین جدید باز می‌شود.

تعهد ۲۸ روزه باعث تغییر مدار ذهنی شما می‌شود. 💫
"""

    @staticmethod
    def create_contact_message():
        return """
👨‍💻 <b>ارتباط با فرزاد قجری</b>

📱 تماس: <code>09302446141</code>
📧 ایمیل: <code>farzadq.ir@gmail.com</code>

🎯 طراحی و توسعه انواع ربات‌های هوشمند و وب‌سایت‌های اختصاصی.
"""
