import os
import json
import vk_api
from vk_api.bot_longpoll import VkBotLongPoll, VkBotEventType
from vk_api.utils import get_random_id

# === ПЕРЕМЕННЫЕ ОКРУЖЕНИЯ ===
VK_TOKEN = os.environ.get("VK_TOKEN")
GROUP_ID = os.environ.get("GROUP_ID")

if not VK_TOKEN or not GROUP_ID:
    raise ValueError("Задайте VK_TOKEN и GROUP_ID в переменных окружения")

GROUP_ID = int(GROUP_ID)

# === ССЫЛКИ ===
CONSULTATION_URL = "https://vk.cc/cWSPkT"   # ссылка на бесплатную консультацию
PARTNER_URL = "https://vk.cc/cWSPv5"        # второй оффер (можно использовать в меню)

# === ЧАСТО ЗАДАВАЕМЫЕ ВОПРОСЫ (СПРАВКА) ===
faq_items = [
    {
        "title": "Что такое банкротство физических лиц?",
        "content": "Это законная процедура списания долгов, если вы не можете их платить. После завершения процедуры все долги (кредиты, займы, налоги, ЖКХ) аннулируются."
    },
    {
        "title": "Какие долги можно списать?",
        "content": "Кредиты, займы, просрочки по ЖКХ, налоги, штрафы, долги перед физлицами. Не списываются только алименты, возмещение вреда здоровью и текущие платежи."
    },
    {
        "title": "Что будет с имуществом?",
        "content": "Единственное жильё, предметы обихода, призы, инструменты для работы — остаются. Могут продать: вторую квартиру, машину, дорогую технику, землю. Но мы помогаем сохранить максимум."
    },
    {
        "title": "Сколько стоит процедура?",
        "content": "Стоимость зависит от сложности и региона. В среднем от 50 000 до 120 000 ₽. Возможна беспроцентная рассрочка. Точную цену скажет юрист на бесплатной консультации."
    },
    {
        "title": "Как долго длится банкротство?",
        "content": "Обычно 6–9 месяцев. Всё это время вы защищены от коллекторов и приставов."
    },
    {
        "title": "Кому подходит банкротство?",
        "content": "Гражданам РФ от 25 до 60 лет с долгами от 300 000 ₽. Подходят работающие (официально и нет) и безработные. Главное — отсутствие действующего статуса банкрота."
    }
]

# === ВОПРОСЫ КВИЗА ===
questions = [
    {
        "text": "📊 Вопрос 1 из 4\n\nКакова общая сумма ваших долгов?\n(кредиты, займы, налоги, ЖКХ)",
        "buttons": [
            {"label": "До 300 000 ₽", "value": "less_300k"},
            {"label": "300 000 – 600 000 ₽", "value": "300_600k"},
            {"label": "600 000 – 1 млн ₽", "value": "600k_1m"},
            {"label": "Больше 1 млн ₽", "value": "1m_plus"}
        ]
    },
    {
        "text": "💰 Вопрос 2 из 4\n\nКакой у вас доход в месяц после вычета обязательных платежей?",
        "buttons": [
            {"label": "Меньше 15 000 ₽", "value": "low"},
            {"label": "15 000 – 30 000 ₽", "value": "medium"},
            {"label": "30 000 – 50 000 ₽", "value": "high"},
            {"label": "Больше 50 000 ₽", "value": "very_high"}
        ]
    },
    {
        "text": "🏠 Вопрос 3 из 4\n\nЕсть ли у вас в собственности имущество? (квартира, дом, машина)",
        "buttons": [
            {"label": "Да, есть", "value": "yes"},
            {"label": "Нет, ничего", "value": "no"}
        ]
    },
    {
        "text": "⚖️ Вопрос 4 из 4\n\nПриставы уже списывают деньги с карты или зарплаты?",
        "buttons": [
            {"label": "Да, списывают", "value": "yes"},
            {"label": "Нет, но коллекторы звонят", "value": "collectors"},
            {"label": "Нет, просто сложно платить", "value": "hard"}
        ]
    }
]

FINAL_MESSAGE = (
    "✅ По результатам опроса вы **подходите** для банкротства.\n\n"
    "🎯 **Юридическая компания «Банкрот»** поможет:\n"
    "• Списать долги от 300 000 ₽ законно\n"
    "• Остановить коллекторов и приставов\n"
    "• Сохранить единственное жильё и имущество\n\n"
    f"📝 **Бесплатная консультация юриста:**\n{CONSULTATION_URL}\n\n"
    "Заполните анкету — свяжутся через 15 минут."
)

