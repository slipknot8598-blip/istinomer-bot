import os
import openai
import re
import random
import asyncio
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes, CallbackQueryHandler
from telegram.request import HTTPXRequest

# ===== ПЕРЕМЕННЫЕ ОКРУЖЕНИЯ =====
CLOUD_API_KEY = os.getenv("CLOUD_API_KEY")
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")

# ===== КЛИЕНТ ДЛЯ CLOUD.RU =====
client = openai.OpenAI(
    api_key=CLOUD_API_KEY,
    base_url="https://foundation-models.api.cloud.ru/v1"
)

user_last_text = {}
user_history = {}

FACTS = [
    "Человек склонен верить тому, что подтверждает его картину мира. Это называется когнитивным искажением.",
    "Эмоции часто мешают видеть факты. Страх и гнев делают нас более доверчивыми к манипуляциям.",
    "Манипуляция работает через страх, надежду и чувство вины. Без них она теряет силу.",
    "Семантическая плотность — это количество реальной информации в тексте. Чем она выше, тем полезнее текст.",
    "Один и тот же текст может быть прочитан по-разному в зависимости от контекста и твоего настроения.",
    "Ложь часто звучит увереннее, чем правда. Уверенность — это не доказательство.",
    "Мы выбираем не то, во что верить, а то, что подтверждает наши убеждения. Это работает против нас.",
]

def clean_text(text):
    text = re.sub(r'\*+', '', text)
    text = re.sub(r'\_+', '', text)
    text = re.sub(r'\#+', '', text)
    text = re.sub(r'^[\s\-]+', '', text, flags=re.MULTILINE)
    text = re.sub(r'\n{3,}', '\n\n', text)
    return text.strip()

def analyze_text(text):
    try:
        response = client.chat.completions.create(
            model="Qwen/Qwen3-Coder-Next",
            messages=[
                {"role": "system", "content": (
                    "Ты — Истиномер. Ты показываешь структуру текста. "
                    "Ты не оцениваешь, не осуждаешь и не навязываешь. "
                    "Ты называешь три параметра: "
                    "индекс манипуляции (0–100%), "
                    "эмоциональный заряд (гнев, страх, радость или спокойствие), "
                    "семантическая плотность (кратко). "
                    "Ты не используешь звёздочки, списки или маркеры. "
                    "Твой тон — нейтральный, ясный, без лишней философии. "
                    "Ты помогаешь человеку видеть структуру, а не говоришь ему, что думать."
                )},
                {"role": "user", "content": text}
            ],
            temperature=0.3
        )
        return clean_text(response.choices[0].message.content)
    except Exception as e:
        return f"Ошибка: {e}"

def flip_text(text):
    try:
        response = client.chat.completions.create(
            model="Qwen/Qwen3-Coder-Next",
            messages=[
                {"role": "system", "content": (
                    "Ты переписываешь текст с противоположной точки зрения. "
                    "Сохраняешь все факты, но меняешь эмоциональную окраску и угол подачи. "
                    "Без звёздочек и маркеров. "
                    "Это не ложь и не истина — это другая проекция."
                )},
                {"role": "user", "content": text}
            ],
            temperature=0.7
        )
        return clean_text(response.choices[0].message.content)
    except Exception as e:
        return f"Ошибка при перевороте: {e}"

def blind_spot(text):
    try:
        response = client.chat.completions.create(
            model="Qwen/Qwen3-Coder-Next",
            messages=[
                {"role": "system", "content": (
                    "Ты — Истиномер. Ты показываешь, что человек мог упустить в тексте. "
                    "Ты не осуждаешь, а просто указываешь на скрытые детали: "
                    "неочевидные факты, логические разрывы, скрытые допущения, "
                    "эмоциональные триггеры, которые могли повлиять на восприятие. "
                    "Без звёздочек и списков. Говори коротко и ясно."
                )},
                {"role": "user", "content": text}
            ],
            temperature=0.5
        )
        return clean_text(response.choices[0].message.content)
    except Exception as e:
        return f"Ошибка: {e}"

