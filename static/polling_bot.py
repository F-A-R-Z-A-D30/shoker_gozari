import json
import os
import time
import requests
from dotenv import load_dotenv

from static.graphics_handler import GraphicsHandler
from static.content.loader import (
    load_day_content,
    get_all_topics,
    get_topic_by_id,
    start_topic_for_user,
    complete_day_for_user,
    get_user_topic_progress
)

# ایمپورت مدیر بازنشانی روزانه
from daily_reset import daily_reset

# بارگذاری متغیرهای محیطی
load_dotenv()

# خواندن توکن
BOT_TOKEN = os.getenv('BALE_BOT_TOKEN')
if not BOT_TOKEN:
    print("❌ خطا: توکن ربات در فایل .env یافت نشد!")
    exit()

BASE_URL = f"https://tapi.bale.ai/bot{BOT_TOKEN}"


# ========== توابع اصلی ربات ==========

def send_message(chat_id, text, keyboard=None):
    url = f"{BASE_URL}/sendMessage"
    data = {
        "chat_id": chat_id,
        "text": text,
        "parse_mode": "HTML"
    }

    if keyboard:
        data["reply_markup"] = json.dumps(keyboard)

    try:
        response = requests.post(url, json=data, timeout=30)
        result = response.json()

        if not result.get("ok"):
            print(f"❌ خطای API: {result}")

        return result
    except Exception as e:
        print(f"❌ خطا در ارسال پیام: {e}")
        return None


def get_updates(last_update_id=0):
    url = f"{BASE_URL}/getUpdates"
    params = {
        "offset": last_update_id + 1,
        "timeout": 30,
        "limit": 100
    }

    try:
        response = requests.get(url, params=params, timeout=35)
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"⚠️ خطا در دریافت پیام‌ها: {e}")
        time.sleep(5)
        return {"ok": False}
    except Exception as e:
        print(f"❌ خطای ناشناخته: {e}")
        return {"ok": False}


def answer_callback(callback_id):
    url = f"{BASE_URL}/answerCallbackQuery"
    data = {"callback_query_id": callback_id}
    try:
        requests.post(url, json=data, timeout=5)
    except:
        pass


# ========== تابع پرداخت ساده ==========

def send_donation_invoice(chat_id, user_id, amount=10000):
    """ارسال صورتحساب برای حمایت مالی با مبلغ دلخواه"""

    provider_token = os.getenv('BALE_PROVIDER_TOKEN')
    if not provider_token:
        print("❌ خطا: provider_token در .env تنظیم نشده!")
        send_message(chat_id, "⚠️ سیستم پرداخت موقتاً غیرفعال است.")
        return False

    # ارسال صورتحساب
    url = f"{BASE_URL}/sendInvoice"

    data = {
        "chat_id": chat_id,
        "title": "حمایت از توسعه‌دهنده",
        "description": f"حمایت مالی داوطلبانه به مبلغ {amount:,} ریال\n(هر مبلغی که مایل باشید)",
        "payload": f"donation_{user_id}_{int(time.time())}",
        "provider_token": provider_token,
        "currency": "IRT",
        "prices": [
            {
                "label": "حمایت مالی داوطلبانه",
                "amount": amount  # مبلغ به ریال
            }
        ]
    }

    try:
        response = requests.post(url, json=data, timeout=30)
        result = response.json()

        if result.get("ok"):
            print(f"✅ Invoice حمایت ارسال شد برای کاربر {user_id} - مبلغ: {amount:,} ریال")
            return True
        else:
            print(f"❌ خطا در ارسال Invoice: {result}")
            return False
    except Exception as e:
        print(f"❌ خطا در ارسال invoice: {e}")
        return False


def handle_successful_payment(update):
    """پردازش پرداخت موفق"""
    message = update.get("message")
    if not message or "successful_payment" not in message:
        return None

    payment = message["successful_payment"]
    user_id = message["from"]["id"]
    chat_id = message["chat"]["id"]
    payload = payment["invoice_payload"]
    amount = payment["total_amount"]

    print(f"💰 پرداخت موفق از کاربر {user_id}")
    print(f"💵 مبلغ: {amount:,} ریال")

    # ارسال تشکر
    amount_toman = amount / 10  # تبدیل به تومان
    message_text = f"""
💖 <b>با تشکر از حمایت شما!</b>

✅ مبلغ <b>{amount_toman:,.0f} تومان</b> با موفقیت دریافت شد
🌟 حمایت شما انگیزه‌ای برای توسعه ربات است
🙏 از لطف و همراهی شما سپاسگزاریم

📞 برای پیگیری: @farzadQ_ir
"""

    send_message(chat_id, message_text)
    return True


