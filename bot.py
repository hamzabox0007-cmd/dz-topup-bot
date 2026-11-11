import os
import telebot
from flask import Flask
from threading import Thread

# توكن بوت التيليجرام الخاص بك
TOKEN = '9181651284:AAFhCeulxRzQYuJ_VmLSy8E054kVZPNXkF8'
bot = telebot.TeleBot(TOKEN)

# معرف الإدارة الخاص بك (تستطيع استقبال إشعارات الطلبات هنا إن أردت لاحقاً)
ADMIN_ID = "000000000"  # ضع آيدي الخاص بك هنا إن أردت

CCP_INFO = "📌 **رقم حساب CCP / RIP:**\n`00799999001922271613`\n👤 **الاسم:** خدمة الوساطة الرقمية\n\n⚠️ *ملاحظة:* بعد التحويل، أرسل صورة الوصل هنا مع تحديد طلبك ليتم التنفيذ فوراً."
BINANCE_INFO = "📌 **محفظة بينانس (USDT - TRC20):**\n`TM72iNjNBDRvUE46KCrK8z1d2PSeaWrVGT`\n\n⚠️ *ملاحظة:* أرسل لقطة شاشة للتحويل مع معرف الصفقة (TxID)."
SUPPORT_CONTACT = "💬 **للتواصل المباشر والطلب السريع:**\nرئيس الخدمة: @hamzabox007-cmd"

# إنشاء خادم ويب محلي لإبقاء البوت حياً على Render
app = Flask('')

@app.route('/')
def home():
    return "Bot is active, autonomous and running 24/7!"

def run_web():
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 8080)))

# رسالة الترحيب الترويجية الذاتية
@bot.message_handler(commands=['start'])
def send_welcome(message):
    user_name = message.from_user.first_name or "عزيزنا العميل"
    markup = telebot.types.InlineKeyboardMarkup(row_width=2)
    
    btn_games = telebot.types.InlineKeyboardButton("🎮 شحن الألعاب (Free Fire)", callback_data='games')
    btn_usdt = telebot.types.InlineKeyboardButton("💱 صرافة USDT بأفضل سعر", callback_data='usdt')
    btn_subs = telebot.types.InlineKeyboardButton("📺 اشتراكات رقمية (Netflix / IPTV)", callback_data='subs')
    btn_pay = telebot.types.InlineKeyboardButton("💳 طرق الدفع (CCP & Binance)", callback_data='payment')
    btn_support = telebot.types.InlineKeyboardButton("📞 الدعم الفني والاتصال", callback_data='support')
    
    markup.add(btn_games, btn_usdt, btn_subs, btn_pay, btn_support)
    
    welcome_text = (
        f"🔥 **أهلاً بك يا {user_name} في منصة العنابي للخدمات الرقمية 24/7** 🚀\n\n"
        "🤖 *أنا مساعدك الذكي والمستقل لإدارة وتلبية طلباتك بشكل آلي وسريع.*\n\n"
        "✨ **خدماتنا المتاحة:**\n"
        "⚡ شحن فوري للألعاب وعملات USDT.\n"
        "🍿 اشتراكات ترفيهية مضمونة طيلة المدة.\n"
        "🛡️ معاملات آمنة وموثوقة في السوق الجزائري.\n\n"
        "👇 **اختر الخدمة المطلوبة من الأزرار أدناه:**"
    )
    bot.send_message(message.chat.id, welcome_text, reply_markup=markup, parse_mode="Markdown")

# الرد التلقائي عند إرسال صور أو وصلات الدفع (لكي يستقل البوت في التعامل مع الزبائن)
@bot.message_handler(content_types=['photo'])
def handle_docs(message):
    reply_text = (
        "📥 **تم استلام إيصال الدفع بنجاح!**\n\n"
        "⏳ *البوت يقوم بتحويل طلبك إلى فريق الإدارة للمراجعة والتنفيذ الفوري.*\n"
        "شكراً لثقتكم بخدماتنا، سيتم التواصل معك أو شحن طلبك في أقرب وقت."
    )
    bot.reply_to(message, reply_text, parse_mode="Markdown")

# التعامل مع الأزرار التفاعلية
@bot.callback_query_handler(func=lambda call: True)
def callback_query(call):
    if call.data == 'games':
        text = (
            "🎮 **قسم شحن الألعاب (Free Fire & فري فاير):**\n\n"
            "💎 **العروض المتوفرة حالياً:**\n"
            "• 100 جوهرة\n"
            "• 310 جوهرة (الأكثر طلباً 🔥)\n"
            "• 520 جوهرة\n\n"
            "🛒 **خطوات الطلب الذاتي:**\n"
            "1. قم بتحويل المبلغ عبر CCP أو بينانس.\n"
            "2. أرسل **صورة الإيصال (وصل الدفع)** هنا في البوت مباشرة مع كتابة الـ (ID) الخاص بك.\n"
            "3. استلم جواهرك فوراً!"
        )
        bot.answer_callback_query(call.id)
        bot.send_message(call.message.chat.id, text, parse_mode="Markdown")
        
    elif call.data == 'usdt':
        text = (
            "💱 **قسم صرافة USDT الرقمية:**\n\n"
            "📈 بيع وشراء العملات الرقمية بكل أمان وثقة.\n"
            "• متوفر الدفع بالـ CCP / BaridiMob.\n"
            "• أسعار تنافسية ومحدثة.\n\n"
            "💬 للاتفاق الفوري، تواصل مع الإدارة عبر زر الدعم."
        )
        bot.answer_callback_query(call.id)
        bot.send_message(call.message.chat.id, text, parse_mode="Markdown")
        
    elif call.data == 'subs':
        text = (
            "📺 **قسم الاشتراكات الرقمية والترفيهية:**\n\n"
            "🍿 **Netflix:** حسابات رسمية وضمان كامل.\n"
            "📡 **IPTV:** اشتراكات سنوية لأقوى الباقات والقنوات بجودة عالية.\n\n"
            "💳 أرسل إيصال الدفع واستلم معلومات الدخول في الحال!"
        )
        bot.answer_callback_query(call.id)
        bot.send_message(call.message.chat.id, text, parse_mode="Markdown")
        
    elif call.data == 'payment':
        text = f"💳 **بيانات الدفع الرسمية المعتمدة:**\n\n{CCP_INFO}\n\n━━━━━━━━━━━━━━━\n\n{BINANCE_INFO}"
        bot.answer_callback_query(call.id)
        bot.send_message(call.message.chat.id, text, parse_mode="Markdown")
        
    elif call.data == 'support':
        text = f"📞 **مركز الدعم والخدمة:**\n\n{SUPPORT_CONTACT}\n\nنحن في خدمتك على مدار الساعة."
        bot.answer_callback_query(call.id)
        bot.send_message(call.message.chat.id, text, parse_mode="Markdown")

# تشغيل النظام الآلي السحابي
if __name__ == '__main__':
    t = Thread(target=run_web)
    t.start()
    print("Autonomous Bot is running 24/7...")
    bot.infinity_polling()

