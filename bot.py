import os
import telebot
from flask import Flask
from threading import Thread
from datetime import datetime

# توكن بوت التيليجرام الخاص بك
TOKEN = '9181651284:AAFhCeulxRzQYuJ_VmLSy8E054kVZPNXkF8'
bot = telebot.TeleBot(TOKEN)

# معرف الإدارة الخاص بك لاستقبال إشعارات الأموال الحقيقية
ADMIN_ID = "8528044992" 

# قاعدة بيانات مؤقتة لتخزين بيانات ومحافظ الزبائن
user_data = {}

CCP_INFO = "📌 **رقم حساب CCP (لاستقبال الأموال الحقيقية):**\n`00799999001922271613`\n👤 **الاسم:** خدمة الوساطة الرقمية"
BINANCE_INFO = "📌 **محفظة بينانس (USDT):**\n`TM72iNjNBDRvUE46KCrK8z1d2PSeaWrVGT`"
SUPPORT_CONTACT = "💬 **للدعم والإدارة:** @hamzabox007-cmd"

# خادم الويب لإبقاء البوت حياً 24/7 على Render
app = Flask('')

@app.route('/')
def home():
    return "Professional Digital Brokerage Bot is active 24/7!"

def run_web():
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 8080)))

# دالة لجلب بيانات المستخدم ومحفظته اليومية
def get_user(user_id):
    today = datetime.now().strftime("%Y-%m-%d")
    if user_id not in user_data:
        user_data[user_id] = {
            "balance": 0.0,       # الرصيد المالي بالدج
            "mining_coins": 0.0,  # رصيد العملة الرقمية المعدنة
            "referrals": 0,       # عدد الأصدقاء المدعوين
            "last_date": today    # لتصفير العداد يومياً
        }
    return user_data[user_id]

# القائمة الرئيسية والترحيب مع دعم نظام الإحالة (Referred by)
@bot.message_handler(commands=['start'])
def send_welcome(message):
    user = message.from_user
    u = get_user(user.id)
    
    # فحص نظام الدعوات إذا دخل عبر رابط صديقه
    args = message.text.split()
    if len(args) > 1 and args[1].startswith("ref_"):
        try:
            referrer_id = int(args[1].replace("ref_", ""))
            if referrer_id != user.id and referrer_id in user_data:
                # إعطاء مكافأة لمن دعا صديقه إن لم يتم احتسابه مسبقاً
                user_data[referrer_id]["mining_coins"] += 20.0
                bot.send_message(referrer_id, f"🎉 **مرحباً! انضم صديق جديد عبر رابط الدعوة الخاص بك.**\n➕ تمت إضافة `20 عملة معدنية` إلى رصيدك التعديني!", parse_mode="Markdown")
        except:
            pass

    markup = telebot.types.InlineKeyboardMarkup(row_width=2)
    btn_wallet = telebot.types.InlineKeyboardButton(f"👛 المحفظة ({u['balance']} دج)", callback_data='wallet')
    btn_mining = telebot.types.InlineKeyboardButton(f"⛏️ تعدين العملة الرقمية", callback_data='mining_menu')
    btn_ref = telebot.types.InlineKeyboardButton(f"👥 ادعُ أصدقائك واربح", callback_data='referral_menu')
    btn_convert = telebot.types.InlineKeyboardButton("🔄 تحويل العملة لنقود حقيقية", callback_data='convert_coins')
    btn_games = telebot.types.InlineKeyboardButton("🎮 شحن Free Fire", callback_data='games')
    btn_deposit = telebot.types.InlineKeyboardButton("💳 معلومات الدفع (CCP)", callback_data='deposit')
    btn_support = telebot.types.InlineKeyboardButton("📞 الدعم الفني", callback_data='support')
    
    markup.add(btn_wallet, btn_mining, btn_ref, btn_convert, btn_games, btn_deposit, btn_support)
    
    welcome_text = (
        f"🔥 **أهلاً بك يا {user.first_name} في المنصة الرقمية المعتمدة للوساطة والشحن** 🚀\n\n"
        "⛏️ *ابدأ الآن في تعدين العملة الرقمية مجاناً، ادعُ أصدقائك لزيادة أرباحك، وحولها مباشرة إلى أموال حقيقية لشحن ألعابك ودفعاتك!*\n\n"
        "👇 **اختر ما تحتاجه من القائمة أدناه:**"
    )
    bot.send_message(message.chat.id, welcome_text, reply_markup=markup, parse_mode="Markdown")

