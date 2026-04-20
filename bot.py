import os
import json
import vk_api
from vk_api.bot_longpoll import VkBotLongPoll, VkBotEventType
from vk_api.utils import get_random_id

# === ПРОВЕРКА ПЕРЕМЕННЫХ ОКРУЖЕНИЯ ===
VK_TOKEN = os.environ.get("VK_TOKEN")
GROUP_ID = os.environ.get("GROUP_ID")

if not VK_TOKEN or not GROUP_ID:
    raise ValueError("❌ Ошибка: задайте VK_TOKEN и GROUP_ID в переменных окружения")

GROUP_ID = int(GROUP_ID)

# === ЦЕЛЕВАЯ ССЫЛКА ===
LEAD_URL = "https://vk.cc/cWSPkT"

# === ВОПРОСЫ КВИЗА ===
questions = [
    {
        "text": "📊 Вопрос 1 из 4:\n\n**Какова общая сумма ваших долгов?**\n(кредиты, займы, налоги, ЖКХ)",
        "buttons": [
            {"label": "До 300 000 ₽", "value": "less_300k"},
            {"label": "300 000 – 600 000 ₽", "value": "300_600k"},
            {"label": "600 000 – 1 млн ₽", "value": "600k_1m"},
            {"label": "Больше 1 млн ₽", "value": "1m_plus"}
        ]
    },
    {
        "text": "💰 Вопрос 2 из 4:\n\n**Какой у вас доход в месяц после вычета обязательных платежей?**\n(кредиты, коммуналка, алименты)",
        "buttons": [
            {"label": "Меньше 15 000 ₽", "value": "low"},
            {"label": "15 000 – 30 000 ₽", "value": "medium"},
            {"label": "30 000 – 50 000 ₽", "value": "high"},
            {"label": "Больше 50 000 ₽", "value": "very_high"}
        ]
    },
    {
        "text": "🏠 Вопрос 3 из 4:\n\n**Есть ли у вас в собственности имущество?**\n(квартира, дом, земля, автомобиль, техника)",
        "buttons": [
            {"label": "Да, есть", "value": "yes"},
            {"label": "Нет, ничего", "value": "no"}
        ]
    },
    {
        "text": "⚖️ Вопрос 4 из 4:\n\n**Приставы уже списывают деньги с карты или зарплаты?**",
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
    "• Сохранить единственное жильё и имущество\n"
    "• Работаем официально по договору, 15 лет опыта\n\n"
    f"📝 **Бесплатная консультация юриста:**\n{LEAD_URL}\n\n"
    "Заполните короткую анкету — с вами свяжутся через 15 минут."
)

WELCOME_MESSAGE = (
    "👋 **Здравствуйте!**\n\n"
    "Я помощник юридической компании «Банкрот». Мы помогаем людям законно списывать долги через банкротство физических лиц.\n\n"
    "🔹 **Наши преимущества:**\n"
    "• 15 лет на рынке, 47 юристов в штате\n"
    "• Более 19 980 выигранных дел\n"
    "• 350+ млн рублей списанных долгов\n"
    "• 1800+ консультаций ежемесячно\n"
    "• 500+ отзывов от клиентов\n\n"
    "📊 **Пройдите короткий опрос (4 вопроса), и я скажу, подходит ли вам процедура банкротства.**\n\n"
    "👇 Нажмите кнопку ниже, чтобы начать."
)

user_states = {}
user_answers = {}

def send_keyboard(vk, peer_id, message_text, buttons, one_time=True):
    """Отправляет сообщение с клавиатурой."""
    if not message_text:
        message_text = "Выберите вариант ответа."
    keyboard = {
        "one_time": one_time,
        "buttons": []
    }
    row = []
    for i, btn in enumerate(buttons):
        button = {
            "action": {
                "type": "text",
                "label": btn["label"],
                "payload": json.dumps(btn["value"])
            },
            "color": "primary"
        }
        row.append(button)
        if (i + 1) % 2 == 0 or i == len(buttons) - 1:
            keyboard["buttons"].append(row)
            row = []
    keyboard_json = json.dumps(keyboard, ensure_ascii=False)
    vk.messages.send(
        peer_id=peer_id,
        message=message_text,
        random_id=get_random_id(),
        keyboard=keyboard_json
    )

def send_message(vk, peer_id, message_text):
    """Отправляет простое текстовое сообщение."""
    if not message_text:
        message_text = "..."
    vk.messages.send(
        peer_id=peer_id,
        message=message_text,
        random_id=get_random_id()
    )

def start_quiz(vk, peer_id, user_id):
    """Начинает квиз с первого вопроса."""
    user_states[user_id] = 0
    user_answers[user_id] = {}
    q = questions[0]
    send_keyboard(vk, peer_id, q["text"], q["buttons"])
    print(f"📌 Начат опрос для {user_id}")

def process_answer(vk, peer_id, user_id, answer_text, payload):
    """Обрабатывает ответ и переходит к следующему вопросу или завершает."""
    current = user_states.get(user_id)
    if current is None or current >= len(questions):
        start_quiz(vk, peer_id, user_id)
        return

    user_answers[user_id][f"q{current+1}"] = answer_text
    print(f"📝 {user_id} ответил на вопрос {current+1}: {answer_text}")

    next_q = current + 1
    if next_q < len(questions):
        user_states[user_id] = next_q
        q = questions[next_q]
        send_keyboard(vk, peer_id, q["text"], q["buttons"])
    else:
        # Квиз завершён
        del user_states[user_id]
        send_message(vk, peer_id, FINAL_MESSAGE)
        print(f"✅ Опрос завершён: {user_id} -> {json.dumps(user_answers[user_id], ensure_ascii=False)}")
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

            # Извлекаем payload
            payload = msg.get("payload")
            if payload:
                try:
                    payload = json.loads(payload)
                except:
                    payload = None

            # Если payload == "start" — запускаем квиз (это было нажатие на кнопку "Начать опрос")
            if payload == "start":
                start_quiz(vk, peer_id, user_id)
                continue

            # Текст сообщения (если пользователь написал что-то вручную)
            text = msg.get("text", "").strip().lower()
            if text in ["/start", "начать", "старт", "привет", "здравствуй", "бот"]:
                start_quiz(vk, peer_id, user_id)
                continue

            # Если пользователь в процессе квиза и пришёл ответ от кнопки
            if user_id in user_states:
                if payload is not None:
                    cur_q = user_states[user_id]
                    # Ищем кнопку с таким значением
                    for btn in questions[cur_q]["buttons"]:
                        if btn["value"] == payload:
                            process_answer(vk, peer_id, user_id, btn["label"], payload)
                            break
                    else:
                        send_message(vk, peer_id, "Пожалуйста, используйте кнопки для ответа.")
                else:
                    send_message(vk, peer_id, "📱 Отвечайте, пожалуйста, нажимая на кнопки под сообщением.")
            else:
                # Пользователь не в квизе — показываем приветствие с кнопкой
                keyboard = {
                    "one_time": False,
                    "buttons": [[{
                        "action": {
                            "type": "text",
                            "label": "▶️ Начать опрос",
                            "payload": json.dumps("start")
                        },
                        "color": "positive"
                    }]]
                }
                vk.messages.send(
                    peer_id=peer_id,
                    message=WELCOME_MESSAGE,
                    random_id=get_random_id(),
                    keyboard=json.dumps(keyboard, ensure_ascii=False)
                )

if __name__ == "__main__":
    main()
