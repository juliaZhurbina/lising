"""
Настройки приложения
Загружает конфигурацию из переменных окружения
"""
import os
from pathlib import Path
from dotenv import load_dotenv

# Загружаем переменные окружения из .env файла
env_path = Path(__file__).parent.parent / '.env'
load_dotenv(dotenv_path=env_path)


class Settings:
    """Класс для хранения настроек приложения"""
    
    # Telegram Bot
    TELEGRAM_BOT_TOKEN: str = os.getenv('TELEGRAM_BOT_TOKEN', '')
    
    # GigaChat API
    GIGACHAT_AUTH_KEY: str = os.getenv('GIGACHAT_AUTH_KEY', '')
    GIGACHAT_SCOPE: str = os.getenv('GIGACHAT_SCOPE', 'GIGACHAT_API_PERS')
    GIGACHAT_API_AUTH_URL: str = os.getenv('GIGACHAT_API_AUTH_URL', 'https://ngw.devices.sberbank.ru:9443/api/v2/oauth')
    GIGACHAT_API_CHAT_URL: str = os.getenv('GIGACHAT_API_CHAT_URL', 'https://gigachat.devices.sberbank.ru/api/v1/chat/completions')
    
    # База данных
    DATABASE_PATH: str = os.getenv('DATABASE_PATH', '')
    
    # Логирование
    LOG_LEVEL: str = os.getenv('LOG_LEVEL', 'INFO')
    
    @classmethod
    def validate(cls) -> bool:
        """Проверка наличия обязательных настроек"""
        required_settings = [
            ('TELEGRAM_BOT_TOKEN', cls.TELEGRAM_BOT_TOKEN),
            ('GIGACHAT_AUTH_KEY', cls.GIGACHAT_AUTH_KEY),
            ('DATABASE_PATH', cls.DATABASE_PATH),
        ]
        
        missing = []
        for name, value in required_settings:
            if not value:
                missing.append(name)
        
        if missing:
            print(f"⚠️  Отсутствуют обязательные настройки: {', '.join(missing)}")
            print(f"📝 Проверьте файл .env")
            return False
        
        return True
    
    @classmethod
    def get_database_path(cls) -> Path:
        """Получить путь к базе данных как Path объект"""
        return Path(cls.DATABASE_PATH)


# Создаем экземпляр настроек
settings = Settings()