# ========== توابع کیبورد ==========

def create_categories_keyboard():
    keyboard = GraphicsHandler.create_categories_keyboard()
    return keyboard


def create_main_menu_keyboard():
    keyboard = GraphicsHandler.create_main_menu_keyboard()
    return keyboard


def create_start_keyboard():
    """کیبورد شروع با دکمه حمایت"""
    keyboard = {
        "inline_keyboard": [
            [
                {"text": "💖 حمایت از توسعه‌دهنده", "callback_data": "support_options"}
            ],
            [
                {"text": "🚀 شروع استفاده از ربات", "callback_data": "start_using"}
            ]
        ]
    }
    return keyboard


def create_support_options_keyboard():
    """کیبورد انتخاب مبلغ حمایت"""
    keyboard = {
        "inline_keyboard": [
            [
                {"text": "۱۰,۰۰۰ تومان", "callback_data": "support_10000"},
                {"text": "۲۰,۰۰۰ تومان", "callback_data": "support_20000"}
            ],
            [
                {"text": "۵۰,۰۰۰ تومان", "callback_data": "support_50000"},
                {"text": "۱۰۰,۰۰۰ تومان", "callback_data": "support_100000"}
            ],
            [
                {"text": "💰 مبلغ دلخواه", "callback_data": "support_custom"},
                {"text": "⏪ بازگشت", "callback_data": "support_back"}
            ]
        ]
    }
    return keyboard


# ========== توابع پردازش پیام ==========

def handle_start(chat_id, user_id, username, first_name):
    welcome_text = GraphicsHandler.create_welcome_message()

    # ارسال پیام خوش‌آمد با دکمه حمایت
    send_message(chat_id, welcome_text)
    time.sleep(1)

    # ارسال دکمه‌های شروع
    start_text = """
🎯 <b>برای شروع کار با ربات، یکی از گزینه‌های زیر را انتخاب کنید:</b>

• <b>استفاده رایگان:</b> تمام محتوای ربات به صورت کاملاً رایگان در دسترس شماست
• <b>حمایت داوطلبانه:</b> اگر از ربات راضی هستید و می‌خواهید از توسعه‌دهنده حمایت کنید

💝 <i>ربات به صورت کاملاً رایگان ارائه می‌شود. حمایت شما اختیاری و داوطلبانه است.</i>
"""

    start_keyboard = create_start_keyboard()
    send_message(chat_id, start_text, start_keyboard)


def handle_support_options(chat_id, user_id):
    """نمایش گزینه‌های حمایت"""
    support_text = """
💖 <b>انتخاب مبلغ حمایت</b>

لطفاً یکی از مبالغ زیر را انتخاب کنید یا مبلغ دلخواه خود را وارد کنید:

🌟 <b>گزینه‌های موجود:</b>
• ۱۰,۰۰۰ تومان
• ۲۰,۰۰۰ تومان  
• ۵۰,۰۰۰ تومان
• ۱۰۰,۰۰۰ تومان
• یا هر مبلغ دلخواه دیگری

🙏 <i>هر مبلغی که مایل باشید قابل قبول است. هدف فقط حمایت و قدردانی است.</i>
"""

    support_keyboard = create_support_options_keyboard()
    send_message(chat_id, support_text, support_keyboard)


