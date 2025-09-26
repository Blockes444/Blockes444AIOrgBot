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

# Конфигурация
TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
YANDEX_API_KEY = os.getenv('YANDEX_API_KEY')  # Новый ключ!
ADMIN_ID = os.getenv('ADMIN_ID')
BOT_NAME = os.getenv('BOT_NAME', 'BlockesAIBot')

# Детальная проверка переменных
logging.info("=== Yandex GPT Bot Starting ===")
logging.info(f"BOT_NAME: {BOT_NAME}")
logging.info(f"TELEGRAM_BOT_TOKEN: {'SET' if TELEGRAM_BOT_TOKEN else 'MISSING'}")
logging.info(f"YANDEX_API_KEY: {'SET' if YANDEX_API_KEY else 'MISSING'}")

async def yandex_gpt(message):
    """Функция для общения с Yandex GPT API"""
    try:
        logging.info(f"Sending request to Yandex GPT: {message[:50]}...")
        
        if not YANDEX_API_KEY:
            logging.error("YANDEX_API_KEY is missing!")
            return None

        headers = {
            "Authorization": f"Api-Key {YANDEX_API_KEY}",
            "Content-Type": "application/json"
        }
        
        data = {
            "modelUri": "gpt://b1gvmk9u7ea7lpg4g86r/yandexgpt/latest",
            "completionOptions": {
                "stream": False,
                "temperature": 0.6,
                "maxTokens": 1000
            },
            "messages": [
                {
                    "role": "user",
                    "text": message
                }
            ]
        }
        
        logging.info("Making request to Yandex GPT API...")
        
        response = requests.post(
            "https://llm.api.cloud.yandex.net/foundationModels/v1/completion",
            headers=headers,
            json=data,
            timeout=30
        )
        
        logging.info(f"Yandex GPT response status: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            if 'result' in result and 'alternatives' in result['result']:
                ai_response = result['result']['alternatives'][0]['message']['text']
                logging.info(f"Yandex GPT response: {len(ai_response)} characters")
                return ai_response
            else:
                logging.error("Unexpected response format")
                return None
        else:
            logging.error(f"Yandex GPT API error {response.status_code}: {response.text}")
            return None
            
    except requests.exceptions.Timeout:
        logging.error("Yandex GPT API timeout")
        return None
    except requests.exceptions.ConnectionError:
        logging.error("Yandex GPT API connection error")
        return None
    except Exception as e:
        logging.error(f"Yandex GPT API unexpected error: {str(e)}")
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
        if len(user_message) > 2000:
            await update.message.reply_text("❌ Сообщение слишком длинное. Максимум 2000 символов.")
            return
        
        # Логируем запрос
        logging.info(f"User request from {chat_id}: {user_message[:100]}...")
        
        # Отправляем сообщение о обработке
        processing_message = await update.message.reply_text("🤔 Думаю...")
        
        # Получаем ответ от Yandex GPT
        ai_response = await yandex_gpt(user_message)
        
        if ai_response is None:
            # Fallback ответ
            ai_response = f"🤖 Привет! Я получил ваш запрос: '{user_message}'\n\n" \
                         "В настоящее время настраиваю подключение к Yandex GPT. " \
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
        f'🤖 Привет! Я {BOT_NAME} - бот с Yandex GPT AI.\n'
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

⚡ **Powered by Yandex GPT**
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
    
    if not YANDEX_API_KEY:
        logging.error("❌ CRITICAL: YANDEX_API_KEY is not set!")
        logging.error("❌ Get your API key from: https://yandex.cloud/")
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
        logging.info(f"🚀 {BOT_NAME} starting with Yandex GPT API...")
        application.run_polling(
            drop_pending_updates=True,
            allowed_updates=Update.ALL_TYPES
        )
        
    except Exception as e:
        logging.error(f"Failed to start bot: {e}")

if __name__ == '__main__':
    main()
