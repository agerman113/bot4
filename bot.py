import os
import re
import json
import requests
import vk_api
from vk_api.bot_longpoll import VkBotLongPoll, VkBotEventType
from vk_api.keyboard import VkKeyboard, VkKeyboardColor
from vk_api.utils import get_random_id

# === КОНФИГУРАЦИЯ ===
VK_TOKEN = os.environ.get("VK_TOKEN")
GROUP_ID = os.environ.get("GROUP_ID")
LEAD_URL = "https://edin.center/vladivostok/bankrotstvo-fizicheskih-lic?utm_source=vk_bot"

if not VK_TOKEN or not GROUP_ID:
    raise ValueError("❌ Ошибка: переменные окружения VK_TOKEN и GROUP_ID не заданы!")

GROUP_ID = int(GROUP_ID)

# === СОСТОЯНИЯ ПОЛЬЗОВАТЕЛЕЙ ===
user_states = {}  # user_id -> current_question_index
user_answers = {}  # user_id -> dict of answers

# === ВОПРОСЫ КВИЗА ===
# Вопросы составлены так, чтобы на них нельзя было ответить "неподходяще".
# Любой ответ ведёт к выводу, что клиенту нужно банкротство.
questions = [
    {
        "text": "📊 Здравствуйте! Я помогу проверить, подходит ли вам процедура банкротства.\n\n"
                "Отвечайте честно — это займёт меньше минуты.\n\n"
                "👉 Вопрос 1 из 4:\n"
                "**Сколько у вас сейчас долгов по кредитам, займам, налогам или ЖКХ?**",
        "buttons": [
            {"label": "🔹 100 000 – 300 000 ₽", "value": "100-300k"},
            {"label": "🔸 300 000 – 600 000 ₽", "value": "300-600k"},
            {"label": "🔹 600 000 – 1 000 000 ₽", "value": "600k-1m"},
            {"label": "🔸 Более 1 000 000 ₽", "value": "1m+"}
        ]
    },
    {
        "text": "💰 Вопрос 2 из 4:\n"
                "**Какой у вас среднемесячный доход после уплаты всех обязательных платежей?**",
        "buttons": [
            {"label": "📉 Менее 15 000 ₽", "value": "less_15k"},
            {"label": "📊 15 000 – 30 000 ₽", "value": "15-30k"},
            {"label": "📈 30 000 – 50 000 ₽", "value": "30-50k"},
            {"label": "💵 Более 50 000 ₽", "value": "50k+"}
        ]
    },
    {
        "text": "🏠 Вопрос 3 из 4:\n"
                "**Есть ли у вас в собственности квартира, дом, автомобиль или другая недвижимость?**",
        "buttons": [
            {"label": "✅ Да, есть", "value": "yes"},
            {"label": "❌ Нет, ничего", "value": "no"}
        ]
    },
    {
        "text": "⚖️ Вопрос 4 из 4:\n"
                "**Возбуждено ли в отношении вас исполнительное производство (приставы списывают деньги с карты или зарплаты)?**",
        "buttons": [
            {"label": "⚠️ Да, уже списывают", "value": "yes"},
            {"label": "🟢 Нет, но коллекторы звонят", "value": "no_collectors"},
            {"label": "🔵 Нет, просто не хватает на платежи", "value": "no"}
        ]
    }
]

# === ФИНАЛЬНЫЙ ТЕКСТ (показывается после квиза) ===
FINAL_MESSAGE = (
    "✅ По результатам опроса вы подходите для списания долгов через банкротство.\n\n"
    "🎯 **Юристы нашей компании помогут:**\n"
    "• Полностью списать долги от 300 000 ₽\n"
    "• Остановить звонки коллекторов и приставов\n"
    "• Сохранить единственное жильё и имущество\n\n"
    "📝 **Чтобы получить бесплатную консультацию юриста и точный расчёт стоимости процедуры — "
    "заполните небольшую анкету на сайте.**\n\n"
    "🔗 **Перейти к заполнению анкеты:**\n"
    f"{LEAD_URL}\n\n"
    "💬 После отправки анкеты с вами свяжется юрист в течение 15 минут и ответит на все вопросы."
)

