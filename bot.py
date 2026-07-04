import telebot
from telebot import types
from langchain_gigachat import GigaChat
from langchain_core.messages import SystemMessage, HumanMessage

TELEGRAM_TOKEN = "токен"
GIGACHAT_CREDENTIALS = "апи"
bot = telebot.TeleBot(TELEGRAM_TOKEN)
llm = GigaChat(credentials=GIGACHAT_CREDENTIALS, verify_ssl_certs=False, model="GigaChat")
user_sessions = {}

SYSTEM_PROMPT = (
    "Ты — ведущий и организатор мероприятий. Твоя цель — генерировать простые, "
    "понятные и лаконичные сценарии. Избегай канцеляризма, псевдонаучных терминов и общих фраз. "
    "Выдавай только конкретные практические идеи и четкий план по времени."
)

def main_menu():
    markup = types.InlineKeyboardMarkup()
    btn = types.InlineKeyboardButton("Спроектировать событие", callback_data="action_generate")
    markup.add(btn)
    return markup

@bot.message_handler(commands=['start'])
def cmd_start(message):
    bot.send_message(
        message.chat.id,
        f"Привет, {message.from_user.first_name}!\n"
        "Я ИИ-Помощник организатора. Помогу быстро набросать идеи и составить план для вашего мероприятия.\n\n"
        "Нажмите кнопку ниже, чтобы начать:",
        reply_markup=main_menu()
    )

@bot.callback_query_handler(func=lambda call: True)
def handle_callbacks(call):
    if call.data == "action_generate":
        user_sessions[call.message.chat.id] = {}
        msg = bot.send_message(call.message.chat.id, "Шаг 1: Введите название или тему мероприятия:")
        bot.register_next_step_handler(msg, process_title_step)
        bot.answer_callback_query(call.id)

def process_title_step(message):
    chat_id = message.chat.id
    user_sessions[chat_id]['title'] = message.text
    msg = bot.send_message(chat_id, "Шаг 2: Введите краткое описание или задачу (для кого проводится, какая цель):")
    bot.register_next_step_handler(msg, process_description_step)

def process_description_step(message):
    chat_id = message.chat.id
    user_sessions[chat_id]['description'] = message.text
    msg = bot.send_message(chat_id, "Шаг 3: Укажите длительность мероприятия:")
    bot.register_next_step_handler(msg, process_generation_step)

def process_generation_step(message):
    chat_id = message.chat.id
    user_sessions[chat_id]['duration'] = message.text

    data = user_sessions[chat_id]
    status_msg = bot.send_message(chat_id, "Генерирую план и подбираю идеи...")

    prompt = (
        f"Составь лаконичный план и предложи список идей по следующим параметрам:\n"
        f"- Название/Тема: {data['title']}\n"
        f"- Описание: {data['description']}\n"
        f"- Длительность: {data['duration']}\n\n"
        f"Ответ верни строго в таком формате разметки:\n"
        f"ПЛАН МЕРОПРИЯТИЯ: Название\n"
        f"Креативные идеи и фишки:\n"
        f"[Твой список идей]\n\n"
        f"План по времени (Длительность):\n"
        f"[Твой поминутный таймлайн]"
    )

    try:
        messages = [
            SystemMessage(content=SYSTEM_PROMPT),
            HumanMessage(content=prompt)
        ]

        result = llm.invoke(messages)
        response_text = result.content

        bot.delete_message(chat_id, status_msg.message_id)
        bot.send_message(chat_id, response_text, parse_mode="Markdown", reply_markup=main_menu())

    except Exception as e:
        bot.delete_message(chat_id, status_msg.message_id)
        bot.send_message(chat_id, f"Ошибка генерации: {str(e)}", reply_markup=main_menu())

    if chat_id in user_sessions:
        del user_sessions[chat_id]

if __name__ == "__main__":
    bot.infinity_polling()
