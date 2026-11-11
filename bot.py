import os
import telebot
from flask import Flask
from threading import Thread

# توكن بوت التيليجرام الخاص بك
TOKEN = '9181651284:AAFhCeulxRzQYuJ_VmLSy8E054kVZPNXkF8'
bot = telebot.TeleBot(TOKEN)

# معلومات الدفع والاتصال المعتمدة
CCP_INFO = "📌 **رقم حساب CCP / RIP:**\n`00799999001922271613`\n👤 **الاسم:** خدمة الوساطة الرقمية\n\n⚠️ *ملاحظة:* بعد التحويل، أرسل صورة الوصل هنا مع تحديد طلبك ليتم التنفيذ فوراَ."
BINANCE_INFO = "📌 **محفظة بينانس (USDT - TRC20):**\n`TM72iNjNBDRvUE46KCrK8z1d2PSeaWrVGT`\n\n⚠️ *ملاحظة:* أرسل لقطة شاشة للتحويل مع معرف الصفقة (TxID)."
SUPPORT_CONTACT = "💬 **للتواصل المباشر والطلب السريع:**\nرئيس الخدمة: @hamzabox007-cmd"

# إنشاء خفر ويب وهمي لإرضاء متطلبات Render للبورتات
app = Flask('')

@app.route('/')
def home():
    return "Bot is active and running 24/7!"

def run_web():
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 8080)))

# رسالة الترحيب الترويجية الجذابة
@bot.message_handler(commands=['start'])
def send_welcome(message):
    markup = telebot.types.InlineKeyboardMarkup(row_width=2)
    
    btn_games = telebot.types.InlineKeyboardButton("🎮 شحن الألعاب (Free Fire)", callback_data='games')
    btn_usdt = telebot.types.InlineKeyboardButton("💱 صرافة USDT بأفضل سعر", callback_data='usdt')
    btn_subs = telebot.types.InlineKeyboardButton("📺 اشتراكات رقمية (Netflix / IPTV)", callback_data='subs')
    btn_pay = telebot.types.InlineKeyboardButton("💳 طرق الدفع (CCP & Binance)", callback_data='payment')
    btn_support = telebot.types.InlineKeyboardButton("📞 الدعم الفني والاتصال", callback_data='support')
    
    markup.add(btn_games, btn_usdt, btn_subs, btn_pay, btn_support)
    
    welcome_text = (
        "🔥 **أهلاً بك في منصة العنابي للخدمات الرقمية والوساطة 24/7** 🚀\n\n"
        "✨ **لماذا تختارنا؟**\n"
        "⚡ سرعة في التنفيذ وأمان تام.\n"
        "💎 أفضل الأسعار في السوق الجزائري.\n"
        "🛡️ ضمان شامل على جميع الخدمات والاشتراكات.\n\n"
        "👇 **اختر الخدمة التي تناسب احتياجك وابدأ الآن:**"
    )
    bot.send_message(message.chat.id, welcome_text, reply_markup=markup, parse_mode="Markdown")

# التعامل مع الأزرار التفاعلية
@bot.callback_query_handler(func=lambda call: True)
def callback_query(call):
    if call.data == 'games':
        text = (
            "🎮 **قسم شحن الألعاب (Free Fire & فري فاير):**\n\n"
            "💎 **العروض المتوفرة حالياً:**\n"
            "• 100 جوهرة ⟵ السعر المناسب\n"
            "• 310 جوهرة ⟵ الأكثر طلباً 🔥\n"
            "• 520 جوهرة ⟵ عرض مميز\n\n"
            "🛒 **طريقة الطلب:**\n"
            "1. قم بتحويل المبلغ عبر CCP أو بينانس.\n"
            "2. أرسل إيصال الدفع + الـ (ID) الخاص بك هنا في البوت.\n"
            "3. استلم جواهرك في دقائق معدودة!"
        )
        bot.answer_callback_query(call.id)
        bot.send_message(call.message.chat.id, text, parse_mode="Markdown")
        
    elif call.data == 'usdt':
        text = (
            "💱 **قسم صرافة USDT الرقمية:**\n\n"
            "📈 شراء وبيع العملات الرقمية بكل أمان وثقة.\n"
            "• متوفر الدفع بالـ CCP / BaridiMob.\n"
            "• أسعار تنافسية ومحدثة باستمرار.\n\n"
            "💬 للاتفاق على الكمية والسعر، تواصل مباشرة مع الإدارة."
        )
        bot.answer_callback_query(call.id)
        bot.send_message(call.message.chat.id, text, parse_mode="Markdown")
        
    elif call.data == 'subs':
        text = (
            "📺 **قسم الاشتراكات الرقمية والترفيهية:**\n\n"
            "🍿 **Netflix:** حسابات رسمية، ضمان كامل طيلة المدة.\n"
            "📡 **IPTV:** اشتراكات سنوية لأقوى القنوات والباقات بجودة عالية ودون تقطيع.\n\n"
            "💳 اختر خدمتك المفضلة، أرسل إيصال الدفع، واستلم معلومات الدخول فوراً!"
        )
        bot.answer_callback_query(call.id, "جاري فتح قسم الاشتراكات...")
        bot.send_message(call.message.chat.id, text, parse_mode="Markdown")
        
    elif call.data == 'payment':
        text = f"💳 **بيانات الدفع الرسمية المعتمدة:**\n\n{CCP_INFO}\n\n━━━━━━━━━━━━━━━\n\n{BINANCE_INFO}"
        bot.answer_callback_query(call.id)
        bot.send_message(call.message.chat.id, text, parse_mode="Markdown")
        
    elif call.data == 'support':
        text = f"📞 **مركز الدعم والخدمة:**\n\n{SUPPORT_CONTACT}\n\nنحن في خدمتك على مدار الساعة للإجابة عن استفساراتكم وتنفيذ طلباتكم."
        bot.answer_callback_query(call.id)
        bot.send_message(call.message.chat.id, text, parse_mode="Markdown")

# تشغيل الخادم الوهمي والبوت معاً
if __name__ == '__main__':
    # تشغيل سيرفر الويب في خلفية الكود لفتح البورت المطلوب
    t = Thread(target=run_web)
    t.start()
    
    print("Bot and web server are running smoothly...")
    bot.infinity_polling()