def handle_category_selection(chat_id, user_id, topic_id):
    """پردازش انتخاب موضوع - با سیستم ساعت ۶ صبح"""

    try:
        # بررسی دسترسی روزانه
        access_info = daily_reset.get_access_info(user_id, topic_id)

        if not access_info["has_access"]:
            # کاربر امروز دسترسی نداشته یا قبل از ۶ صبح دسترسی داشته
            topic_info = get_topic_by_id(topic_id)
            topic_name = topic_info['name'] if topic_info else "این موضوع"
            topic_emoji = topic_info['emoji'] if topic_info else "⏰"

            last_day = access_info.get("last_day", 0)

            if last_day > 0:
                # کاربر قبلاً روزی را دیده
                message = f"""
⏰ <b>زمان برای روز جدید هنوز نرسیده!</b>

{topic_emoji} <b>سیستم روزانه شکرگزاری</b>

✅ آخرین روزی که کامل کردید: <b>روز {last_day}</b>
🕕 بازنشانی روزانه: <b>ساعت ۶ صبح</b>
⏳ زمان باقیمانده: <b>{access_info['remaining_text']}</b>

📅 <i>برای مشاهده روز {last_day + 1}:</i>

1️⃣ تا ساعت <b>{access_info['next_reset_human']}</b> صبر کنید
2️⃣ سپس دوباره این موضوع را انتخاب کنید

🌟 <b>چرا سیستم ساعت ۶ صبح؟</b>
• ایجاد نظم صبحگاهی در شکرگزاری
• شروع روز با انرژی مثبت
• تبدیل به عادت پایدار روزانه

💡 <i>شما می‌توانید روزهای قبلی را مرور کنید...</i>
"""

                keyboard = {
                    "inline_keyboard": [
                        [
                            {"text": f"📖 بازخوانی روز {last_day}", "callback_data": f"review_{topic_id}_{last_day}"}
                        ],
                        [
                            {"text": "🎯 انتخاب موضوع دیگر", "callback_data": "categories"},
                            {"text": "📊 پیشرفت من", "callback_data": "progress"}
                        ]
                    ]
                }

                send_message(chat_id, message, keyboard)
                return
            else:
                # کاربر قبلاً هیچ روزی ندیده اما دسترسی ندارد (مورد عجیب)
                message = "⚠️ خطا در سیستم زمان‌بندی. لطفاً دوباره تلاش کنید."
                send_message(chat_id, message)
                return

        # کاربر می‌تواند دسترسی داشته باشد
        topic_info = get_topic_by_id(topic_id)
        if not topic_info:
            send_message(chat_id, "❌ موضوع یافت نشد.")
            return

        user_progress = get_user_topic_progress(user_id, topic_id)

        if not user_progress.get("started", False):
            print(f"🎯 کاربر {user_id} برای اولین بار موضوع {topic_id} را شروع می‌کند")
            content = start_topic_for_user(user_id, topic_id)
        else:
            current_day = user_progress.get("current_day", 1)
            print(f"📅 کاربر {user_id} موضوع {topic_id} - روز {current_day}")
            content = load_day_content(topic_id, current_day, user_id)

        if not content:
            send_message(chat_id, "❌ خطا در بارگذاری محتوا.")
            return

        # ثبت دسترسی کاربر
        daily_reset.record_access(user_id, topic_id, content['day_number'])

        is_completed = content["day_number"] in user_progress.get("completed_days", [])

        # ساخت پیام
        message = f"""
{content['topic_emoji'] * 3}
<b>{content['week_title']}</b>
📖 {content.get('author_quote', '')}

<b>{content['topic_name']}</b>
📅 روز {content['day_number']} از ۲۸ • هفته {content['week_number']}
🕕 بازنشانی بعدی: ساعت ۶ صبح

<i>{content['intro']}</i>

──────────────
{content['topic_emoji']} <b>۱۰ شکرگزاری امروز:</b>
"""

        for i, item in enumerate(content['items'][:10], 1):
            message += f"\n{i}. {item}"

        message += "\n──────────────\n"

        if content.get('exercise'):
            message += f"💡 <b>تمرین امروز:</b> {content['exercise']}\n\n"

        if content.get('affirmation'):
            message += f"🌟 <b>تأکید مثبت:</b> <i>{content['affirmation']}</i>\n\n"

        if content.get('reflection'):
            message += f"💭 <b>بازتاب:</b> {content['reflection']}\n\n"

        if is_completed:
            message += "✅ <b>این روز قبلاً تکمیل شده است.</b>"
        else:
            message += "🙏 پس از خواندن، دکمه 'امروز شکرگزار بودم' را فشار دهید."

        inline_keyboard = GraphicsHandler.create_day_inline_keyboard(
            topic_id,
            content['day_number'],
            is_completed
        )
        send_message(chat_id, message, inline_keyboard)

        time.sleep(0.5)
        menu_message = "🔽 <b>منوی دسترسی سریع:</b>"
        markup_keyboard = create_main_menu_keyboard()
        send_message(chat_id, menu_message, markup_keyboard)

    except Exception as e:
        print(f"❌ خطا در handle_category_selection: {e}")
        import traceback
        traceback.print_exc()
        error_msg = "⚠️ خطایی رخ داد. لطفاً دوباره تلاش کنید."
        send_message(chat_id, error_msg)