# === СОСТОЯНИЯ ПОЛЬЗОВАТЕЛЕЙ ===
class States:
    MAIN_MENU = "main_menu"
    QUIZ = "quiz"
    FAQ = "faq"

user_state = {}          # user_id -> состояние (States.MAIN_MENU, ...)
user_quiz_data = {}      # user_id -> {"current_q": int, "answers": dict}

# === ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ ===

def send_main_menu(vk, peer_id, user_id):
    """Отправляет главное меню с кнопками."""
    user_state[user_id] = States.MAIN_MENU
    keyboard = {
        "one_time": False,
        "buttons": [
            [
                {
                    "action": {
                        "type": "text",
                        "label": "📝 Пройти опрос",
                        "payload": json.dumps("quiz")
                    },
                    "color": "primary"
                },
                {
                    "action": {
                        "type": "text",
                        "label": "❓ Справка (FAQ)",
                        "payload": json.dumps("faq")
                    },
                    "color": "secondary"
                }
            ],
            [
                {
                    "action": {
                        "type": "open_link",
                        "label": "📞 Бесплатная консультация",
                        "link": CONSULTATION_URL
                    },
                    "color": "positive"
                }
            ]
        ]
    }
    message = (
        "🏠 **Главное меню**\n\n"
        "Я помогу вам разобраться с долгами. Выберите действие:\n"
        "• **Пройти опрос** — узнаете, подходит ли вам банкротство (4 вопроса)\n"
        "• **Справка** — ответы на частые вопросы\n"
        "• **Консультация** — сразу перейти к юристу"
    )
    vk.messages.send(
        peer_id=peer_id,
        message=message,
        random_id=get_random_id(),
        keyboard=json.dumps(keyboard, ensure_ascii=False)
    )

def send_quiz_question(vk, peer_id, user_id, q_index):
    """Отправляет вопрос квиза с кнопками 'Назад' (если не первый) и меню."""
    q = questions[q_index]
    # Кнопки ответов
    buttons = q["buttons"]
    # Добавляем служебные кнопки
    nav_buttons = []
    if q_index > 0:
        nav_buttons.append({"label": "◀ Назад", "value": "back"})
    nav_buttons.append({"label": "🏠 В меню", "value": "menu"})
    # Объединяем: сначала кнопки ответов, потом служебные (с новой строки)
    keyboard = {
        "one_time": False,
        "buttons": []
    }
    # Ряды с ответами
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
    # Служебные кнопки отдельным рядом
    service_row = []
    for btn in nav_buttons:
        service_row.append({
            "action": {
                "type": "text",
                "label": btn["label"],
                "payload": json.dumps(btn["value"])
            },
            "color": "secondary"
        })
    if service_row:
        keyboard["buttons"].append(service_row)
    
    vk.messages.send(
        peer_id=peer_id,
        message=q["text"],
        random_id=get_random_id(),
        keyboard=json.dumps(keyboard, ensure_ascii=False)
    )

def start_quiz(vk, peer_id, user_id):
    """Запускает квиз с первого вопроса."""
    user_state[user_id] = States.QUIZ
    user_quiz_data[user_id] = {"current_q": 0, "answers": {}}
    send_quiz_question(vk, peer_id, user_id, 0)

def handle_quiz_answer(vk, peer_id, user_id, payload):
    """Обрабатывает ответ в квизе (включая навигацию)."""
    data = user_quiz_data.get(user_id)
    if not data:
        start_quiz(vk, peer_id, user_id)
        return
    current = data["current_q"]
    if payload == "back":
        # Назад: переходим к предыдущему вопросу
        if current > 0:
            new_q = current - 1
            data["current_q"] = new_q
            send_quiz_question(vk, peer_id, user_id, new_q)
        else:
            send_quiz_question(vk, peer_id, user_id, current)
        return
    elif payload == "menu":
        # Прерываем квиз и уходим в меню
        if user_id in user_quiz_data:
            del user_quiz_data[user_id]
        send_main_menu(vk, peer_id, user_id)
        return
    else:
        # Обычный ответ на вопрос
        # Найдём текст кнопки по payload
        btn_text = None
        for btn in questions[current]["buttons"]:
            if btn["value"] == payload:
                btn_text = btn["label"]
                break
        if btn_text is None:
            # Неизвестный payload
            send_quiz_question(vk, peer_id, user_id, current)
            return
        # Сохраняем ответ
        data["answers"][f"q{current+1}"] = btn_text
        next_q = current + 1
        if next_q < len(questions):
            data["current_q"] = next_q
            send_quiz_question(vk, peer_id, user_id, next_q)
        else:
            # Квиз окончен
            # Показываем результат
            vk.messages.send(
                peer_id=peer_id,
                message=FINAL_MESSAGE,
                random_id=get_random_id()
            )
            # Удаляем данные квиза и возвращаем в меню
            del user_quiz_data[user_id]
            # Через паузу отправим меню (чтобы не заваливать сообщениями)
            # Но можно сразу отправить меню после финального сообщения
            send_main_menu(vk, peer_id, user_id)

