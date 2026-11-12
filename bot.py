"""A small, dependency-free Telegram bot using the official Bot API."""

from __future__ import annotations

import html
import json
import logging
import os
import time
import urllib.error
import urllib.parse
import urllib.request
from typing import Any

import storage
from storage import BusinessError


LOGGER = logging.getLogger("rewards_bot")
TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "").strip()
ADMIN_IDS_RAW = os.environ.get("TELEGRAM_ADMIN_IDS", "")
MINING_REWARD_POINTS = int(os.environ.get("MINING_REWARD_POINTS", "10"))
MINING_COOLDOWN_HOURS = int(os.environ.get("MINING_COOLDOWN_HOURS", "24"))
MINING_COOLDOWN_SECONDS = MINING_COOLDOWN_HOURS * 60 * 60
MAX_MESSAGE_LENGTH = 4000

MAIN_MENU = {
    "keyboard": [
        [{"text": "💰 رصيدي"}, {"text": "📋 المهام"}],
        [{"text": "⛏️ نقاط التعدين"}, {"text": "📢 الإعلانات"}],
        [{"text": "💸 طلب استبدال"}, {"text": "🆘 المساعدة"}],
    ],
    "resize_keyboard": True,
}


class TelegramAPIError(Exception):
    pass


def _parse_admin_ids() -> set[int]:
    ids: set[int] = set()
    for value in ADMIN_IDS_RAW.split(","):
        value = value.strip()
        if value:
            try:
                ids.add(int(value))
            except ValueError as exc:
                raise RuntimeError("TELEGRAM_ADMIN_IDS must contain numeric Telegram user IDs.") from exc
    return ids


ADMIN_IDS = _parse_admin_ids()