def handle_complete_day(chat_id, user_id, topic_id, day_number):
    """تکمیل روز - با سیستم ساعت ۶ صبح"""

    if complete_day_for_user(user_id, topic_id, day_number):
        topic_info = get_topic_by_id(topic_id)
        topic_name = topic_info['name'] if topic_info else "این موضوع"
        topic_emoji = topic_info['emoji'] if topic_info else "🎉"

        # دریافت اطلاعات زمان‌بندی
        access_info = daily_reset.get_access_info(user_id, topic_id)
        next_reset_human = access_info.get('next_reset_human', '۶ صبح')

        if day_number < 28:
            message = f"""
{topic_emoji} <b>تبریک! روز {day_number} {topic_name} را کامل کردید!</b>

✅ <b>تمرین امروز ثبت شد</b>
✨ شما یک گام دیگر به سوی تحول زندگی برداشتید

🎯 <b>سیستم روزانه شکرگزاری (ساعت ۶ صبح):</b>
<i>برای بهترین نتیجه، این روند را دنبال کنید:</i>

1️⃣ <b>فردا ساعت {next_reset_human} به ربات مراجعه کنید</b>
2️⃣ موضوع "{topic_name}" را انتخاب کنید  
3️⃣ محتوای روز {day_number + 1} برای شما نمایش داده می‌شود

⏰ <i>این سیستم به شما کمک می‌کند:</i>
• شکرگزاری صبحگاهی را به عادت تبدیل کنید
• روز خود را با انرژی مثبت شروع کنید
• نتایج پایدار و ماندگار بگیرید

🌟 <b>تا فردا صبح، تأثیرات شکرگزاری امروز را در زندگی خود مشاهده کنید...</b>
"""

            keyboard = {
                "inline_keyboard": [
                    [
                        {"text": f"📖 بازخوانی روز {day_number}", "callback_data": f"review_{topic_id}_{day_number}"}
                    ],
                    [
                        {"text": "🎯 انتخاب موضوع دیگر", "callback_data": "categories"},
                        {"text": "📊 پیشرفت من", "callback_data": f"progress_{topic_id}"}
                    ]
                ]
            }

            send_message(chat_id, message, keyboard)

        else:
            message = f"""
🎊 <b>شکوه‌آمیز! دوره ۲۸ روزه {topic_name} کامل شد!</b>

{topic_emoji * 3}

🌟 <b>دستاورد بزرگ شما:</b>
✅ ۲۸ روز تمرین مستمر شکرگزاری
✅ ۲۸۰ مورد شکرگزاری ثبت شده  
✅ ۴ هفته تحول ذهنی
✅ تبدیل شکرگزاری به سبک زندگی

🎯 <b>حالا می‌توانید:</b>

🔄 همین موضوع را از اول شروع کنید
➡️ موضوع جدیدی را انتخاب کنید  
📊 پیشرفت کلی خود را ببینید

💝 <i>"شما تبدیل به آنچه شکرگزارش هستید، می‌شوید" - راندا برن</i>
"""

            keyboard = {
                "inline_keyboard": [
                    [
                        {"text": f"🔄 شروع مجدد {topic_emoji}", "callback_data": f"restart_{topic_id}"},
                        {"text": "🎯 موضوع جدید", "callback_data": "categories"}
                    ],
                    [
                        {"text": "📊 پیشرفت کلی", "callback_data": "progress"}
                    ]
                ]
            }

            send_message(chat_id, message, keyboard)
    else:
        send_message(chat_id, "✅ این روز قبلاً تکمیل شده است.")


# ========== توابع منوی اصلی ==========

def handle_help(chat_id):
    """ارسال راهنمای کامل"""
    help_text = """
📚 <b>راهنمای کامل ربات معجزه شکرگزاری</b>

🎯 <b>سیستم ۲۸ روزه:</b>
• ۸ موضوع اصلی زندگی
• هر موضوع: ۲۸ روز تمرین
• هر روز: ۱۰ مورد شکرگزاری

⏰ <b>سیستم زمان‌بندی:</b>
• بازنشانی روزانه: <b>ساعت ۶ صبح</b>
• هر روز فقط یک بار می‌توانید تمرین کنید
• هدف: ایجاد عادت روزانه

📱 <b>نحوه استفاده:</b>
1️⃣ یک موضوع انتخاب کنید
2️⃣ ۱۰ مورد شکرگزاری را بخوانید
3️⃣ تمرین روزانه را انجام دهید
4️⃣ دکمه "امروز شکرگزار بودم" را فشار دهید
5️⃣ فردا ساعت ۶ صبح برای روز بعدی برگردید

💖 <b>حمایت داوطلبانه:</b>
• ربات کاملاً رایگان است
• حمایت مالی اختیاری است
• هر مبلغی قابل قبول است
• برای تشکر و کمک به توسعه

🌟 <b>نکات مهم:</b>
• با احساس عمیق شکرگزاری کنید
• بر نکات مثبت تمرکز کنید
• شکرگزاری را به سبک زندگی تبدیل کنید

📞 <b>پشتیبانی:</b>
برای سوالات و مشکلات با توسعه‌دهنده تماس بگیرید.
"""

    markup_keyboard = create_main_menu_keyboard()
    send_message(chat_id, help_text, markup_keyboard)