def generate_report(text, analysis):
    try:
        response = client.chat.completions.create(
            model="Qwen/Qwen3-Coder-Next",
            messages=[
                {"role": "system", "content": (
                    "Ты — Истиномер. Ты создаёшь краткий отчёт по тексту. "
                    "Структура: оценка правдивости, эмоциональный заряд, семантическая плотность, "
                    "основные манипуляции и скрытые смыслы. "
                    "Без звёздочек, списков и маркеров. "
                    "Только факты и выводы."
                )},
                {"role": "user", "content": f"Текст: {text}\n\nАнализ: {analysis}"}
            ],
            temperature=0.3
        )
        return clean_text(response.choices[0].message.content)
    except Exception as e:
        return f"Ошибка: {e}"

def get_menu_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🔄 Увидеть иначе", callback_data="flip")],
        [InlineKeyboardButton("🔍 Слепое пятно", callback_data="blind")],
        [InlineKeyboardButton("📄 Экспорт отчёта", callback_data="export")],
        [InlineKeyboardButton("📤 Поделиться", url="https://t.me/istinomer_bot")]
    ])

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Я покажу тебе три параметра любого текста.\n\n"
        "Индекс манипуляции\n"
        "Эмоциональный заряд\n"
        "Семантическая плотность\n\n"
        "А если захочешь — я покажу, как те же факты звучат с другой стороны.\n\n"
        "Команды:\n"
        "/fact — факт дня о восприятии\n"
        "/history — твоя история анализов\n"
        "Просто отправь мне текст, ссылку или новость."
    )

async def fact_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    fact = random.choice(FACTS)
    await update.message.reply_text(f"🧠 {fact}")

async def history_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    history = user_history.get(user_id, [])
    if not history:
        await update.message.reply_text("У тебя пока нет сохранённых анализов.")
        return
    text = "📋 Твоя история анализов:\n\n"
    for i, entry in enumerate(history[-5:], 1):
        text += f"{i}. {entry[:100]}...\n"
    await update.message.reply_text(text)

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Отправь мне любой текст.\n"
        "Я покажу три параметра.\n"
        "Нажми «Увидеть иначе», чтобы посмотреть на него с другой стороны.\n"
        "/fact — факт дня\n"
        "/history — история анализов"
    )

async def donate_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Если тебе полезен Истиномер, ты можешь поддержать его развитие:\n\n"
        "💳 По ссылке: https://your.donate.link\n"
        "Или просто поделись ботом с друзьями. Спасибо 🙏"
    )

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    user_id = update.effective_user.id
    user_last_text[user_id] = text

    await update.message.reply_text("Анализирую...")

    analysis = analyze_text(text)

    if user_id not in user_history:
        user_history[user_id] = []
    user_history[user_id].append(f"Текст: {text[:50]}... | {analysis[:50]}...")

    await update.message.reply_text(analysis, reply_markup=get_menu_keyboard())

async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    user_id = update.effective_user.id
    text = user_last_text.get(user_id)

    if not text:
        await query.edit_message_text("Текст не найден. Отправь что-нибудь сначала.")
        return

    if query.data == "flip":
        await query.edit_message_text("Смотрю с другой стороны...")
        flipped = flip_text(text)
        await query.edit_message_text(flipped, reply_markup=get_menu_keyboard())

    elif query.data == "blind":
        await query.edit_message_text("Ищу, что ты мог упустить...")
        blind = blind_spot(text)
        await query.edit_message_text(f"🔍 Слепое пятно:\n\n{blind}", reply_markup=get_menu_keyboard())

    elif query.data == "export":
        await query.edit_message_text("Генерирую отчёт...")
        analysis = analyze_text(text)
        report = generate_report(text, analysis)
        await query.edit_message_text(f"📄 Отчёт:\n\n{report}", reply_markup=get_menu_keyboard())

def main():
    token = TELEGRAM_TOKEN
    request = HTTPXRequest()
    app = Application.builder().token(token).request(request).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("donate", donate_command))
    app.add_handler(CommandHandler("fact", fact_command))
    app.add_handler(CommandHandler("history", history_command))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    app.add_handler(CallbackQueryHandler(button_callback, pattern="flip|blind|export"))

    print("✅ Истиномер 2.0 запущен")
    app.run_polling()

if __name__ == "__main__":
    main()