# إدارة الأزرار التفاعلية بدقة واحترافية
@bot.callback_query_handler(func=lambda call: True)
def callback_query(call):
    user_id = call.from_user.id
    u = get_user(user_id)
    
    if call.data == 'wallet':
        text = (
            f"👛 **محفظتك الشخصية:**\n\n"
            f"💰 **الرصيد النقدي القابل للشحن:** `{u['balance']} دج`\n"
            f"🪙 **رصيد عملة التعدين:** `{u['mining_coins']} عملة`\n\n"
            f"💡 *كل 100 عملة معدنة = 50 دج رصيد نقدي في محفظتك!*"
        )
        markup = telebot.types.InlineKeyboardMarkup()
        markup.add(telebot.types.InlineKeyboardButton("🏠 القائمة الرئيسية", callback_data='main_menu'))
        bot.answer_callback_query(call.id)
        bot.send_message(call.message.chat.id, text, reply_markup=markup, parse_mode="Markdown")
        
    elif call.data == 'mining_menu':
        text = (
            f"⛏️ **قسم تعدين العملة الرقمية للمنصة:**\n\n"
            f"• رصيدك الحالي من العملة: `{u['mining_coins']} عملة`\n"
            f"• أرباح التعدين لكل نقرة: `10 عملات رقمية`\n\n"
            f"👇 اضغط على زر 'بدء دورة التعدين' لجمع العملات الآن:"
        )
        markup = telebot.types.InlineKeyboardMarkup(row_width=1)
        markup.add(telebot.types.InlineKeyboardButton("⛏️ بدء دورة تعدين جديدة (+10 عملات)", callback_data='do_mining'))
        markup.add(telebot.types.InlineKeyboardButton("🏠 القائمة الرئيسية", callback_data='main_menu'))
        bot.answer_callback_query(call.id)
        bot.send_message(call.message.chat.id, text, reply_markup=markup, parse_mode="Markdown")
        
    elif call.data == 'do_mining':
        u["mining_coins"] += 10.0
        bot.answer_callback_query(call.id, "🎉 ممتاز! تمت إضافة 10 عملات معدنية لمحفظتك بنجاح.", show_alert=True)
        
        text = (
            f"✅ **تمت عملية التعدين بنجاح!**\n"
            f"🪙 رصيدك التعديني الحالي: `{u['mining_coins']} عملة`\n\n"
            f"استمر في التعدين أو ادعُ أصدقائك لتسريع أرباحك!"
        )
        markup = telebot.types.InlineKeyboardMarkup(row_width=1)
        markup.add(telebot.types.InlineKeyboardButton("⛏️ تعدين مرة أخرى", callback_data='do_mining'))
        markup.add(telebot.types.InlineKeyboardButton("🏠 القائمة الرئيسية", callback_data='main_menu'))
        bot.send_message(call.message.chat.id, text, reply_markup=markup, parse_mode="Markdown")
        
    elif call.data == 'referral_menu':
        ref_link = f"https://t.me/dz_topup2026_bot?start=ref_{user_id}"
        text = (
            f"👥 **برنامج دعوة الأصدقاء (Affiliate):**\n\n"
            f"شارك رابط الدعوة الخاص بك مع أصدقائك وفي المجموعات:\n"
            f"`{ref_link}`\n\n"
            f"🎁 **المكافأة:** كل صديق يدخل من طرفك يمنحك `20 عملة معدنية` فورية في رصيد التعدين الخاص بك!"
        )
        markup = telebot.types.InlineKeyboardMarkup()
        markup.add(telebot.types.InlineKeyboardButton("🏠 القائمة الرئيسية", callback_data='main_menu'))
        bot.answer_callback_query(call.id)
        bot.send_message(call.message.chat.id, text, reply_markup=markup, parse_mode="Markdown")
        
    elif call.data == 'convert_coins':
        if u["mining_coins"] >= 100:
            # كل 100 عملة تتحول إلى 50 دج
            u["mining_coins"] -= 100.0
            u["balance"] += 50.0
            text = (
                f"🎉 **تم التحويل بنجاح تام!**\n"
                f"🔄 خصمنا `100 عملة` وأضفنا `50 دج` إلى رصيدك النقدي.\n"
                f"💰 رصيدك النقدي الجديد: `{u['balance']} دج`"
            )
            bot.answer_callback_query(call.id, "تم التحويل إلى نقود بنجاح! 🚀")
        else:
            needed = 100 - u["mining_coins"]
            text = (
                f"⚠️ **عذراً، رصيدك المعدن غير كافٍ للتحويل.**\n"
                f"رصيدك الحالي: `{u['mining_coins']} عملة`\n"
                f"تحتاج إلى `100 عملة` على الأقل للتحويل (متبقي لك {needed} عملة)."
            )
            bot.answer_callback_query(call.id, "الرصيد غير كافٍ", show_alert=True)
        
        markup = telebot.types.InlineKeyboardMarkup()
        markup.add(telebot.types.InlineKeyboardButton("🏠 القائمة الرئيسية", callback_data='main_menu'))
        bot.send_message(call.message.chat.id, text, reply_markup=markup, parse_mode="Markdown")
        
    elif call.data == 'games':
        text = (
            "🎮 **قسم شحن Free Fire:**\n\n"
            "• 100 جوهرة\n"
            "• 310 جوهرة (الأكثر طلباً 🔥)\n\n"
            "🛒 يمكنك الشحن مباشرة باستخدام رصيد محفظتك النقدي أو عبر الدفع المباشر."
        )
        markup = telebot.types.InlineKeyboardMarkup()
        markup.add(telebot.types.InlineKeyboardButton("🏠 القائمة الرئيسية", callback_data='main_menu'))
        bot.answer_callback_query(call.id)
        bot.send_message(call.message.chat.id, text, reply_markup=markup, parse_mode="Markdown")
        
    elif call.data == 'deposit':
        text = f"💳 **حسابات الاستقبال للإدارة:**\n\n{CCP_INFO}\n\n{BINANCE_INFO}\n\n⚠️ *بعد التحويل، أرسل صورة الوصل هنا ليصل الإشعار فوراً للإدارة وتنفيذ طلبك!*"
        markup = telebot.types.InlineKeyboardMarkup()
        markup.add(telebot.types.InlineKeyboardButton("🏠 القائمة الرئيسية", callback_data='main_menu'))
        bot.answer_callback_query(call.id)
        bot.send_message(call.message.chat.id, text, reply_markup=markup, parse_mode="Markdown")
        
    elif call.data == 'support':
        text = f"📞 **الدعم الفني والخدمات:**\n{SUPPORT_CONTACT}"
        markup = telebot.types.InlineKeyboardMarkup()
        markup.add(telebot.types.InlineKeyboardButton("🏠 القائمة الرئيسية", callback_data='main_menu'))
        bot.answer_callback_query(call.id)
        bot.send_message(call.message.chat.id, text, reply_markup=markup, parse_mode="Markdown")
        
    elif call.data == 'main_menu':
        send_welcome(call.message)