def handle_progress(chat_id, user_id, topic_id=None):
    """نمایش پیشرفت کاربر"""
    topics = get_all_topics()

    if topic_id:
        # پیشرفت یک موضوع خاص
        topic_info = get_topic_by_id(topic_id)
        if not topic_info:
            send_message(chat_id, "❌ موضوع یافت نشد")
            return

        progress = get_user_topic_progress(user_id, topic_id)
        completed = len(progress.get('completed_days', []))
        current_day = progress.get('current_day', 1)
        percentage = (completed / 28) * 100

        text = f"""
{topic_info['emoji']} <b>پیشرفت در {topic_info['name']}</b>

✅ روزهای تکمیل‌شده: {completed} از ۲۸
📅 روز جاری: {current_day}
📈 پیشرفت: {percentage:.1f}%
"""

        # نوار پیشرفت
        progress_bar_length = 10
        filled = int((current_day / 28) * progress_bar_length)
        progress_bar = "█" * filled + "░" * (progress_bar_length - filled)
        text += f"\n{progress_bar}\n"

        if completed == 28:
            text += "\n🎊 <b>تبریک! شما این موضوع را کامل کردید!</b>"
        elif completed >= 20:
            text += "\n🌟 <b>عالی! نزدیک به پایان هستید.</b>"
        elif completed >= 10:
            text += "\n💪 <b>خوب پیش می‌روید! ادامه دهید.</b>"
        elif completed > 0:
            text += "\n🚀 <b>شروع خوبی داشته‌اید!</b>"
        else:
            text += "\n🎯 <b>هنوز شروع نکرده‌اید. همین حالا شروع کنید!</b>"

        # ارسال با Markup Keyboard
        markup_keyboard = create_main_menu_keyboard()
        send_message(chat_id, text, markup_keyboard)

    else:
        # پیشرفت کلی
        text = "<b>📊 پیشرفت کلی شما</b>\n\n"

        total_completed = 0

        for topic in topics:
            progress = get_user_topic_progress(user_id, topic['id'])
            completed = len(progress.get('completed_days', []))
            total_completed += completed

            percentage = (completed / 28) * 100
            progress_bar_length = 5
            filled = int((completed / 28) * progress_bar_length)
            progress_bar = "█" * filled + "░" * (progress_bar_length - filled)

            text += f"{topic['emoji']} {topic['name']}: {progress_bar} {completed}/۲۸\n"

        total_days = len(topics) * 28
        total_percentage = (total_completed / total_days) * 100 if total_days > 0 else 0

        text += f"\n✅ کل روزهای تکمیل‌شده: {total_completed} از {total_days}"
        text += f"\n📈 درصد کلی: {total_percentage:.1f}%"

        if total_percentage > 70:
            text += "\n\n🌟 <b>عالی! شما در مسیر تحول کامل هستید.</b>"
        elif total_percentage > 40:
            text += "\n\n💪 <b>خوب پیش می‌روید! ادامه دهید.</b>"
        elif total_percentage > 0:
            text += "\n\n🚀 <b>شروع خوبی داشته‌اید!</b>"

        # ارسال با Markup Keyboard
        markup_keyboard = create_main_menu_keyboard()
        send_message(chat_id, text, markup_keyboard)


def handle_encourage(chat_id, topic_id):
    """ارسال پیام تشویقی"""
    topic_info = get_topic_by_id(topic_id)

    if topic_info:
        encourage_text = f"""
{topic_info['emoji']} <b>انگیزه برای ادامه {topic_info['name']}</b>

"هر شکرگزاری قدمی است به سوی تحول زندگی.
هر روز که سپاسگزاری می‌کنید،
یک لایه از محدودیت‌ها را می‌کنید."

🌟 تمرین امروز را با عشق انجام دهید
🎯 بر نکات مثبت تمرکز کنید
💖 از قلب خود تشکر کنید

<i>شما در مسیر درستی قرار دارید...</i>
"""
    else:
        encourage_text = """
✨ <b>پیام تشویقی</b>

"شکرگزاری معجزه‌ای است که زندگیتان را متحول می‌کند."

💖 هر روز ۱۰ دقیقه وقت بگذارید
🎯 روی نکات مثبت تمرکز کنید
🌟 معجزه را در زندگی خود ببینید

<i>ادامه دهید... هر روز نزدیک‌تر</i>
"""

    markup_keyboard = create_main_menu_keyboard()
    send_message(chat_id, encourage_text, markup_keyboard)


