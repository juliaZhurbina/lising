"""
Точка входа в приложение
"""
import logging
import sys
from pathlib import Path

from config.settings import settings
from bot.telegram_bot import TelegramBot
from services.gigachat_service import GigaChatService
from services.database_manager import DatabaseManager

# Настройка логирования
logging.basicConfig(
    level=getattr(logging, settings.LOG_LEVEL),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('bot.log', encoding='utf-8')
    ]
)

logger = logging.getLogger(__name__)


def main():
    """Основная функция запуска приложения"""
    logger.info("=" * 50)
    logger.info("Запуск Telegram бота для работы с заявками")
    logger.info("=" * 50)
    
    # Проверка настроек
    if not settings.validate():
        logger.error("❌ Не все обязательные настройки заполнены!")
        logger.info("📝 Пожалуйста, заполните файл .env с необходимыми данными")
        logger.info("📄 Используйте .env.example как шаблон")
        return
    
    logger.info("✅ Все настройки загружены успешно")
    
    # Проверка существования файла базы данных
    db_path = settings.get_database_path()
    if not db_path.exists():
        logger.error(f"❌ Файл базы данных не найден: {db_path}")
        logger.info("📝 Убедитесь, что путь к файлу указан правильно в .env")
        return
    
    logger.info(f"✅ Файл базы данных найден: {db_path}")
    
    # Инициализация сервисов
    try:
        # Инициализация GigaChat
        gigachat_service = GigaChatService(
            auth_key=settings.GIGACHAT_AUTH_KEY,
            scope=settings.GIGACHAT_SCOPE,
            api_auth_url=settings.GIGACHAT_API_AUTH_URL,
            api_chat_url=settings.GIGACHAT_API_CHAT_URL
        )
        logger.info("✅ GigaChat сервис инициализирован")
        
        # Инициализация Database Manager
        database_manager = DatabaseManager(db_path)
        if database_manager.load_data():
            logger.info("✅ База данных загружена успешно")
        else:
            logger.error("❌ Ошибка при загрузке базы данных")
            return
        
        # Инициализация и запуск бота
        bot = TelegramBot(
            token=settings.TELEGRAM_BOT_TOKEN,
            gigachat_service=gigachat_service,
            database_manager=database_manager
        )
        bot.run()
    except KeyboardInterrupt:
        logger.info("Остановка бота по запросу пользователя")
    except Exception as e:
        logger.error(f"Критическая ошибка: {e}", exc_info=True)


if __name__ == "__main__":
    main()