def send_faq(vk, peer_id, user_id):
    """Отправляет список часто задаваемых вопросов с кнопками."""
    user_state[user_id] = States.FAQ
    # Формируем клавиатуру: по два вопроса в строке, плюс кнопка "Назад в меню"
    keyboard = {
        "one_time": False,
        "buttons": []
    }
    row = []
    for i, item in enumerate(faq_items):
        button = {
            "action": {
                "type": "text",
                "label": f"📌 {item['title'][:30]}",
                "payload": json.dumps(f"faq_{i}")
            },
            "color": "secondary"
        }
        row.append(button)
        if (i + 1) % 2 == 0 or i == len(faq_items) - 1:
            keyboard["buttons"].append(row)
            row = []
    # Кнопка "Назад в меню"
    keyboard["buttons"].append([{
        "action": {
            "type": "text",
            "label": "🏠 В главное меню",
            "payload": json.dumps("menu")
        },
        "color": "primary"
    }])
    message = "❓ **Часто задаваемые вопросы о банкротстве**\n\nВыберите интересующий вас вопрос:"
    vk.messages.send(
        peer_id=peer_id,
        message=message,
        random_id=get_random_id(),
        keyboard=json.dumps(keyboard, ensure_ascii=False)
    )

def handle_faq_answer(vk, peer_id, user_id, payload):
    """Показывает ответ на выбранный вопрос."""
    if payload == "menu":
        send_main_menu(vk, peer_id, user_id)
        return
    if payload.startswith("faq_"):
        idx = int(payload.split("_")[1])
        if 0 <= idx < len(faq_items):
            item = faq_items[idx]
            # Отправляем ответ, затем снова показываем список FAQ (или меню — по желанию)
            answer_text = f"**{item['title']}**\n\n{item['content']}"
            vk.messages.send(
                peer_id=peer_id,
                message=answer_text,
                random_id=get_random_id()
            )
            # После ответа показываем тот же список FAQ (чтобы можно было выбрать другой вопрос)
            send_faq(vk, peer_id, user_id)
        else:
            send_faq(vk, peer_id, user_id)

# === ГЛАВНЫЙ ЦИКЛ ===
def main():
    print("🚀 Бот запущен с меню и навигацией")
    vk_session = vk_api.VkApi(token=VK_TOKEN)
    vk = vk_session.get_api()
    longpoll = VkBotLongPoll(vk_session, GROUP_ID)

    for event in longpoll.listen():
        if event.type == VkBotEventType.MESSAGE_NEW and event.from_user:
            peer_id = event.obj.message["peer_id"]
            user_id = event.obj.message["from_id"]
            msg = event.obj.message

            payload = msg.get("payload")
            if payload:
                try:
                    payload = json.loads(payload)
                except:
                    payload = None
            text = msg.get("text", "").strip().lower()

            # Обработка команд
            if text in ["/start", "меню", "начать", "привет", "старт"]:
                send_main_menu(vk, peer_id, user_id)
                continue

            # Определяем текущее состояние пользователя
            state = user_state.get(user_id, States.MAIN_MENU)

            # Если пользователь прислал payload (нажатие на кнопку)
            if payload is not None:
                if state == States.MAIN_MENU:
                    if payload == "quiz":
                        start_quiz(vk, peer_id, user_id)
                    elif payload == "faq":
                        send_faq(vk, peer_id, user_id)
                    else:
                        send_main_menu(vk, peer_id, user_id)
                elif state == States.QUIZ:
                    handle_quiz_answer(vk, peer_id, user_id, payload)
                elif state == States.FAQ:
                    handle_faq_answer(vk, peer_id, user_id, payload)
                else:
                    send_main_menu(vk, peer_id, user_id)
            else:
                # Текстовое сообщение (не кнопка)
                if state == States.MAIN_MENU:
                    send_main_menu(vk, peer_id, user_id)
                elif state == States.QUIZ:
                    # Попросим использовать кнопки
                    vk.messages.send(
                        peer_id=peer_id,
                        message="📱 Пожалуйста, отвечайте на вопросы, нажимая на кнопки.",
                        random_id=get_random_id()
                    )
                elif state == States.FAQ:
                    send_faq(vk, peer_id, user_id)
                else:
                    send_main_menu(vk, peer_id, user_id)

if __name__ == "__main__":
    main()
