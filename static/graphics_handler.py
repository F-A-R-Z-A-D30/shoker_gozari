import sys
import os

# تنظیم مسیرها برای پیدا کردن loader.py در ریشه پروژه
current_dir = os.path.dirname(os.path.abspath(__file__))
root_path = os.path.dirname(current_dir)
if root_path not in sys.path:
    sys.path.insert(0, root_path)

class GraphicsHandler:

    @staticmethod
    def get_all_topics():
        """دریافت همه موضوعات - برای جلوگیری از import error"""
        try:
            from loader import get_all_topics as get_topics
            return get_topics()
        except ImportError:
            try:
                from static.content.loader import get_all_topics as get_topics
                return get_topics()
            except ImportError:
                # بازگشت به داده‌های پیش‌فرض
                return [
                    {"id": 1, "name": "سلامتی و تندرستی", "emoji": "💚", "image": "assets/health.png"},
                    {"id": 2, "name": "خانواده و روابط", "emoji": "👨‍👩‍👧‍👦", "image": "assets/family.png"},
                    {"id": 3, "name": "ثروت و فراوانی", "emoji": "💰", "image": "assets/wealth.png"},
                    {"id": 4, "name": "شادی و آرامش", "emoji": "😊", "image": "assets/happiness.png"},
                    {"id": 5, "name": "اهداف و موفقیت", "emoji": "🎯", "image": "assets/goals.png"},
                    {"id": 6, "name": "زندگی مطلوب", "emoji": "🏠", "image": "assets/quality.png"},
                    {"id": 7, "name": "طبیعت و کائنات", "emoji": "🌿", "image": "assets/nature.png"},
                    {"id": 8, "name": "عشق و معنویت", "emoji": "💖", "image": "assets/love.png"}
                ]

    @staticmethod
    def load_day_content(topic_id, day_number, user_id=None):
        """لود محتوا با مدیریت خطا"""
        try:
            from loader import load_day_content as load_content
            return load_content(topic_id, day_number, user_id)
        except ImportError:
            try:
                from static.content.loader import load_day_content as load_content
                return load_content(topic_id, day_number, user_id)
            except ImportError:
                # محتوای پیش‌فرض
                return {
                    "success": True,
                    "topic_name": "سلامتی و تندرستی",
                    "topic_emoji": "💚",
                    "week_title": "تمرین روزانه",
                    "author_quote": "«شکرگزاری کلید فراوانی است.»",
                    "intro": "امروز را با شکرگزاری شروع کنید...",
                    "items": [
                        "شکرگزاری برای سلامتی",
                        "شکرگزاری برای خانواده",
                        "شکرگزاری برای شغل",
                        "شکرگزاری برای خانه",
                        "شکرگزاری برای غذا",
                        "شکرگزاری برای هوای پاک",
                        "شکرگزاری برای فرصت‌ها",
                        "شکرگزاری برای چالش‌های رشد‌دهنده",
                        "شکرگزاری برای تجربیات ارزشمند",
                        "شکرگزاری برای همین لحظه زندگی"
                    ],
                    "exercise": "📖 این ۱۰ مورد را در دفتر شکرگزاری خود بنویسید و هر کدام را با احساس قدردانی تکرار کنید."
                }

    @staticmethod
    def load_past_day_content(topic_id, day_number, user_id=None):
        """لود محتوای روزهای گذشته"""
        try:
            from loader import load_past_day_content as load_past_content
            return load_past_content(topic_id, day_number, user_id)
        except ImportError:
            try:
                from static.content.loader import load_past_day_content as load_past_content
                return load_past_content(topic_id, day_number, user_id)
            except ImportError:
                # محتوای پیش‌فرض برای مرور
                return {
                    "success": True,
                    "topic_name": "سلامتی و تندرستی",
                    "topic_emoji": "💚",
                    "week_title": "مرور تمرین گذشته",
                    "author_quote": "«مرور شکرگزاری‌ها، معجزه را تازه می‌کند.»",
                    "intro": "امروز را با مرور شکرگزاری‌های گذشته آغاز می‌کنیم...",
                    "items": [
                        "مرور شکرگزاری برای سلامتی",
                        "مرور شکرگزاری برای خانواده",
                        "مرور شکرگزاری برای شغل",
                        "مرور شکرگزاری برای خانه",
                        "مرور شکرگزاری برای غذا",
                        "مرور شکرگزاری برای هوای پاک",
                        "مرور شکرگزاری برای فرصت‌ها",
                        "مرور شکرگزاری برای چالش‌ها",
                        "مرور شکرگزاری برای تجربیات",
                        "مرور شکرگزاری برای لحظات زندگی"
                    ],
                    "exercise": "🙏 با احساس قدردانی، روزهای گذشته را مرور کنید."
                }

    @staticmethod
    def create_beautiful_message(topic_name, day_number, user_progress=None):
        """🎨 ساخت پیام گرافیکی زیبا برای تمرین روزانه"""
        topics = GraphicsHandler.get_all_topics()
        topic_id = None
        
        for topic in topics:
            if topic["name"] == topic_name or topic["name"] in topic_name:
                topic_id = topic["id"]
                break

        if not topic_id:
            return "⚠️ موضوع مورد نظر یافت نشد."

        content = GraphicsHandler.load_day_content(topic_id, day_number)
        if not content or not content.get("success", True):
            return "❌ محتوای مورد نظر یافت نشد."

        emoji = content.get("topic_emoji", "✨")
        topic_emoji = emoji * 3

        is_completed = False
        if user_progress and "completed_days" in user_progress:
            is_completed = day_number in user_progress["completed_days"]

        t_name = content.get('topic_name', 'موضوع')
        w_title = content.get('week_title', 'تمرین روزانه')
        a_quote = content.get('author_quote') or content.get('week_quote', '🌟 «شکرگزاری کلید فراوانی است.»')
        intro_text = content.get('intro', '')

        message = f"""
{topic_emoji}
🎯 {t_name}
─────────────────
📅 روز {day_number} از ۲۸
🎭 {w_title}

💫 {a_quote}

🌟 امروز:
{intro_text}
─────────────────
🙏 شکرگزاری‌های امروز:
"""
        items = content.get("items", [])
        for i, item in enumerate(items[:10], 1):
            if is_completed:
                message += f"\n✅ {item}"
            else:
                message += f"\n{emoji} {item}"

        message += """
─────────────────
"""

        if content.get('exercise'):
            message += f"""
💡 تمرین امروز:
{content['exercise']}
─────────────────
"""

        if is_completed:
            message += """
✅ این روز با موفقیت تکمیل شد!
✨ شما یک قدم به تحول نزدیک‌تر شدید.
"""
        else:
            message += """
🚀 آماده اید؟
روی دکمه «امروز شکرگزار بودم» کلیک کنید.
معجزه در یک کلیک آغاز می‌شود...
"""

        return message

    @staticmethod
    def create_categories_keyboard():
        """🎯 ساخت کیبورد موضوعات اصلی"""
        topics = GraphicsHandler.get_all_topics()
        keyboard = {"keyboard": [], "resize_keyboard": True}

        row = []
        for i, topic in enumerate(topics):
            button_text = f"{topic['emoji']} {topic['name']}"
            row.append(button_text)
            
            if (i + 1) % 2 == 0:
                keyboard["keyboard"].append(row)
                row = []
        
        if row:
            keyboard["keyboard"].append(row)

        keyboard["keyboard"].append(["📊 پیشرفت کلی", "❓ راهنما"])
        keyboard["keyboard"].append(["👨‍💻 ارتباط با من", "💝 حمایت"])
        
        return keyboard

    @staticmethod
    def create_day_inline_keyboard(topic_id, day_number, is_completed=False, completed_days=None):
        """🔘 ساخت دکمه‌های اینلاین زیبا"""
        topics = GraphicsHandler.get_all_topics()
        topic_emoji = "🙏"
        
        for topic in topics:
            if topic["id"] == topic_id:
                topic_emoji = topic["emoji"]
                break

        keyboard = {"inline_keyboard": []}

        if is_completed:
            button_text = f"✅ روز {day_number} تکمیل شد"
        else:
            button_text = f"{topic_emoji} امروز شکرگزار بودم"
        
        keyboard["inline_keyboard"].append([
            {
                "text": button_text,
                "callback_data": f"complete_{topic_id}_{day_number}"
            }
        ])

        if completed_days and len(completed_days) > 0:
            keyboard["inline_keyboard"].append([
                {"text": "📖 مرور روزهای گذشته", "callback_data": f"review_{topic_id}"}
            ])

        keyboard["inline_keyboard"].append([
            {"text": f"📊 پیشرفت", "callback_data": f"progress_{topic_id}"},
            {"text": f"🎯 موضوعات", "callback_data": "categories"}
        ])

        return keyboard

    @staticmethod
    def create_day_options_keyboard(topic_id, completed_days):
        """ساخت کیبورد گزینه‌های روز"""
        keyboard = {"inline_keyboard": []}
        
        if completed_days:
            keyboard["inline_keyboard"].append([
                {"text": "📖 مرور روزهای گذشته", "callback_data": f"review_{topic_id}"}
            ])
        
        keyboard["inline_keyboard"].append([
            {"text": "🎯 موضوعات دیگر", "callback_data": "categories"},
            {"text": "📊 پیشرفت کلی", "callback_data": "overall_progress"}
        ])
        
        return keyboard

    @staticmethod
    def create_past_days_keyboard(topic_id, completed_days):
        """ساخت کیبورد برای انتخاب روزهای گذشته"""
        keyboard = {"inline_keyboard": []}
        
        row = []
        for day in sorted(completed_days):
            row.append({
                "text": f"📅 روز {day}",
                "callback_data": f"pastday_{topic_id}_{day}"
            })
            
            if len(row) == 3:
                keyboard["inline_keyboard"].append(row)
                row = []
        
        if row:
            keyboard["inline_keyboard"].append(row)
        
        keyboard["inline_keyboard"].append([
            {"text": "🔙 بازگشت", "callback_data": f"cat_{topic_id}"},
            {"text": "🏠 منوی اصلی", "callback_data": "main_menu"}
        ])
        
        return keyboard

    @staticmethod
    def create_review_keyboard(topic_id, day_number, completed_days):
        """ساخت کیبورد برای صفحه مرور روز گذشته"""
        keyboard = {"inline_keyboard": []}
        
        # بررسی آیا روز بعدی هم موجود است
        if day_number < 28 and (day_number + 1) in completed_days:
            keyboard["inline_keyboard"].append([
                {"text": "➡️ روز بعدی", "callback_data": f"pastday_{topic_id}_{day_number + 1}"}
            ])
        
        keyboard["inline_keyboard"].append([
            {"text": "📖 همه روزها", "callback_data": f"review_{topic_id}"},
            {"text": "🔙 بازگشت", "callback_data": f"cat_{topic_id}"}
        ])
        
        return keyboard

    @staticmethod
    def create_main_menu_keyboard():
        """🏠 منوی اصلی پایین صفحه"""
        return {
            "keyboard": [
                ["🎯 موضوعات شکرگزاری"],
                ["📊 پیشرفت کلی", "❓ راهنما"],
                ["👨‍💻 ارتباط با من", "💝 حمایت"]
            ],
            "resize_keyboard": True
        }

    @staticmethod
    def create_welcome_message(first_name=""):
        """🎉 پیام خوش‌آمدگویی زیبا"""
        if first_name:
            greeting = f"سلام {first_name} عزیز! 🌟"
        else:
            greeting = "سلام عزیز! 🌟"
            
        return f"""
{greeting}

══════════════════
✨ به ربات معجزه شکرگزاری خوش آمدید ✨
══════════════════

📚 بر اساس کتاب:
«معجزه شکرگزاری» اثر راندا برن

🎯 هدف ربات:
• تغییر نگرش در ۲۸ روز
• تمرکز بر داشته‌ها
• جذب فراوانی

💫 ۸ حوزه اصلی زندگی:
💚 سلامتی و تندرستی
👨‍👩‍👧‍👦 خانواده و روابط  
💰 ثروت و فراوانی
😊 شادی و آرامش
🎯 اهداف و موفقیت
🏠 زندگی مطلوب
🌿 طبیعت و کائنات
💖 عشق و معنویت

══════════════════
🚀 بیایید معجزه را آغاز کنیم!
✨ شروع سفر ۲۸ روزه تحول...
"""

    @staticmethod
    def create_help_message():
        """📖 راهنمای کاربردی و زیبا"""
        return """
❓ راهنمای استفاده از ربات

─────────────────

🎯 روش کار:
۱. موضوع مورد نظر را انتخاب کنید
۲. هر روز ۱۰ مورد شکرگزاری دریافت می‌کنید
۳. تمرین روز را با دقت انجام دهید
۴. دکمه «امروز شکرگزار بودم» را بزنید

⏰ زمان‌بندی:
• هر روز ساعت ۶ صبح تمرین جدید باز می‌شود
• ۲۴ ساعت فرصت دارید تمرین را کامل کنید
• تعهد ۲۸ روزه برای تحول ذهنی

💡 نکات مهم:
• با احساس بخوانید و بنویسید
• در جای آرام تمرین کنید  
• تغییرات را یادداشت کنید
• صبور باشید، معجزه تدریجی است

─────────────────

✨ راز موفقیت:
"تعهد + عمل = معجزه"

🌟 شما می‌توانید!
"""

    @staticmethod
    def create_contact_message():
        """📞 اطلاعات تماس زیبا"""
        return """
👨‍💻 ارتباط با توسعه‌دهنده

─────────────────

🎯 فرزاد قجری
• توسعه‌دهنده ربات شکرگزاری
• برنامه‌نویس پایتون و وب

📱 تماس مستقیم:
۰۹۳۰۲۴۴۶۱۴۱

📧 ایمیل:
farzadq.ir@gmail.com

🌐 وب‌سایت:
www.danekar.ir

─────────────────

💼 خدمات ارائه شده:
✅ طراحی و توسعه ربات‌های هوشمند
✅ طراحی وب‌سایت‌های اختصاصی  
✅ آموزش برنامه‌نویسی (مبتدی تا پیشرفته)
✅ مشاوره فنی و راه‌اندازی استارتاپ

─────────────────

✨ شکرگزار فرصت همکاری ✨
"""

    @staticmethod
    def get_topic_image(topic_id):
        """دریافت مسیر تصویر موضوع"""
        topics = GraphicsHandler.get_all_topics()
        for topic in topics:
            if topic["id"] == topic_id:
                # اگر مسیر نسبی داده شده، مسیر کامل بساز
                image_path = topic.get("image", "")
                if image_path and not os.path.isabs(image_path):
                    # ساخت مسیر کامل از ریشه پروژه
                    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
                    full_path = os.path.join(base_dir, image_path)
                    if os.path.exists(full_path):
                        return full_path
                return image_path
        return None
