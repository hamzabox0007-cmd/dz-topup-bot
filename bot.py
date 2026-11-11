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

CCP_INFO = "📌 **رقم حساب CCP الخاص بك (لاستقبال الأموال الحقيقية):**\n`00799999001922271613`\n👤 **الاسم:** خدمة الوساطة الرقمية"
BINANCE_INFO = "📌 **محفظة بينانس (USDT):**\n`TM72iNjNBDRvUE46KCrK8z1d2PSeaWrVGT`"
SUPPORT_CONTACT = "💬 **للدعم والإدارة:** @hamzabox007-cmd"

# خادم الويب لإبقاء البوت حياً 24/7 على Render
app = Flask('')

@app.route('/')
def home():
    return "Al-Annabi Internal Ad Network is active 24/7!"

def run_web():
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 8080)))

# دالة لجلب بيانات المستخدم ومحفظته اليومية
def get_user(user_id):
    today = datetime.now().strftime("%Y-%m-%d")
    if user_id not in user_data:
        user_data[user_id] = {
            "balance": 0.0,       # الرصيد المالي بالدج
            "points": 0.0,        # النقاط المتراكمة
            "ads_watched": 0,     # عدد الإعلانات المشاهدة اليوم
            "last_date": today    # لتصفير العداد يومياً
        }
    
    if user_data[user_id]["last_date"] != today:
        user_data[user_id]["ads_watched"] = 0
        user_data[user_id]["last_date"] = today
        
    return user_data[user_id]

# القائمة الرئيسية والترحيب
@bot.message_handler(commands=['start'])
def send_welcome(message):
    user = message.from_user
    u = get_user(user.id)
    
    markup = telebot.types.InlineKeyboardMarkup(row_width=2)
    btn_wallet = telebot.types.InlineKeyboardButton(f"👛 محفظتي ({u['balance']} دج)", callback_data='wallet')
    btn_earn = telebot.types.InlineKeyboardButton(f"📺 إعلانات شبكة العنابي ({u['ads_watched']}/10)", callback_data='earn_ads')
    btn_convert = telebot.types.InlineKeyboardButton("🔄 تحويل النقاط لرصيد", callback_data='convert_points')
    btn_games = telebot.types.InlineKeyboardButton("🎮 شحن Free Fire", callback_data='games')
    btn_deposit = telebot.types.InlineKeyboardButton("💳 معلومات الدفع (CCP)", callback_data='deposit')
    btn_support = telebot.types.InlineKeyboardButton("📞 الدعم الفني", callback_data='support')
    
    markup.add(btn_wallet, btn_earn, btn_convert, btn_games, btn_deposit, btn_support)
    
    welcome_text = (
        f"🔥 **أهلاً بك يا {user.first_name} في منصة العنابي للوساطة الرقمية** 🚀\n\n"
        "💎 *تفاعل مع شبكة إعلانات العنابي الداخلية يومياً، اجمع النقاط، حولها إلى رصيد مجاني، وشحن ألعابك بكل أمان!*\n\n"
        "👇 **اختر ما تحتاجه من القائمة أدناه:**"
    )
    bot.send_message(message.chat.id, welcome_text, reply_markup=markup, parse_mode="Markdown")