def telegram(method: str, params: dict[str, Any] | None = None) -> Any:
    if not TOKEN:
        raise RuntimeError("TELEGRAM_BOT_TOKEN is not configured.")

    payload: dict[str, str] = {}
    for key, value in (params or {}).items():
        if value is None:
            continue
        if isinstance(value, bool):
            payload[key] = str(value).lower()
        else:
            payload[key] = value if isinstance(value, str) else str(value)
    request = urllib.request.Request(
        f"https://api.telegram.org/bot{TOKEN}/{method}",
        data=urllib.parse.urlencode(payload).encode("utf-8"),
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=40) as response:
            body = response.read()
    except urllib.error.HTTPError as exc:
        raise TelegramAPIError(f"Telegram returned HTTP {exc.code}.") from None
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        reason = getattr(exc, "reason", None)
        raise TelegramAPIError(f"Network request failed ({type(reason or exc).__name__}).") from None

    try:
        result = json.loads(body.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        raise TelegramAPIError("Telegram returned an unreadable response.") from None
    if not result.get("ok"):
        raise TelegramAPIError("Telegram rejected the request.")
    return result.get("result")


def send_message(
    chat_id: int,
    text: str,
    reply_markup: dict[str, Any] | None = None,
    parse_mode: str | None = "HTML",
) -> None:
    if len(text) > MAX_MESSAGE_LENGTH:
        text = text[: MAX_MESSAGE_LENGTH - 20] + "\n…"
    params: dict[str, Any] = {"chat_id": chat_id, "text": text}
    if parse_mode:
        params["parse_mode"] = parse_mode
    if reply_markup is not None:
        params["reply_markup"] = json.dumps(reply_markup, ensure_ascii=False)
    telegram("sendMessage", params)


def answer_callback(callback_id: str, text: str = "", show_alert: bool = False) -> None:
    telegram(
        "answerCallbackQuery",
        {"callback_query_id": callback_id, "text": text[:180], "show_alert": show_alert},
    )


def private_chat_id(update: dict[str, Any]) -> int | None:
    message = update.get("message")
    if message:
        chat = message.get("chat", {})
        if chat.get("type") == "private":
            return int(chat["id"])
        return None
    callback = update.get("callback_query", {})
    chat = callback.get("message", {}).get("chat", {})
    if chat.get("type") == "private":
        return int(chat["id"])
    return None


def is_admin(user_id: int) -> bool:
    return user_id in ADMIN_IDS


def notify_admins(text: str, reply_markup: dict[str, Any] | None = None) -> None:
    for admin_id in ADMIN_IDS:
        try:
            send_message(admin_id, text, reply_markup=reply_markup)
        except TelegramAPIError as exc:
            # The admin must start the bot before it can receive private messages.
            LOGGER.warning("Could not notify an admin (%s).", type(exc).__name__)


def start_message(user_id: int, first_name: str) -> None:
    safe_name = html.escape(first_name or "صديق")
    send_message(
        user_id,
        (
            f"أهلًا {safe_name} في بوت النقاط.\n\n"
            "يمكنك إرسال إثبات المهام للحصول على نقاط بعد مراجعة المشرف، "
            "وجمع نقاط تعدين تجريبية. النقاط هنا داخلية وليست عملة رقمية "
            "ولا تمثل ربحًا مضمونًا.\n\n"
            "طلبات الاستبدال يراجعها المشرف يدويًا."
        ),
        reply_markup=MAIN_MENU,
    )


def show_balance(user_id: int) -> None:
    balance = storage.get_balance(user_id)
    send_message(
        user_id,
        f"رصيدك الحالي: <b>{balance:,} نقطة</b>\n"
        "النقاط داخلية، ولا تعني قيمة نقدية ثابتة أو ضمانًا للدفع.",
        reply_markup=MAIN_MENU,
    )


def show_tasks(user_id: int) -> None:
    tasks = storage.list_active_tasks()
    if not tasks:
        send_message(user_id, "لا توجد مهام متاحة حاليًا.", reply_markup=MAIN_MENU)
        return
    for task in tasks:
        title = html.escape(str(task["title"]))
        instructions = html.escape(str(task["instructions"]))
        text = (
            f"<b>المهمة #{task['id']}: {title}</b>\n"
            f"{instructions}\n\n"
            f"المكافأة بعد الاعتماد: <b>{task['reward_points']} نقطة</b>"
        )
        markup = {
            "inline_keyboard": [
                [{"text": "إرسال الإثبات", "callback_data": f"task:submit:{task['id']}"}]
            ]
        }
        send_message(user_id, text, reply_markup=markup)


def show_ads_notice(user_id: int) -> None:
    send_message(
        user_id,
        (
            "مكافآت الإعلانات غير مفعّلة حاليًا.\n"
            "لن يُضاف رصيد لمجرد فتح رابط أو النقر عليه. يلزم أن تسمح شبكة الإعلان "
            "بالزيارات المحفّزة وأن توفر طريقة موثوقة للتحقق من إكمال الإعلان."
        ),
        reply_markup=MAIN_MENU,
    )


def start_withdrawal(user_id: int) -> None:
    balance = storage.get_balance(user_id)
    if balance <= 0:
        send_message(user_id, "لا يوجد رصيد متاح لطلب الاستبدال.", reply_markup=MAIN_MENU)
        return
    storage.set_state(user_id, "withdraw_amount")
    send_message(
        user_id,
        (
            f"رصيدك المتاح {balance:,} نقطة.\n"
            "أرسل عدد النقاط الذي تريد طلب استبداله كرقم صحيح.\n\n"
            "تنبيه: لا يوجد تحويل تلقائي إلى دج أو USDT؛ الطلب يراجعه المشرف "
            "وفق شروط البرنامج. أرسل /cancel للإلغاء."
        ),
        reply_markup=MAIN_MENU,
    )


def handle_state(user_id: int, text: str) -> bool:
    current = storage.get_state(user_id)
    if current is None:
        return False

    state, payload = current
    if state == "task_proof":
        proof = text.strip()
        if not proof:
            send_message(user_id, "أرسل وصفًا أو رابطًا عامًا يثبت إكمال المهمة، أو /cancel.")
            return True
        try:
            submission_id = storage.submit_task_proof(int(payload["task_id"]), user_id, proof)
        except (BusinessError, KeyError, ValueError) as exc:
            storage.clear_state(user_id)
            send_message(user_id, str(exc) if isinstance(exc, BusinessError) else "تعذر حفظ الإثبات.")
            return True
        storage.clear_state(user_id)
        task = storage.get_submission(submission_id)
        send_message(user_id, "تم استلام الإثبات. سيظهر الرصيد بعد اعتماد المشرف.")
        if task:
            notify_admins(
                (
                    f"<b>إثبات مهمة جديد #{submission_id}</b>\n"
                    f"المهمة: {html.escape(str(task['title']))}\n"
                    f"معرّف المستخدم: <code>{user_id}</code>\n"
                    f"الإثبات: {html.escape(str(task['proof']))}"
                ),
                {
                    "inline_keyboard": [[
                        {"text": "اعتماد", "callback_data": f"task:approve:{submission_id}"},
                        {"text": "رفض", "callback_data": f"task:reject:{submission_id}"},
                    ]]
                },
            )
        return True

    if state == "withdraw_amount":
        try:
            points = int(text.strip())
        except ValueError:
            send_message(user_id, "أرسل عدد النقاط كرقم صحيح، أو /cancel.")
            return True
        if points <= 0:
            send_message(user_id, "أدخل عدد نقاط أكبر من صفر.")
            return True
        balance = storage.get_balance(user_id)
        if points > balance:
            send_message(user_id, f"رصيدك {balance:,} نقطة فقط. أرسل رقمًا أقل أو /cancel.")
            return True
        storage.set_state(user_id, "withdraw_method", {"points": points})
        send_message(
            user_id,
            f"اختر وسيلة المراجعة لطلب {points:,} نقطة:",
            reply_markup={
                "inline_keyboard": [[
                    {"text": "CCP", "callback_data": "withdraw:method:ccp"},
                    {"text": "USDT", "callback_data": "withdraw:method:binance"},
                ]]
            },
        )
        return True

    if state == "withdraw_method":
        send_message(user_id, "اختر الوسيلة من الأزرار أعلاه، أو أرسل /cancel.")
        return True

    return False


def handle_message(message: dict[str, Any]) -> None:
    chat = message.get("chat", {})
    if chat.get("type") != "private":
        return
    user = message.get("from", {})
    user_id = int(user["id"])
    text = str(message.get("text", "")).strip()
    storage.register_user(user_id, str(user.get("first_name", "")), user.get("username"))

    if text.startswith("/"):
        storage.clear_state(user_id)
        handle_command(user_id, text, str(user.get("first_name", "")))
        return

    if text == "💰 رصيدي":
        show_balance(user_id)
    elif text == "📋 المهام":
        show_tasks(user_id)
    elif text == "⛏️ نقاط التعدين":
        handle_mining(user_id)
    elif text == "📢 الإعلانات":
        show_ads_notice(user_id)
    elif text == "💸 طلب استبدال":
        start_withdrawal(user_id)
    elif text == "🆘 المساعدة":
        show_help(user_id)
    elif not handle_state(user_id, text):
        send_message(user_id, "اختر أحد الأزرار من القائمة أو أرسل /help.", reply_markup=MAIN_MENU)


def handle_command(user_id: int, text: str, first_name: str = "") -> None:
    command, _, args = text.partition(" ")
    command = command.split("@", 1)[0].lower()
    args = args.strip()

    if command == "/start":
        start_message(user_id, first_name)
    elif command in ("/help",):
        show_help(user_id)
    elif command in ("/balance",):
        show_balance(user_id)
    elif command in ("/tasks",):
        show_tasks(user_id)
    elif command in ("/mine",):
        handle_mining(user_id)
    elif command in ("/ads",):
        show_ads_notice(user_id)
    elif command in ("/withdraw",):
        start_withdrawal(user_id)
    elif command == "/cancel":
        storage.clear_state(user_id)
        send_message(user_id, "تم إلغاء العملية.", reply_markup=MAIN_MENU)
    elif command == "/admin":
        handle_admin_home(user_id)
    elif command == "/taskadd":
        handle_task_add(user_id, args)
    elif command == "/taskpause":
        handle_task_pause(user_id, args)
    elif command == "/pending":
        handle_pending(user_id)
    elif command == "/stats":
        handle_stats(user_id)
    else:
        send_message(user_id, "الأمر غير معروف. أرسل /help لعرض الخيارات.", reply_markup=MAIN_MENU)


def handle_mining(user_id: int) -> None:
    if MINING_REWARD_POINTS <= 0 or MINING_COOLDOWN_HOURS <= 0:
        send_message(user_id, "التعدين التجريبي غير مضبوط حاليًا.")
        return
    try:
        balance = storage.claim_mining(user_id, MINING_REWARD_POINTS, MINING_COOLDOWN_SECONDS)
    except BusinessError as exc:
        send_message(user_id, str(exc), reply_markup=MAIN_MENU)
        return
    send_message(
        user_id,
        (
            f"أُضيفت <b>{MINING_REWARD_POINTS} نقطة تجريبية</b> إلى رصيدك.\n"
            f"الرصيد الآن: {balance:,} نقطة.\n"
            f"المحاولة التالية بعد {MINING_COOLDOWN_HOURS} ساعة."
        ),
        reply_markup=MAIN_MENU,
    )


def show_help(user_id: int) -> None:
    send_message(
        user_id,
        (
            "<b>المساعدة</b>\n"
            "/start — بدء الاستخدام\n"
            "/balance — عرض النقاط\n"
            "/tasks — عرض المهام\n"
            "/mine — جمع نقاط تجريبية\n"
            "/ads — حالة مكافآت الإعلانات\n"
            "/withdraw — طلب استبدال يدوي\n"
            "/cancel — إلغاء الخطوة الحالية\n\n"
            "لا ترسل كلمات مرور أو مفاتيح سرية أو بيانات بطاقات. "
            "النقاط ليست عملة رقمية ولا تضمن عائدًا نقديًا."
        ),
        reply_markup=MAIN_MENU,
    )


def _require_admin(user_id: int) -> bool:
    if is_admin(user_id):
        return True
    send_message(user_id, "هذا الأمر مخصص للمشرف.")
    return False


def handle_admin_home(user_id: int) -> None:
    if not _require_admin(user_id):
        return
    stats = storage.get_stats()
    send_message(
        user_id,
        (
            "<b>إدارة البوت</b>\n"
            f"المستخدمون: {stats['users']}\n"
            f"إثباتات معلقة: {stats['pending_tasks']}\n"
            f"طلبات استبدال مفتوحة: {stats['pending_withdrawals']}\n\n"
            "<code>/taskadd النقاط | العنوان | التعليمات</code>\n"
            "<code>/taskpause رقم_المهمة</code>\n"
            "<code>/pending</code>\n"
            "<code>/stats</code>"
        ),
    )


def handle_task_add(user_id: int, args: str) -> None:
    if not _require_admin(user_id):
        return
    parts = [part.strip() for part in args.split("|", 2)]
    if len(parts) != 3:
        send_message(user_id, "الصيغة: <code>/taskadd النقاط | العنوان | التعليمات</code>")
        return
    try:
        reward = int(parts[0])
        if reward <= 0:
            raise ValueError
        task_id = storage.create_task(parts[1], parts[2], reward, user_id)
    except ValueError:
        send_message(user_id, "النقاط يجب أن تكون عددًا صحيحًا موجبًا.")
        return
    except BusinessError as exc:
        send_message(user_id, str(exc))
        return
    send_message(user_id, f"تم إنشاء المهمة #{task_id}.")


def handle_task_pause(user_id: int, args: str) -> None:
    if not _require_admin(user_id):
        return
    try:
        task_id = int(args)
        active = storage.pause_task(task_id, user_id)
    except ValueError:
        send_message(user_id, "أرسل رقم المهمة، مثل <code>/taskpause 12</code>.")
        return
    except BusinessError as exc:
        send_message(user_id, str(exc))
        return
    send_message(user_id, f"تم {'تفعيل' if active else 'إيقاف'} المهمة #{task_id}.")


def handle_pending(user_id: int) -> None:
    if not _require_admin(user_id):
        return
    pending = storage.get_pending_items()
    items_count = len(pending["submissions"]) + len(pending["withdrawals"])
    if not items_count:
        send_message(user_id, "لا توجد طلبات معلقة.")
        return

    for item in pending["submissions"]:
        submission_id = int(item["id"])
        text = (
            f"<b>إثبات مهمة #{submission_id}</b>\n"
            f"المهمة: {html.escape(str(item['title']))}\n"
            f"المستخدم: <code>{item['user_id']}</code>\n"
            f"الإثبات: {html.escape(str(item['proof']))}"
        )
        send_message(
            user_id,
            text,
            reply_markup={
                "inline_keyboard": [[
                    {"text": "اعتماد", "callback_data": f"task:approve:{submission_id}"},
                    {"text": "رفض", "callback_data": f"task:reject:{submission_id}"},
                ]]
            },
        )

    for item in pending["withdrawals"]:
        request_id = int(item["id"])
        method = "CCP" if item["method"] == "ccp" else "USDT"
        text = (
            f"<b>طلب استبدال #{request_id}</b>\n"
            f"المستخدم: <code>{item['user_id']}</code>\n"
            f"النقاط المحجوزة: {item['points']:,}\n"
            f"الوسيلة المطلوبة: {method}\n"
            "لا تُسجل الطلب كمدفوع إلا بعد إجراء التحويل يدويًا."
        )
        buttons = [[
            {"text": "قبول للمراجعة", "callback_data": f"withdraw:approve:{request_id}"},
            {"text": "رفض وإرجاع النقاط", "callback_data": f"withdraw:reject:{request_id}"},
        ]]
        if item.get("status") == "approved":
            buttons = [[{"text": "تأكيد الدفع اليدوي", "callback_data": f"withdraw:paid:{request_id}"}]]
        send_message(user_id, text, reply_markup={"inline_keyboard": buttons})


def handle_stats(user_id: int) -> None:
    if not _require_admin(user_id):
        return
    stats = storage.get_stats()
    send_message(
        user_id,
        (
            "<b>ملخص البوت</b>\n"
            f"المستخدمون: {stats['users']}\n"
            f"إثباتات بانتظار المراجعة: {stats['pending_tasks']}\n"
            f"طلبات الاستبدال المفتوحة: {stats['pending_withdrawals']}"
        ),
    )


def handle_callback(callback: dict[str, Any]) -> None:
    callback_id = str(callback["id"])
    callback_chat = callback.get("message", {}).get("chat", {})
    if callback_chat.get("type") != "private":
        answer_callback(callback_id, "استخدم البوت في المحادثة الخاصة.", show_alert=True)
        return
    data = str(callback.get("data", ""))
    user = callback.get("from", {})
    user_id = int(user["id"])
    storage.register_user(user_id, str(user.get("first_name", "")), user.get("username"))

    parts = data.split(":")
    if len(parts) == 3 and parts[0] == "task" and parts[1] == "submit":
        try:
            task_id = int(parts[2])
            storage.set_state(user_id, "task_proof", {"task_id": task_id})
            answer_callback(callback_id, "أرسل الإثبات في رسالة خاصة.")
            send_message(user_id, "أرسل وصفًا أو رابطًا عامًا يثبت إكمال المهمة، أو /cancel.")
        except (ValueError, TelegramAPIError):
            answer_callback(callback_id, "تعذر بدء إرسال الإثبات.", show_alert=True)
        return

    if len(parts) == 3 and parts[0] == "withdraw" and parts[1] == "method":
        method = parts[2]
        current = storage.get_state(user_id)
        if method not in ("ccp", "binance") or current is None or current[0] != "withdraw_method":
            answer_callback(callback_id, "انتهت هذه الخطوة. ابدأ طلبًا جديدًا.", show_alert=True)
            return
        try:
            points = int(current[1]["points"])
            request_id = storage.create_withdrawal(user_id, points, method)
            storage.clear_state(user_id)
            answer_callback(callback_id, "تم إرسال الطلب للمراجعة.")
            send_message(
                user_id,
                (
                    f"سُجل طلب الاستبدال #{request_id} لـ {points:,} نقطة.\n"
                    "حُجزت النقاط مؤقتًا. إذا رُفض الطلب فستُعاد إلى رصيدك. "
                    "لا يتم أي تحويل تلقائي."
                ),
                reply_markup=MAIN_MENU,
            )
            method_label = "CCP" if method == "ccp" else "USDT"
            notify_admins(
                (
                    f"<b>طلب استبدال جديد #{request_id}</b>\n"
                    f"المستخدم: <code>{user_id}</code>\n"
                    f"النقاط: {points:,}\n"
                    f"الوسيلة: {method_label}\n"
                    "راجع شروط البرنامج وتواصل مع المستخدم قبل أي تحويل."
                ),
                {
                    "inline_keyboard": [[
                        {"text": "قبول للمراجعة", "callback_data": f"withdraw:approve:{request_id}"},
                        {"text": "رفض وإرجاع النقاط", "callback_data": f"withdraw:reject:{request_id}"},
                    ]]
                },
            )
        except (BusinessError, KeyError, ValueError) as exc:
            storage.clear_state(user_id)
            answer_callback(
                callback_id,
                str(exc) if isinstance(exc, BusinessError) else "تعذر إنشاء الطلب.",
                show_alert=True,
            )
        return

    if len(parts) == 3 and parts[0] == "task" and parts[1] in ("approve", "reject"):
        if not is_admin(user_id):
            answer_callback(callback_id, "غير مصرح.", show_alert=True)
            return
        try:
            submission_id = int(parts[2])
            approved = parts[1] == "approve"
            result = storage.review_submission(submission_id, user_id, approved)
            answer_callback(callback_id, "تمت المراجعة.")
            outcome = "اعتمد" if approved else "رُفض"
            send_message(user_id, f"تم {outcome} الإثبات #{submission_id}.")
            if approved:
                send_message(
                    result["user_id"],
                    f"تم اعتماد المهمة «{html.escape(result['title'])}» وأضيفت {result['points']} نقطة.",
                    reply_markup=MAIN_MENU,
                )
            else:
                send_message(result["user_id"], "لم يُعتمد إثبات المهمة. يمكنك إرسال إثبات جديد إذا كانت المهمة ما زالت متاحة.")
        except (BusinessError, ValueError) as exc:
            answer_callback(callback_id, str(exc) if isinstance(exc, BusinessError) else "رقم غير صالح.", show_alert=True)
        return

    if len(parts) == 3 and parts[0] == "withdraw" and parts[1] in ("approve", "reject", "paid"):
        if not is_admin(user_id):
            answer_callback(callback_id, "غير مصرح.", show_alert=True)
            return
        try:
            request_id = int(parts[2])
            result = storage.review_withdrawal(request_id, user_id, parts[1])
            answer_callback(callback_id, "تم تحديث الطلب.")
            send_message(user_id, f"تم تحديث حالة الطلب #{request_id} إلى {result['status']}.")
            if result["status"] == "approved":
                user_text = (
                    f"قُبل طلب الاستبدال #{request_id} للمراجعة النهائية. "
                    "لم يتم إرسال أي تحويل بعد؛ سيتواصل معك المشرف."
                )
            elif result["status"] == "rejected":
                user_text = f"رُفض طلب الاستبدال #{request_id} وأُعيدت النقاط إلى رصيدك."
            else:
                user_text = f"أكّد المشرف إتمام الدفع اليدوي لطلب #{request_id}. تواصل معه عند وجود مشكلة."
            send_message(result["user_id"], user_text, reply_markup=MAIN_MENU)
        except (BusinessError, ValueError) as exc:
            answer_callback(callback_id, str(exc) if isinstance(exc, BusinessError) else "رقم غير صالح.", show_alert=True)
        return

    answer_callback(callback_id, "هذا الزر غير صالح أو انتهت صلاحيته.", show_alert=True)


def process_update(update: dict[str, Any]) -> None:
    if "message" in update:
        handle_message(update["message"])
    elif "callback_query" in update:
        handle_callback(update["callback_query"])


def validate_configuration() -> None:
    if not TOKEN:
        raise RuntimeError("Add TELEGRAM_BOT_TOKEN in the project's Secrets.")
    if not ADMIN_IDS:
        raise RuntimeError("Set TELEGRAM_ADMIN_IDS to at least one numeric Telegram user ID.")
    if MINING_REWARD_POINTS <= 0 or MINING_COOLDOWN_HOURS <= 0:
        raise RuntimeError("Mining reward and cooldown must be positive integers.")


def run() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    validate_configuration()
    storage.initialize_database()

    me = telegram("getMe")
    telegram(
        "setMyCommands",
        {
            "commands": json.dumps(
                [
                    {"command": "start", "description": "بدء الاستخدام"},
                    {"command": "help", "description": "المساعدة"},
                    {"command": "balance", "description": "عرض الرصيد"},
                    {"command": "tasks", "description": "عرض المهام"},
                    {"command": "mine", "description": "نقاط التعدين التجريبية"},
                    {"command": "withdraw", "description": "طلب استبدال يدوي"},
                ],
                ensure_ascii=False,
            )
        },
    )
    LOGGER.info("Bot started as @%s.", me.get("username", "bot"))

    offset: int | None = None
    backoff = 1
    while True:
        try:
            updates = telegram(
                "getUpdates",
                {
                    "offset": offset,
                    "timeout": 25,
                    "allowed_updates": json.dumps(["message", "callback_query"]),
                },
            )
            backoff = 1
            for update in updates or []:
                offset = int(update["update_id"]) + 1
                try:
                    process_update(update)
                except Exception as exc:
                    LOGGER.error("Update failed (%s).", type(exc).__name__)
                    chat_id = private_chat_id(update)
                    if chat_id is not None:
                        try:
                            send_message(chat_id, "تعذر تنفيذ الطلب الآن. حاول مرة أخرى لاحقًا.")
                        except TelegramAPIError:
                            pass
        except TelegramAPIError as exc:
            LOGGER.warning("Polling failed (%s); retrying in %s seconds.", type(exc).__name__, backoff)
            time.sleep(backoff)
            backoff = min(backoff * 2, 30)


if __name__ == "__main__":
    run()