def handle_contact_developer(chat_id):
    """ارسال اطلاعات تماس با توسعه‌دهنده"""
    contact_text = """
👨‍💻 <b>ارتباط با توسعه‌دهنده</b>


💎 **توسعه‌دهنده:**  
فـــرزاد قــجری  

📞 **تماس مستقیم:**  
۰۹۳۰۲۴۴۶۱۴۱ 

📧 **ایمیل:**  
farzadq.ir@gmail.com 

🆔 **آیدی‌های ارتباطی:**  
**ایتا:** farzadQ_ir@  
**تلگرام:** farzadQ_ir@  
**بله:** farzadQ_ir@  
**روبیکا:** farzadQ_ir@  

---

🎯 **حوزه‌های تخصصی و خدمات:**  
✅ طراحی و ساخت ربات‌های تلگرام و وب‌سایت‌های پویا  
✅ توسعه اپلیکیشن‌های موبایل (Android/iOS) و نرم‌افزارهای دسکتاپ  
✅ برنامه‌نویسی پایتون، فریم‌ورک‌های Django و Flask  
✅ طراحی و توسعه API و سیستم‌های پایگاه‌داده  
✅ مشاوره، پشتیبانی فنی و دوره‌های آموزشی برنامه‌نویسی  

    🌍**www.danekar.ir**
---

✨ *برای شروع پروژه، دریافت مشاوره یا همکاری، از طریق راه‌های فوق در ارتباط باشید.*


"""

    markup_keyboard = create_main_menu_keyboard()
    send_message(chat_id, contact_text, markup_keyboard)


def handle_show_topics(chat_id):
    """نمایش لیست موضوعات"""
    categories_text = "🎯 <b>لطفاً یک موضوع از ۸ حوزه اصلی انتخاب کنید:</b>"
    markup_keyboard = create_categories_keyboard()
    send_message(chat_id, categories_text, markup_keyboard)


def handle_review_day(chat_id, user_id, topic_id, day_number):
    """بازخوانی یک روز تکمیل شده"""
    topic_info = get_topic_by_id(topic_id)

    if not topic_info:
        send_message(chat_id, "❌ موضوع یافت نشد.")
        return

    # بارگذاری محتوای روز
    content = load_day_content(topic_id, day_number, user_id)

    if not content or not content.get("success", False):
        send_message(chat_id, f"❌ خطا در بارگذاری محتوا.")
        return

    message = f"""
📖 <b>بازخوانی روز {day_number}: {content['topic_name']}</b>

🎯 {content['week_title']}
<i>{content['intro']}</i>

──────────────
{content['topic_emoji']} <b>۱۰ شکرگزاری این روز:</b>
"""

    for i, item in enumerate(content['items'][:10], 1):
        message += f"\n{i}. {item}"

    message += "\n──────────────\n"

    if content.get('exercise'):
        message += f"💡 <b>تمرین:</b> {content['exercise']}\n\n"

    if content.get('affirmation'):
        message += f"🌟 <b>تأکید مثبت:</b> <i>{content['affirmation']}</i>\n\n"

    if content.get('reflection'):
        message += f"💭 <b>بازتاب:</b> {content['reflection']}\n\n"

    message += "✅ <b>این روز قبلاً تکمیل شده است.</b>"

    keyboard = {
        "inline_keyboard": [
            [
                {"text": "🔙 بازگشت به موضوع", "callback_data": f"cat_{topic_id}"},
                {"text": "🎯 منوی اصلی", "callback_data": "categories"}
            ]
        ]
    }

    send_message(chat_id, message, keyboard)


def handle_restart_topic(chat_id, user_id, topic_id):
    """شروع مجدد یک موضوع از روز اول"""
    topic_info = get_topic_by_id(topic_id)

    if not topic_info:
        send_message(chat_id, "❌ موضوع یافت نشد.")
        return

    # بازنشانی زمان‌بندی
    daily_reset.reset_user_access(user_id, topic_id)

    # شروع از روز اول
    content = start_topic_for_user(user_id, topic_id)

    message = f"""
🔄 <b>شروع مجدد {topic_info['name']}</b>

{topic_info['emoji'] * 3}

✅ زمان‌بندی شما بازنشانی شد
🎯 حالا می‌توانید از روز ۱ شروع کنید

🌟 <i>این بار با تجربه بیشتر و عمق افزون‌تر...</i>
"""

    keyboard = {
        "inline_keyboard": [
            [
                {"text": f"🚀 شروع روز ۱", "callback_data": f"cat_{topic_id}"}
            ],
            [
                {"text": "⏪ انصراف", "callback_data": "categories"}
            ]
        ]
    }

    send_message(chat_id, message, keyboard)


