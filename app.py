import os
import logging
import requests
import json
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

# Детальная проверка переменных при запуске
logging.info("=== DeepSeek Bot Starting ===")
logging.info(f"BOT_NAME: {BOT_NAME}")
logging.info(f"TELEGRAM_BOT_TOKEN: {'SET' if TELEGRAM_BOT_TOKEN else 'MISSING'}")
logging.info(f"DEEPSEEK_API_KEY: {'SET' if DEEPSEEK_API_KEY else 'MISSING'}")

async def deepseek_chat(message):
    """Диагностическая версия с подробным логированием"""
    try:
        logging.info(f"=== DEEPSEEK API DIAGNOSTICS ===")
        logging.info(f"API Key: {DEEPSEEK_API_KEY[:10]}...{DEEPSEEK_API_KEY[-10:]}")
        logging.info(f"Message: {message}")
        
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {DEEPSEEK_API_KEY}",
            "User-Agent": "Telegram-Bot/1.0"
        }
        
        data = {
            "model": "deepseek-chat",
            "messages": [
                {"role": "user", "content": "Привет! Ответь коротко."}
            ],
            "max_tokens": 50,
            "temperature": 0.7
        }
        
        logging.info("Sending test request to DeepSeek...")
        
        response = requests.post(
            "https://api.deepseek.com/v1/chat/completions",
            headers=headers,
            json=data,
            timeout=30
        )
        
        logging.info(f"=== RESPONSE DETAILS ===")
        logging.info(f"Status Code: {response.status_code}")
        logging.info(f"Response Headers: {dict(response.headers)}")
        logging.info(f"Response Text: {response.text}")
        
        if response.status_code == 200:
            result = response.json()
            logging.info(f"Full Response: {json.dumps(result, ensure_ascii=False)}")
            return "✅ DeepSeek API работает! Тестовый запрос успешен."
        else:
            return f"❌ Ошибка DeepSeek API: {response.status_code} - {response.text}"
            
    except Exception as e:
        logging.error(f"Exception: {str(e)}")
        return f"❌ Исключение: {str(e)}"
        
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
        if len(user_message) > 2000:
            await update.message.reply_text("❌ Сообщение слишком длинное. Максимум 2000 символов.")
            return
        
        # Логируем запрос
        logging.info(f"User request from {chat_id}: {user_message[:100]}...")
        
        # Отправляем сообщение о обработке
        processing_message = await update.message.reply_text("🤔 Думаю...")
        
        # Получаем ответ от DeepSeek
        ai_response = await deepseek_chat(user_message)
        
        if ai_response is None:
            # Fallback ответ
            ai_response = f"🤖 Привет! Я получил ваш запрос: '{user_message}'\n\n" \
                         "В настоящее время настраиваю подключение к DeepSeek AI. " \
                         "Попробуйте еще раз через минуту!"
        
        # Удаляем сообщение "Думаю" и отправляем ответ
        try:
            await context.bot.delete_message(
                chat_id=chat_id,
                message_id=processing_message.message_id
            )
        except:
            pass  # Игнорируем ошибки удаления сообщения
        
        # Разбиваем длинные ответы на части
        if len(ai_response) > 4000:
            for i in range(0, len(ai_response), 4000):
                await update.message.reply_text(ai_response[i:i+4000])
        else:
            await update.message.reply_text(ai_response)
        
        logging.info("Response sent successfully")
        
    except Exception as e:
        logging.error(f"Error in GTP command: {e}")
        await update.message.reply_text("❌ Извините, произошла ошибка. Попробуйте позже.")

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды /start"""
    await update.message.reply_text(
        f'🤖 Привет! Я {BOT_NAME} - бот с DeepSeek AI.\n'
        'Используйте команду /GTP "ваш вопрос" для общения со мной.\n\n'
        'Пример: /GTP "Напиши рецепт пасты"\n'
        'Пример: /GTP "Объясни квантовую физику"'
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
/GTP "Помоги написать код на Python"

⚡ **Powered by DeepSeek AI**
    """
    await update.message.reply_text(help_text)

async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик ошибок"""
    logging.error(f"Update {update} caused error {context.error}")

def main():
    """Основная функция"""
    # Проверка наличия токенов
    if not TELEGRAM_BOT_TOKEN:
        logging.error("❌ CRITICAL: TELEGRAM_BOT_TOKEN is not set!")
        return
    
    if not DEEPSEEK_API_KEY:
        logging.error("❌ CRITICAL: DEEPSEEK_API_KEY is not set!")
        logging.error("❌ Get your API key from: https://platform.deepseek.com/api_keys")
        return
    
    logging.info("✅ All environment variables are set correctly")
    
    try:
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
        logging.info(f"🚀 {BOT_NAME} starting with DeepSeek API...")
        application.run_polling(
            drop_pending_updates=True,
            allowed_updates=Update.ALL_TYPES
        )
        
    except Exception as e:
        logging.error(f"Failed to start bot: {e}")

if __name__ == '__main__':
    main()