# إدارة الأزرار التفاعلية بدقة
@bot.callback_query_handler(func=lambda call: True)
def callback_query(call):
    user_id = call.from_user.id
    u = get_user(user_id)
    
    if call.data == 'wallet':
        text = (
            f"👛 **محفظتك الشخصية الحالية:**\n\n"
            f"💰 **رصيدك المالي:** `{u['balance']} دج`\n"
            f"⭐ **نقاطك المجمعة:** `{u['points']} نقطة`\n\n"
            f"💡 *كل 500 نقطة يمكنك تحويلها إلى 100 دج رصيد حقيقي في محفظتك!*"
        )
        markup = telebot.types.InlineKeyboardMarkup()
        markup.add(telebot.types.InlineKeyboardButton("🏠 القائمة الرئيسية", callback_data='main_menu'))
        bot.answer_callback_query(call.id)
        bot.send_message(call.message.chat.id, text, reply_markup=markup, parse_mode="Markdown")
        
    elif call.data == 'earn_ads':
        remaining = 10 - u["ads_watched"]
        text = (
            f"📺 **قسم إعلانات شبكة العنابي الداخلية:**\n\n"
            f"• الإعلانات المشاهدة اليوم: `{u['ads_watched']} / 10`\n"
            f"• المتبقي لك اليوم: `{remaining} إعلانات`\n"
            f"• الربح لكل إعلان: `50 نقطة`\n\n"
            f"📢 **الإعلان الترويجي النشط حالياً:**\n"
            f"━━━━━━━━━━━━━━━━━━━━━\n"
            f"🌟 *عرض خاص من العنابي: اشحن جواهر Free Fire بأسرع وأرخص الأسعار في الجزائر عبر شبكتنا المعتمدة! تابعه الآن واكسب نقاطك.*\n"
            f"━━━━━━━━━━━━━━━━━━━━━\n\n"
            f"👇 اقرأ الإعلان ثم اضغط زر التأكيد لاكتساب نقاطك فوراً:"
        )
        markup = telebot.types.InlineKeyboardMarkup(row_width=1)
        if remaining > 0:
            markup.add(telebot.types.InlineKeyboardButton("✅ تأكيد قراءة الإعلان واكتساب 50 نقطة", callback_data='confirm_ad'))
        else:
            markup.add(telebot.types.InlineKeyboardButton("⏳ لقد استهلكت الـ 10 إعلانات اليومية", callback_data='limit_reached'))
            
        markup.add(telebot.types.InlineKeyboardButton("🏠 القائمة الرئيسية", callback_data='main_menu'))
        bot.answer_callback_query(call.id)
        bot.send_message(call.message.chat.id, text, reply_markup=markup, parse_mode="Markdown")
        
    elif call.data == 'confirm_ad':
        if u["ads_watched"] < 10:
            u["ads_watched"] += 1
            u["points"] += 50
            remaining = 10 - u["ads_watched"]
            
            bot.answer_callback_query(call.id, "🎉 كفو! تمت إضافة 50 نقطة إلى محفظتك بنجاح.", show_alert=True)
            
            text = (
                f"✅ **تم تأكيد الإعلان بنجاح!**\n"
                f"⭐ نقاطك الحالية: `{u['points']} نقطة`\n"
                f"📊 المتبقي لك اليوم: `{remaining} إعلانات`"
            )
            markup = telebot.types.InlineKeyboardMarkup(row_width=1)
            if remaining > 0:
                markup.add(telebot.types.InlineKeyboardButton("📺 مشاهدة إعلان آخر (+50 نقطة)", callback_data='earn_ads'))
            markup.add(telebot.types.InlineKeyboardButton("🏠 القائمة الرئيسية", callback_data='main_menu'))
            bot.send_message(call.message.chat.id, text, reply_markup=markup, parse_mode="Markdown")
        else:
            bot.answer_callback_query(call.id, "⚠️ لقد وصلت لحد الإعلانات الأقصى اليوم (10/10). عُد غداً!", show_alert=True)
            
    elif call.data == 'limit_reached':
        bot.answer_callback_query(call.id, "⚠️ أنهيت إعلانات اليوم. انتظر حتى الغد!", show_alert=True)
        
    elif call.data == 'convert_points':
        if u["points"] >= 500:
            u["points"] -= 500
            u["balance"] += 100.0
            text = (
                f"🎉 **تم التحويل بنجاح تام!**\n"
                f"🔄 خصمنا `500 نقطة` وأضفنا `100 دج` إلى رصيدك المالي.\n"
                f"💰 رصيدك المالي الجديد: `{u['balance']} دج`"
            )
            bot.answer_callback_query(call.id, "تم التحويل إلى رصيد بنجاح! 🚀")
        else:
            needed = 500 - u["points"]
            text = (
                f"⚠️ **عذراً، نقاطك غير كافية للتحويل.**\n"
                f"رصيدك الحالي: `{u['points']} نقطة`\n"
                f"تحتاج إلى `500 نقطة` على الأقل (متبقي لك {needed} نقطة)."
            )
            bot.answer_callback_query(call.id, "النقاط غير كافية", show_alert=True)
        
        markup = telebot.types.InlineKeyboardMarkup()
        markup.add(telebot.types.InlineKeyboardButton("🏠 القائمة الرئيسية", callback_data='main_menu'))
        bot.send_message(call.message.chat.id, text, reply_markup=markup, parse_mode="Markdown")
        
    elif call.data == 'games':
        text = (
            "🎮 **قسم شحن Free Fire:**\n\n"
            "• 100 جوهرة\n"
            "• 310 جوهرة (الأكثر طلباً 🔥)\n\n"
            "🛒 للدفع من رصيد محفظتك المباشر أو عبر CCP، تواصل معنا."
        )
        markup = telebot.types.InlineKeyboardMarkup()
        markup.add(telebot.types.InlineKeyboardButton("🏠 القائمة الرئيسية", callback_data='main_menu'))
        bot.answer_callback_query(call.id)
        bot.send_message(call.message.chat.id, text, reply_markup=markup, parse_mode="Markdown")
        
    elif call.data == 'deposit':
        text = f"💳 **حسابات الاستقبال لاستقبال الأموال الحقيقية:**\n\n{CCP_INFO}\n\n{BINANCE_INFO}\n\n⚠️ *بعد التحويل، أرسل صورة الوصل هنا في البوت ليتم إرسال إشعار فوري لإدارة العنابي!*"
        markup = telebot.types.InlineKeyboardMarkup()
        markup.add(telebot.types.InlineKeyboardButton("🏠 القائمة الرئيسية", callback_data='main_menu'))
        bot.answer_callback_query(call.id)
        bot.send_message(call.message.chat.id, text, reply_markup=markup, parse_mode="Markdown")
        
    elif call.data == 'support':
        text = f"📞 **الدعم الفني:**\n{SUPPORT_CONTACT}"
        markup = telebot.types.InlineKeyboardMarkup()
        markup.add(telebot.types.InlineKeyboardButton("🏠 القائمة الرئيسية", callback_data='main_menu'))
        bot.answer_callback_query(call.id)
        bot.send_message(call.message.chat.id, text, reply_markup=markup, parse_mode="Markdown")
        
    elif call.data == 'main_menu':
        send_welcome(call.message)