# استقبال صور إيصالات الدفع الحقيقي وتنبيهك أنت شخصياً لاستلام الأموال
@bot.message_handler(content_types=['photo'])
def handle_receipt(message):
    user = message.from_user
    username = f"@{user.username}" if user.username else "بدون معرف"
    
    bot.reply_to(message, "📥 **تم استلام صورة الوصل بنجاح!**\n⏳ *تم إرسال الإشعار فوراً إلى إدارة المنصة لمراجعة الحساب وتنفيذ الطلب.*", parse_mode="Markdown")
    
    if ADMIN_ID:
        admin_alert = (
            f"💰 **تنبيه مالي جديد: طلب شحن وإيصال دفع!**\n\n"
            f"👤 **الزبون:** {user.first_name} ({username})\n"
            f"🆔 **الآيدي:** `{user.id}`\n\n"
            f"🎯 *تفقد حسابك في CCP أو بينانس لتأكيد استلام الأموال وتنفيذ الطلب للزبون!*"
        )
        bot.send_photo(ADMIN_ID, message.photo[-1].file_id, caption=admin_alert, parse_mode="Markdown")

# تشغيل البوت سحابياً 24/7
if __name__ == '__main__':
    t = Thread(target=run_web)
    t.start()
    print("Professional Digital Brokerage Bot is running smoothly 24/7...")
    bot.infinity_polling()