def handle_message(chat_id, user_id, text, username="", first_name=""):
    """پردازش پیام متنی از کاربر"""
    print(f"📨 {first_name or username}: {text}")

    # حذف فضای خالی اضافه
    text = text.strip()

    if text == "/start":
        handle_start(chat_id, user_id, username, first_name)

    elif text == "/menu" or text == "/topics" or text == "🎯 موضوعات شکرگزاری" or text == "موضوعات":
        handle_show_topics(chat_id)

    elif text == "/help" or text == "❓ راهنما" or text == "راهنما":
        handle_help(chat_id)

    elif text == "/progress" or text == "📊 پیشرفت کلی" or text == "پیشرفت":
        handle_progress(chat_id, user_id)

    elif text == "👨‍💻 ارتباط با من" or text == "ارتباط" or text == "تماس":
        handle_contact_developer(chat_id)

    elif text == "💫 پیام تشویقی":
        handle_encourage(chat_id, 1)

    # پردازش مبلغ دلخواه حمایت
    elif text.isdigit():
        # اگر عدد وارد کرد، آن را به عنوان مبلغ حمایت در نظر بگیر
        amount = int(text)
        if amount >= 1000:  # حداقل 100 تومان (1000 ریال)
            amount_rials = amount
            if amount < 10000:  # اگر کمتر از 1000 تومان وارد کرد، آن را به ریال تبدیل کن
                amount_rials = amount * 10  # تبدیل تومان به ریال

            send_donation_invoice(chat_id, user_id, amount_rials)
        else:
            send_message(chat_id, "⚠️ مبلغ باید حداقل ۱۰۰ تومان باشد.")
    else:
        # تشخیص موضوع از روی متن دکمه
        topics = get_all_topics()
        selected_topic_id = None

        for topic in topics:
            if topic['name'] in text or topic['emoji'] in text:
                selected_topic_id = topic['id']
                break

        if selected_topic_id:
            handle_category_selection(chat_id, user_id, selected_topic_id)
        else:
            # اگر پیام نامشخص است، منوی اصلی را نمایش بده
            help_text = "🤔 <b>لطفاً از دکمه‌های منو استفاده کنید:</b>"
            markup_keyboard = create_main_menu_keyboard()
            send_message(chat_id, help_text, markup_keyboard)


# ========== حلقه اصلی ==========