# استقبال صور إيصالات الدفع الحقيقي وتنبيهك أنت شخصياً لاستقبال الأموال
@bot.message_handler(content_types=['photo'])
def handle_receipt(message):
    user = message.from_user
    username = f"@{user.username}" if user.username else "بدون معرف"
    
    bot.reply_to(message, "📥 **تم استلام صورة الوصل بنجاح!**\n⏳ *تم إرسال الإشعار فوراً إلى هاتف الإدارة (العنابي) لمراجعة الحساب وتنفيذ طلبك.*", parse_mode="Markdown")
    
    if ADMIN_ID:
        admin_alert = (
            f"💰 **تنبيه مالي هام: وصل دفع جديد!**\n\n"
            f"👤 **الزبون:** {user.first_name} ({username})\n"
            f"🆔 **الآيدي:** `{user.id}`\n\n"
            f"🎯 *تفقد حسابك في CCP أو بينانس لتأكيد استلام الأموال وإضافة الرصيد للزبون!*"
        )
        bot.send_photo(ADMIN_ID, message.photo[-1].file_id, caption=admin_alert, parse_mode="Markdown")

# تشغيل البوت سحابياً 24/7
if __name__ == '__main__':
    t = Thread(target=run_web)
    t.start()
    print("Al-Annabi Ad Network Bot is running smoothly 24/7...")
    bot.infinity_polling()
