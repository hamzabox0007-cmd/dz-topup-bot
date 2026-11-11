import os
import telebot
from telebot import types

# توكن بوت التيليجرام الخاص بك
TOKEN = '9181651284:AAFhCeulxRzQYuJ_VmLSy8E054kVZPNXkF8'
bot = telebot.TeleBot(TOKEN)

# معلومات الدفع الخاصة بك
CCP_INFO = "📌 رقم حساب CCP / RIP:\n00799999001922271613\nالاسم: خدمة الوساطة الرقمية\n\nأرسل إيصال الدفع (وصل الدفع) هنا في البوت مع تحديد الطلب."
BINANCE_INFO = "📌 محفظة بينانس (USDT - TRC20):\n`TM72iNjNBDRvUE46KCrK8z1d2PSeaWrVGT`\n\nأرسل لقطة شاشة للتحويل مع معرف الصفقة (TxID)."

# رسالة الترحيب والأزرار الرئيسية
@bot.message_handler(commands=['start'])
def send_welcome(markup_user):
    markup = types.InlineKeyboardMarkup(row_width=2)
    btn_games = types.InlineKeyboardButton("🎮 شحن الألعاب (Free Fire)", callback_data='games')
    btn_usdt = types.InlineKeyboardButton("💱 بيع وشراء USDT", callback_data='usdt')
    btn_subs = types.InlineKeyboardButton("📺 اشتراكات رقمية (Netflix / IPTV)", callback_data='subs')
    btn_pay = types.InlineKeyboardButton("💳 معلومات الدفع (CCP & Binance)", callback_data='payment')
    
    markup.add(btn_games, btn_usdt, btn_subs, btn_pay)
    
    welcome_text = (
        "مرحباً بك يا العنابي في منصة الوساطة الرقمية 24/7 🚀\n"
        "نحن هنا لتلبية جميع طلباتك بسرعة وأمان تام.\n\n"
        "اختر الخدمة التي تناسبك من الأسفل:"
    )
    bot.send_message(markup_user.chat.id, welcome_text, reply_markup=markup)

# التعامل مع الضغط على الأزرار
@bot.callback_query_handler(func=lambda call: True)
def callback_query(call):
    if call.data == 'games':
        text = "🎮 **شحن ألعاب (Free Fire / بايكات):**\n- 100 جوهرة\n- 310 جوهرة\n- 520 جوهرة\n\nللطلب، يرجى الدفع عبر CCP أو Binance ثم إرسال الوصل مع ذكر الآيدي الخاص بك."
        bot.answer_callback_query(call.id)
        bot.send_message(call.message.chat.id, text, parse_mode="Markdown")
        
    elif call.data == 'usdt':
        text = "💱 **صرافة USDT:**\nمتوفر البيع والشراء بأفضل سعر في السوق الجزائري.\n\nتواصل مباشرة عبر إرسال المبلغ المطلوب والتحويل."
        bot.answer_callback_query(call.id)
        bot.send_message(call.message.chat.id, text, parse_mode="Markdown")
        
    elif call.data == 'subs':
        text = "📺 **الاشتراكات الرقمية:**\n- حسابات Netflix رسمية وضمان كامل.\n- اشتراكات IPTV لمدة سنة بجودة عالية.\n\nاختر خدمتك وأرسل الإيصال لإتمام التفعيل."
        bot.answer_callback_query(call.id)
        bot.send_message(call.message.chat.id, text, parse_mode="Markdown")
        
    elif call.data == 'payment':
        text = f"💳 **طرق الدفع المعتمدة:**\n\n{CCP_INFO}\n\n-------------------\n\n{BINANCE_INFO}"
        bot.answer_callback_query(call.id)
        bot.send_message(call.message.chat.id, text, parse_mode="Markdown")

# تشغيل البوت باستمرار
if __name__ == '__main__':
    print("Bot is running...")
    bot.infinity_polling()
