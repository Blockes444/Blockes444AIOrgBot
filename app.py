import os
import logging
import requests
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

# Загрузка переменных окружения
load_dotenv()

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

# Конфигурация DeepSeek
DEEPSEEK_API_KEY = os.getenv('DEEPSEEK_API_KEY')
TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
ADMIN_ID = os.getenv('ADMIN_ID')
BOT_NAME = os.getenv('BOT_NAME', 'BlockesAIBot')

async def deepseek_chat(message):
    """Функция для общения с DeepSeek API"""
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {DEEPSEEK_API_KEY}"
    }
    
    data = {
        "model": "deepseek-chat",
        "messages": [
            {"role": "system", "content": "Ты полезный помощник, который отвечает на вопросы на русском языке."},
            {"role": "user", "content": message}
        ],
        "max_tokens": 2000,
        "temperature": 0.7,
        "stream": False
    }
    
    try:
        response = requests.post(
            "https://api.deepseek.com/v1/chat/completions",
            headers=headers,
            json=data,
            timeout=30
        )
        response.raise_for_status()
        result = response.json()
        return result['choices'][0]['message']['content']
    except Exception as e:
        logging.error(f"DeepSeek API error: {e}")
        return None

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
        
        # Получаем ответ от DeepSeek
        ai_response = await deepseek_chat(user_message)
        
        if ai_response is None:
            await update.message.reply_text("❌ Ошибка подключения к AI. Попробуйте позже.")
            return
        
        # Удаляем сообщение "Думаю" и отправляем ответ
        await context.bot.delete_message(
            chat_id=chat_id,
            message_id=processing_message.message_id
        )
        
        # Разбиваем длинные ответы на части
        if len(ai_response) > 4000:
            for i in range(0, len(ai_response), 4000):
                await update.message.reply_text(ai_response[i:i+4000])
        else:
            await update.message.reply_text(ai_response)
        
    except Exception as e:
        logging.error(f"Error in GTP command: {e}")
        await update.message.reply_text("❌ Извините, произошла ошибка. Попробуйте позже.")

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды /start"""
    await update.message.reply_text(
        f'🤖 Привет! Я {BOT_NAME} - бот с AI.\n'
        'Используйте команду /GTP "ваш вопрос" для общения со мной.\n\n'
        'Пример: /GTP "Напиши рецепт пасты"'
    )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды /help"""
    help_text = f"""
🤖 **{BOT_NAME} - Команды бота:**

/GTP "ваш вопрос" - Задать вопрос AI
/help - Показать эту справку

**Примеры использования:**
/GTP "Напиши рецепт пасты карбонара"
/GTP "Объясни квантовую физику простыми словами"

⚡ **Powered by DeepSeek AI**
    """
    await update.message.reply_text(help_text)

def main():
    """Основная функция"""
    if not TELEGRAM_BOT_TOKEN or not DEEPSEEK_API_KEY:
        logging.error("Не установлены TELEGRAM_BOT_TOKEN или DEEPSEEK_API_KEY")
        return
    
    # Создание приложения
    application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()
    
    # Добавление обработчиков
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("gpt", gpt_command))
    application.add_handler(CommandHandler("GTP", gpt_command))
    application.add_handler(CommandHandler("help", help_command))
    
    # Запуск бота
    logging.info(f"🚀 {BOT_NAME} starting with DeepSeek...")
    application.run_polling(drop_pending_updates=True)

if __name__ == '__main__':
    main()
