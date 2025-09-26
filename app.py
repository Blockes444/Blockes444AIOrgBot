import os
import logging
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes
import openai

# Загрузка переменных окружения
load_dotenv()

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

# Конфигурация
TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
ADMIN_ID = os.getenv('ADMIN_ID')
BOT_NAME = os.getenv('BOT_NAME', 'BlockesAIBot')

# Инициализация OpenAI
openai.api_key = OPENAI_API_KEY

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды /start"""
    await update.message.reply_text(
        f'🤖 Привет! Я {BOT_NAME} - бот с GPT.\n'
        'Используйте команду /GTP "ваш вопрос" для общения со мной.\n\n'
        'Пример: /GTP "Напиши рецепт пасты"'
    )

async def gpt_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды /GTP"""
    try:
        # Проверяем разрешена ли группа
        chat_id = update.effective_chat.id
        allowed_groups = os.getenv('ALLOWED_GROUP_IDS', 'all')
        
        if allowed_groups != 'all' and str(chat_id) not in allowed_groups.split(','):
            await update.message.reply_text("❌ Бот не работает в этой группе.")
            return
        
        # Получаем текст после команды
        user_message = ' '.join(context.args)
        
        if not user_message:
            await update.message.reply_text(
                'Пожалуйста, напишите сообщение после команды /GTP.\n'
                'Пример: /GTP "Привет, как дела?"'
            )
            return
        
        # Удаляем кавычки если они есть
        if user_message.startswith('"') and user_message.endswith('"'):
            user_message = user_message[1:-1]
        
        # Проверяем длину сообщения
        if len(user_message) > 1000:
            await update.message.reply_text("❌ Сообщение слишком длинное. Максимум 1000 символов.")
            return
        
        # Отправляем сообщение о обработке
        processing_message = await update.message.reply_text("🤔 Думаю...")
        
        # Генерируем ответ с помощью GPT
        response = openai.chat.completions.create(
            model=os.getenv('GPT_MODEL', 'gpt-3.5-turbo'),
            messages=[
                {"role": "system", "content": "Ты полезный помощник, который отвечает на вопросы."},
                {"role": "user", "content": user_message}
            ],
            max_tokens=int(os.getenv('GPT_MAX_TOKENS', 500)),
            temperature=float(os.getenv('GPT_TEMPERATURE', 0.7))
        )
        
        gpt_response = response.choices[0].message.content
        
        # Удаляем сообщение "Думаю" и отправляем ответ
        await context.bot.delete_message(
            chat_id=chat_id,
            message_id=processing_message.message_id
        )
        
        # Разбиваем длинные ответы на части (ограничение Telegram - 4096 символов)
        if len(gpt_response) > 4000:
            for i in range(0, len(gpt_response), 4000):
                await update.message.reply_text(gpt_response[i:i+4000])
        else:
            await update.message.reply_text(gpt_response)
        
    except openai.APIError as e:
        logging.error(f"OpenAI API error: {e}")
        await update.message.reply_text("❌ Ошибка API OpenAI. Проверьте баланс и настройки.")
    except Exception as e:
        logging.error(f"Error in GPT command: {e}")
        await update.message.reply_text("❌ Извините, произошла ошибка. Попробуйте позже.")

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды /help"""
    help_text = f"""
🤖 **{BOT_NAME} - Команды бота:**

/GTP "ваш вопрос" - Задать вопрос GPT
/help - Показать эту справку

**Примеры использования:**
/GTP "Напиши рецепт пасты карбонара"
/GTP "Объясни квантовую физику простыми словами"
/GTP "Помоги написать код на Python"

⚡ **Бот работает в группе: {os.getenv('ALLOWED_GROUP_IDS', 'Все группы')}**
    """
    await update.message.reply_text(help_text)

async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик ошибок"""
    logging.error(f"Update {update} caused error {context.error}")

def main():
    """Основная функция"""
    # Проверка наличия токенов
    if not TELEGRAM_BOT_TOKEN or not OPENAI_API_KEY:
        logging.error("Не установлены TELEGRAM_BOT_TOKEN или OPENAI_API_KEY")
        return
    
    # Создание приложения
    application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()
    
    # Добавление обработчиков
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("gpt", gpt_command))
    application.add_handler(CommandHandler("GTP", gpt_command))
    application.add_handler(CommandHandler("help", help_command))
    
    # Обработчик ошибок
    application.add_error_handler(error_handler)
    
    # Запуск бота
    logging.info(f"🚀 {BOT_NAME} starting...")
    
    # Упрощенный запуск - всегда используем polling
    application.run_polling(
        drop_pending_updates=True,
        allowed_updates=Update.ALL_TYPES
    )

if __name__ == '__main__':
    main()