def start_polling():
    print("=" * 50)
    print("🤖 ربات معجزه شکرگزاری")
    print("📖 بر اساس کتاب راندا برن")
    print("👨‍💻 توسعه‌دهنده: فرزاد قجری")
    print("🎯 ۸ موضوع × ۲۸ روز × ۴ سطح")
    print("⏰ سیستم بازنشانی: ساعت ۶ صبح")
    print("💖 سیستم حمایت: فعال")
    print("=" * 50)

    # تست اتصال
    test_url = f"{BASE_URL}/getMe"
    try:
        response = requests.get(test_url, timeout=10)
        if response.json().get("ok"):
            print("✅ اتصال به API بله برقرار شد")
        else:
            print("❌ خطا در اتصال به بله")
            return
    except:
        print("❌ خطا در اتصال به اینترنت")
        return

    # بررسی provider token
    provider_token = os.getenv('BALE_PROVIDER_TOKEN')
    if provider_token:
        print("✅ سیستم پرداخت فعال است")
    else:
        print("⚠️ سیستم پرداخت غیرفعال (provider_token یافت نشد)")

    print("🚀 ربات در حال اجرا...")
    print("📱 /start را در بله ارسال کنید")

    last_update_id = 0

    try:
        while True:
            try:
                updates = get_updates(last_update_id)

                if updates.get("ok") and updates.get("result"):
                    for update in updates["result"]:
                        last_update_id = update["update_id"]

                        # پردازش successful_payment
                        if "message" in update and "successful_payment" in update["message"]:
                            print(f"💰 پرداخت موفق دریافت شد")
                            handle_successful_payment(update)
                            continue

                        if "message" in update:
                            msg = update["message"]
                            chat_id = msg["chat"]["id"]
                            user_id = str(msg["from"]["id"])
                            text = msg.get("text", "")
                            username = msg["from"].get("username", "")
                            first_name = msg["from"].get("first_name", "")

                            handle_message(chat_id, user_id, text, username, first_name)

                        elif "callback_query" in update:
                            callback = update["callback_query"]
                            callback_id = callback["id"]
                            data = callback.get("data", "")
                            chat_id = callback["message"]["chat"]["id"]
                            user_id = str(callback["from"]["id"])

                            answer_callback(callback_id)
                            print(f"🔄 Callback: {data}")

                            if data == "categories":
                                handle_show_topics(chat_id)

                            elif data.startswith("cat_"):
                                topic_id = int(data.split("_")[1])
                                handle_category_selection(chat_id, user_id, topic_id)

                            elif data.startswith("complete_"):
                                parts = data.split("_")
                                topic_id = int(parts[1])
                                day_number = int(parts[2])
                                handle_complete_day(chat_id, user_id, topic_id, day_number)

                            elif data.startswith("review_"):
                                parts = data.split("_")
                                topic_id = int(parts[1])
                                day_number = int(parts[2])
                                handle_review_day(chat_id, user_id, topic_id, day_number)

                            elif data.startswith("restart_"):
                                topic_id = int(data.split("_")[1])
                                handle_restart_topic(chat_id, user_id, topic_id)

                            elif data == "progress":
                                handle_progress(chat_id, user_id)

                            elif data.startswith("progress_"):
                                topic_id = int(data.split("_")[1])
                                handle_progress(chat_id, user_id, topic_id)

                            elif data == "help" or data == "help_beautiful":
                                handle_help(chat_id)

                            elif data.startswith("encourage_"):
                                topic_id = int(data.split("_")[1])
                                handle_encourage(chat_id, topic_id)

                            elif data == "contact_developer":
                                handle_contact_developer(chat_id)

                            # اضافه کردن handler برای حمایت
                            elif data == "support_options":
                                handle_support_options(chat_id, user_id)

                            elif data == "start_using":
                                categories_text = "🎯 <b>لطفاً یک موضوع از ۸ حوزه اصلی انتخاب کنید:</b>"
                                markup_keyboard = create_categories_keyboard()
                                send_message(chat_id, categories_text, markup_keyboard)

                            elif data == "support_back":
                                # بازگشت به صفحه شروع
                                start_text = """
🎯 <b>برای شروع کار با ربات، یکی از گزینه‌های زیر را انتخاب کنید:</b>

• <b>استفاده رایگان:</b> تمام محتوای ربات به صورت کاملاً رایگان در دسترس شماست
• <b>حمایت داوطلبانه:</b> اگر از ربات راضی هستید و می‌خواهید از توسعه‌دهنده حمایت کنید

💝 <i>ربات به صورت کاملاً رایگان ارائه می‌شود. حمایت شما اختیاری و داوطلبانه است.</i>
"""
                                start_keyboard = create_start_keyboard()
                                send_message(chat_id, start_text, start_keyboard)

                            elif data == "support_custom":
                                # درخواست مبلغ دلخواه
                                message = """
💰 <b>مبلغ دلخواه برای حمایت</b>

لطفاً مبلغ مورد نظر خود را به <b>تومان</b> وارد کنید:

مثال:
• برای ۵۰,۰۰۰ تومان: <code>50000</code>
• برای ۱۵,۰۰۰ تومان: <code>15000</code>
• برای ۱,۰۰۰ تومان: <code>1000</code>

💖 <i>هر مبلغی که مایل باشید قابل قبول است.</i>
"""
                                send_message(chat_id, message)

                            elif data.startswith("support_"):
                                # پردازش مبلغ‌های از پیش تعیین شده
                                try:
                                    amount_str = data.split("_")[1]
                                    amount = int(amount_str)  # مبلغ به تومان
                                    amount_rials = amount * 10  # تبدیل به ریال
                                    send_donation_invoice(chat_id, user_id, amount_rials)
                                except:
                                    send_message(chat_id, "⚠️ خطا در پردازش مبلغ.")

                time.sleep(1)

            except Exception as e:
                print(f"⚠️ خطا در حلقه اصلی: {e}")
                import traceback
                traceback.print_exc()
                time.sleep(5)

    except KeyboardInterrupt:
        print("\n👋 ربات متوقف شد")
    except Exception as e:
        print(f"\n❌ خطای بحرانی: {e}")


if __name__ == "__main__":
    start_polling()