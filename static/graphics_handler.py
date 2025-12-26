import sys
import os

# تنظیم مسیرها برای پیدا کردن loader.py در ریشه پروژه
current_dir = os.path.dirname(os.path.abspath(__file__))
root_path = os.path.dirname(current_dir)
if root_path not in sys.path:
    sys.path.insert(0, root_path)

# مدیریت هوشمند وارد کردن لودر
try:
    from loader import get_all_topics, load_day_content, load_past_day_content
except ImportError:
    try:
        from static.content.loader import get_all_topics, load_day_content, load_past_day_content
    except ImportError:
        try:
            import loader
            get_all_topics = loader.get_all_topics
            load_day_content = loader.load_day_content
            load_past_day_content = loader.load_past_day_content
        except Exception as e:
            print(f"✨ <b>GraphicsHandler: لودر یافت نشد</b>\n📝 {e}")

class GraphicsHandler:

    @staticmethod
    def create_beautiful_message(topic_name, day_number, user_progress=None):
        """🎨 ساخت پیام گرافیکی زیبا برای تمرین روزانه"""
        topics = get_all_topics()
        topic_id = None
        
        # 🔍 پیدا کردن ID موضوع
        for topic in topics:
            if topic["name"] in topic_name:
                topic_id = topic["id"]
                break

        if not topic_id:
            return "⚠️ <b>موضوع مورد نظر یافت نشد.</b>"

        content = load_day_content(topic_id, day_number)
        if not content:
            return "❌ <b>محتوای مورد نظر یافت نشد.</b>"

        emoji = content.get("topic_emoji", "✨")
        topic_emoji = emoji * 3

        is_completed = False
        if user_progress and "completed_days" in user_progress:
            is_completed = day_number in user_progress["completed_days"]

        # 📊 استخراج داده‌ها
        t_name = content.get('topic_name', 'موضوع')
        w_title = content.get('week_title', 'تمرین روزانه')
        a_quote = content.get('author_quote') or content.get('week_quote', '🌟 <i>«شکرگزاری کلید فراوانی است.»</i>')
        intro_text = content.get('intro', '')

        # 🎨 ساخت پیام زیبا
        message = f"""
{topic_emoji}
<b>🎯 {t_name}</b>
<code>─────────────────</code>
<b>📅 روز {day_number} از ۲۸</b>
🎭 {w_title}

💫 {a_quote}

<b>🌟 امروز:</b>
{intro_text}
<code>─────────────────</code>
<b>🙏 شکرگزاری‌های امروز:</b>
"""
        # 📝 اضافه کردن لیست موارد با ایموجی موضوع
        items = content.get("items", [])
        for i, item in enumerate(items[:10], 1):
            if is_completed:
                message += f"\n✅ {item}"
            else:
                message += f"\n{emoji} {item}"

        message += """
<code>─────────────────</code>
"""

        if content.get('exercise'):
            message += f"""
<b>💡 تمرین امروز:</b>
{content['exercise']}
<code>─────────────────</code>
"""

        if is_completed:
            message += """
<b>✅ این روز با موفقیت تکمیل شد!</b>
✨ <i>شما یک قدم به تحول نزدیک‌تر شدید.</i>
"""
        else:
            message += """
<b>🚀 آماده اید؟</b>
روی دکمه «امروز شکرگزار بودم» کلیک کنید.
<i>معجزه در یک کلیک آغاز می‌شود...</i>
"""

        return message

    @staticmethod
    def create_categories_keyboard():
        """🎯 ساخت کیبورد موضوعات اصلی"""
        topics = get_all_topics()
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
        topics = get_all_topics()
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

        # اگر روزهای گذشته برای مرور وجود دارد، دکمه مرور اضافه شود
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
        """ساخت کیبورد گزینه‌های روز (شامل مرور گذشته)"""
        keyboard = {"inline_keyboard": []}
        
        if completed_days:
            keyboard["inline_keyboard"].append([
                {"text": "📖 مرور روزهای گذشته", "callback_data": f"review_{topic_id}"}
            ])
        
        keyboard["inline_keyboard"].append([
            {"text": "🎯 موضوعات دیگر", "callback_data": "categories"},
            {"text": "📊 پیشرفت", "callback_data": f"progress_{topic_id}"}
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
            greeting = f"سلام <b>{first_name}</b> عزیز! 🌟"
        else:
            greeting = "سلام عزیز! 🌟"
            
        return f"""
{greeting}

<code>══════════════════</code>
<b>✨ به ربات معجزه شکرگزاری خوش آمدید ✨</b>
<code>══════════════════</code>

<b>📚 بر اساس کتاب:</b>
«معجزه شکرگزاری» اثر <b>راندا برن</b>

<b>🎯 هدف ربات:</b>
• تغییر نگرش در ۲۸ روز
• تمرکز بر داشته‌ها
• جذب فراوانی

<b>💫 ۸ حوزه اصلی زندگی:</b>
💚 سلامتی و تندرستی
👨‍👩‍👧‍👦 خانواده و روابط  
💰 ثروت و فراوانی
😊 شادی و آرامش
🎯 اهداف و موفقیت
🏠 زندگی مطلوب
🌿 طبیعت و کائنات
💖 عشق و معنویت

<code>══════════════════</code>
<b>🚀 بیایید معجزه را آغاز کنیم!</b>
"""

    @staticmethod
    def create_help_message():
        """📖 راهنمای کاربردی و زیبا"""
        return """
<b>❓ راهنمای استفاده از ربات</b>

<code>─────────────────</code>

<b>🎯 روش کار:</b>
۱. موضوع مورد نظر را انتخاب کنید
۲. هر روز ۱۰ مورد شکرگزاری دریافت می‌کنید
۳. تمرین روز را با دقت انجام دهید
۴. دکمه «امروز شکرگزار بودم» را بزنید

<b>⏰ زمان‌بندی:</b>
• هر روز ساعت ۶ صبح تمرین جدید باز می‌شود
• ۲۴ ساعت فرصت دارید تمرین را کامل کنید
• تعهد ۲۸ روزه برای تحول ذهنی

<b>💡 نکات مهم:</b>
• با احساس بخوانید و بنویسید
• در جای آرام تمرین کنید  
• تغییرات را یادداشت کنید
• صبور باشید، معجزه تدریجی است

<code>─────────────────</code>

<b>✨ راز موفقیت:</b>
<i>«تعهد + عمل = معجزه»</i>

<b>🌟 شما می‌توانید!</b>
"""

    @staticmethod
    def create_contact_message():
        """📞 اطلاعات تماس زیبا"""
        return """
<b>👨‍💻 ارتباط با توسعه‌دهنده</b>

<code>─────────────────</code>

<b>🎯 فرزاد قجری</b>
• توسعه‌دهنده ربات شکرگزاری
• برنامه‌نویس پایتون و وب

<b>📱 تماس مستقیم:</b>
<code>۰۹۳۰۲۴۴۶۱۴۱</code>

<b>📧 ایمیل:</b>
<code>farzadq.ir@gmail.com</code>

<b>🌐 وب‌سایت:</b>
<code>www.danekar.ir</code>

<code>─────────────────</code>

<b>💼 خدمات ارائه شده:</b>
✅ طراحی و توسعه ربات‌های هوشمند
✅ طراحی وب‌سایت‌های اختصاصی  
✅ آموزش برنامه‌نویسی (مبتدی تا پیشرفته)
✅ مشاوره فنی و راه‌اندازی استارتاپ

<code>─────────────────</code>

<b>✨ شکرگزار فرصت همکاری ✨</b>
"""