# === ОБРАБОТЧИКИ ===
def send_keyboard(vk, peer_id, text, buttons, one_time=True):
    """Отправляет сообщение с кнопками."""
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
    """Отправляет простое текстовое сообщение."""
    vk.method("messages.send", {
        "peer_id": peer_id,
        "text": text,
        "random_id": get_random_id()
    })

def start_quiz(vk, peer_id, user_id):
    """Начинает квиз с первого вопроса."""
    user_states[user_id] = 0
    user_answers[user_id] = {}
    q = questions[0]
    send_keyboard(vk, peer_id, q["text"], q["buttons"])

def process_answer(vk, peer_id, user_id, answer_text, payload):
    """Обрабатывает ответ пользователя и переключает вопросы."""
    current_q = user_states.get(user_id, -1)
    
    # Если пользователь не в квизе — начинаем заново
    if current_q == -1 or current_q >= len(questions):
        start_quiz(vk, peer_id, user_id)
        return
    
    # Сохраняем ответ
    user_answers[user_id][f"q{current_q+1}"] = {
        "text": questions[current_q]["text"],
        "answer": answer_text,
        "payload": payload
    }
    
    # Переходим к следующему вопросу
    next_q = current_q + 1
    
    if next_q < len(questions):
        # Есть ещё вопросы — задаём следующий
        user_states[user_id] = next_q
        q = questions[next_q]
        send_keyboard(vk, peer_id, q["text"], q["buttons"])
    else:
        # Квиз окончен — отправляем финальное сообщение и очищаем состояние
        del user_states[user_id]
        
        # Отправляем результат
        send_message(vk, peer_id, FINAL_MESSAGE)
        
        # Опционально: логируем ответы в консоль (на хостинге логи будут видны)
        print(f"📝 Пользователь {user_id} завершил опрос. Ответы: {json.dumps(user_answers[user_id], ensure_ascii=False, indent=2)}")
        del user_answers[user_id]

# === ЗАПУСК БОТА ===
def main():
    print("🚀 Бот запущен и слушает сообщения...")
    vk_session = vk_api.VkApi(token=VK_TOKEN)
    vk = vk_session.get_api()
    longpoll = VkBotLongPoll(vk_session, GROUP_ID)
    
    for event in longpoll.listen():
        if event.type == VkBotEventType.MESSAGE_NEW and event.from_user:
            peer_id = event.obj.message["peer_id"]
            user_id = event.obj.message["from_id"]
            message_text = event.obj.message.get("text", "").strip().lower()
            payload = None
            
            # Если есть payload (нажатие на кнопку) — используем его
            if "payload" in event.obj.message:
                try:
                    payload = json.loads(event.obj.message["payload"])
                except:
                    payload = None
            
            # Команда /start или "начать"
            if message_text in ["/start", "начать", "старт", "start", "привет"]:
                start_quiz(vk, peer_id, user_id)
                continue
            
            # Если пользователь в процессе квиза
            if user_id in user_states:
                # Если пришёл payload от кнопки — это ответ на вопрос
                if payload is not None:
                    # Находим текст кнопки по payload
                    current_q_idx = user_states[user_id]
                    if current_q_idx < len(questions):
                        for btn in questions[current_q_idx]["buttons"]:
                            if btn["value"] == payload:
                                process_answer(vk, peer_id, user_id, btn["label"], payload)
                                break
                        else:
                            # payload не совпал ни с одной кнопкой
                            send_message(vk, peer_id, "Пожалуйста, используйте кнопки для ответа.")
                    else:
                        # Состояние сбилось — перезапускаем
                        start_quiz(vk, peer_id, user_id)
                else:
                    # Текстовый ответ вместо кнопки — просим использовать кнопки
                    send_message(vk, peer_id, "📱 Пожалуйста, отвечайте, нажимая на кнопки под сообщением.")
            else:
                # Если написал что-то другое — предлагаем начать опрос
                keyboard = VkKeyboard(one_time=False)
                keyboard.add_button("Начать опрос", color=VkKeyboardColor.POSITIVE, payload="start")
                vk.method("messages.send", {
                    "peer_id": peer_id,
                    "text": "Привет! 👋\n\nЯ помогу проверить, подходит ли вам процедура банкротства.\n\nНажмите «Начать опрос» — это займёт меньше минуты.",
                    "random_id": get_random_id(),
                    "keyboard": keyboard.get_keyboard()
                })

if __name__ == "__main__":
    main()
