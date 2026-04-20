import os
import json
import vk_api
from vk_api.bot_longpoll import VkBotLongPoll, VkBotEventType
from vk_api.keyboard import VkKeyboard, VkKeyboardColor
from vk_api.utils import get_random_id

# === ПРОВЕРКА ПЕРЕМЕННЫХ ОКРУЖЕНИЯ ===
VK_TOKEN = os.environ.get("VK_TOKEN")
GROUP_ID = os.environ.get("GROUP_ID")

if not VK_TOKEN or not GROUP_ID:
    raise ValueError("❌ Ошибка: задайте VK_TOKEN и GROUP_ID в переменных окружения")

GROUP_ID = int(GROUP_ID)

# === ЦЕЛЕВАЯ ССЫЛКА (первый оффер) ===
LEAD_URL = "https://vk.cc/cWSPkT"   # можно заменить на https://edin.center/... если нужно

# === ВОПРОСЫ КВИЗА ===
# Любой ответ подводит к тому, что банкротство подходит
questions = [
    {
        "text": "📊 Привет! Я помогу проверить, подходит ли вам списание долгов через банкротство.\n\n"
                "Вопрос 1 из 4:\n"
                "**Какова общая сумма ваших долгов?**",
        "buttons": [
            {"label": "До 300 000 ₽", "value": "less_300k"},
            {"label": "300 000 – 600 000 ₽", "value": "300_600k"},
            {"label": "600 000 – 1 млн ₽", "value": "600k_1m"},
            {"label": "Больше 1 млн ₽", "value": "1m_plus"}
        ]
    },
    {
        "text": "💰 Вопрос 2 из 4:\n"
                "**Какой у вас доход в месяц после вычета кредитов и коммуналки?**",
        "buttons": [
            {"label": "Меньше 15 000 ₽", "value": "low"},
            {"label": "15 000 – 30 000 ₽", "value": "medium"},
            {"label": "30 000 – 50 000 ₽", "value": "high"},
            {"label": "Больше 50 000 ₽", "value": "very_high"}
        ]
    },
    {
        "text": "🏠 Вопрос 3 из 4:\n"
                "**Есть ли у вас имущество: квартира, дом, машина?**",
        "buttons": [
            {"label": "Да, есть", "value": "yes"},
            {"label": "Нет, ничего", "value": "no"}
        ]
    },
    {
        "text": "⚖️ Вопрос 4 из 4:\n"
                "**Приставы уже списывают деньги с карты или зарплаты?**",
        "buttons": [
            {"label": "Да, списывают", "value": "yes"},
            {"label": "Нет, но коллекторы звонят", "value": "collectors"},
            {"label": "Нет, просто сложно платить", "value": "hard"}
        ]
    }
]

FINAL_MESSAGE = (
    "✅ По результатам опроса вы **подходите** для процедуры банкротства.\n\n"
    "🎯 **Юридическая компания «Банкрот»** поможет:\n"
    "• Списать все долги от 300 000 ₽ законно\n"
    "• Остановить звонки коллекторов и приставов\n"
    "• Сохранить единственное жильё и имущество\n\n"
    f"📝 **Бесплатная консультация юриста:**\n{LEAD_URL}\n\n"
    "Заполните короткую анкету — с вами свяжутся через 15 минут."
)

# === ХРАНИЛИЩЕ СОСТОЯНИЙ ===
user_states = {}   # user_id -> индекс текущего вопроса
user_answers = {}  # user_id -> dict ответов

def send_keyboard(vk, peer_id, text, buttons, one_time=True):
    keyboard = VkKeyboard(one_time=one_time)
    for i, btn in enumerate(buttons):
        if i % 2 == 0 and i != 0:
            keyboard.add_line()
        keyboard.add_button(btn["label"], color=VkKeyboardColor.PRIMARY, payload=btn["value"])
    vk.method("messages.send", {
        "peer_id": peer_id,
        "text": text,
        "random_id": get_random_id(),
        "keyboard": keyboard.get_keyboard()
    })

def send_message(vk, peer_id, text):
    vk.method("messages.send", {
        "peer_id": peer_id,
        "text": text,
        "random_id": get_random_id()
    })

def start_quiz(vk, peer_id, user_id):
    user_states[user_id] = 0
    user_answers[user_id] = {}
    q = questions[0]
    send_keyboard(vk, peer_id, q["text"], q["buttons"])

def process_answer(vk, peer_id, user_id, answer_text, payload):
    current = user_states.get(user_id)
    if current is None or current >= len(questions):
        start_quiz(vk, peer_id, user_id)
        return

    # сохраняем ответ
    user_answers[user_id][f"q{current+1}"] = answer_text

    next_q = current + 1
    if next_q < len(questions):
        user_states[user_id] = next_q
        q = questions[next_q]
        send_keyboard(vk, peer_id, q["text"], q["buttons"])
    else:
        # квиз закончен
        del user_states[user_id]
        send_message(vk, peer_id, FINAL_MESSAGE)
        # для отладки на хостинге можно вывести ответы в лог
        print(f"✅ Опрос завершён: {user_id} -> {user_answers[user_id]}")
        del user_answers[user_id]

def main():
    print("🚀 Бот запущен")
    vk_session = vk_api.VkApi(token=VK_TOKEN)
    vk = vk_session.get_api()
    longpoll = VkBotLongPoll(vk_session, GROUP_ID)

    for event in longpoll.listen():
        if event.type == VkBotEventType.MESSAGE_NEW and event.from_user:
            peer_id = event.obj.message["peer_id"]
            user_id = event.obj.message["from_id"]
            msg = event.obj.message

            # обрабатываем нажатие кнопки (payload)
            payload = msg.get("payload")
            if payload:
                try:
                    payload = json.loads(payload)
                except:
                    payload = None

            # команда /start или приветственное слово
            text = msg.get("text", "").strip().lower()
            if text in ["/start", "начать", "старт", "привет"]:
                start_quiz(vk, peer_id, user_id)
                continue

            # если пользователь в процессе квиза
            if user_id in user_states:
                if payload is not None:
                    # ищем текст кнопки по payload
                    cur_q = user_states[user_id]
                    for btn in questions[cur_q]["buttons"]:
                        if btn["value"] == payload:
                            process_answer(vk, peer_id, user_id, btn["label"], payload)
                            break
                    else:
                        send_message(vk, peer_id, "Пожалуйста, используйте кнопки для ответа.")
                else:
                    send_message(vk, peer_id, "📱 Отвечайте, пожалуйста, нажимая на кнопки под сообщением.")
            else:
                # не в квизе — предлагаем начать
                keyboard = VkKeyboard(one_time=False)
                keyboard.add_button("Начать опрос", color=VkKeyboardColor.POSITIVE, payload="start")
                vk.method("messages.send", {
                    "peer_id": peer_id,
                    "text": "Привет! 👋\n\nПройдите короткий опрос и узнайте, можно ли списать ваши долги.\n\nНажмите «Начать опрос» — это займёт меньше минуты.",
                    "random_id": get_random_id(),
                    "keyboard": keyboard.get_keyboard()
                })

if __name__ == "__main__":
    main()
