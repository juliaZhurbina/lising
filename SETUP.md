# Инструкция по настройке проекта

## ✅ Что уже сделано

1. ✅ Создана структура проекта
2. ✅ Установлены все зависимости
3. ✅ Созданы базовые файлы и классы
4. ✅ Настроена система конфигурации

## 📋 Что нужно от вас

Для запуска бота необходимо заполнить файл `.env` с вашими данными.

### Шаг 1: Создайте файл .env

Скопируйте `.env.example` в `.env`:

```bash
copy .env.example .env
```

Или создайте файл `.env` вручную в корне проекта.

### Шаг 2: Получите токен Telegram бота

1. Откройте Telegram и найдите бота [@BotFather](https://t.me/BotFather)
2. Отправьте команду `/newbot`
3. Следуйте инструкциям для создания бота
4. Скопируйте полученный токен (выглядит как `123456789:ABCdefGHIjklMNOpqrsTUVwxyz`)

**Вставьте токен в `.env`:**
```
TELEGRAM_BOT_TOKEN=ваш_токен_здесь
```

### Шаг 3: Получите учетные данные GigaChat API

1. Перейдите на [GigaChat Developer Portal](https://developers.sber.ru/gigachat)
2. Зарегистрируйтесь или войдите в систему
3. Создайте приложение и получите:
   - **Client ID**
   - **Client Secret**

**Вставьте данные в `.env`:**
```
GIGACHAT_CLIENT_ID=ваш_client_id
GIGACHAT_CLIENT_SECRET=ваш_client_secret
GIGACHAT_SCOPE=GIGACHAT_API_PERS
```

### Шаг 4: Проверьте путь к базе данных

Убедитесь, что путь к Excel файлу указан правильно:

```
DATABASE_PATH=c:\Users\Admin\Downloads\Книга5.xlsx
```

Если файл находится в другом месте, укажите полный путь.

### Шаг 5: Настройте уровень логирования (опционально)

По умолчанию установлен `INFO`. Можно изменить на:
- `DEBUG` - подробные логи (для отладки)
- `INFO` - информационные сообщения (рекомендуется)
- `WARNING` - только предупреждения и ошибки
- `ERROR` - только ошибки

```
LOG_LEVEL=INFO
```

## 📝 Пример заполненного .env файла

```env
# Telegram Bot Token
TELEGRAM_BOT_TOKEN=123456789:ABCdefGHIjklMNOpqrsTUVwxyz

# GigaChat API Credentials
GIGACHAT_CLIENT_ID=abc123def456
GIGACHAT_CLIENT_SECRET=xyz789uvw012
GIGACHAT_SCOPE=GIGACHAT_API_PERS

# Path to Excel database file
DATABASE_PATH=c:\Users\Admin\Downloads\Книга5.xlsx

# Logging level
LOG_LEVEL=INFO
```

## 🚀 Запуск бота

После заполнения `.env` файла запустите:

```bash
python main.py
```

Бот проверит все настройки и запустится, если все данные корректны.

## ⚠️ Важно

- **НЕ коммитьте файл `.env` в git!** Он содержит секретные данные
- Файл `.env` уже добавлен в `.gitignore` (если используется git)
- Храните токены и секреты в безопасности

## 🆘 Если что-то не работает

1. Проверьте, что все поля в `.env` заполнены
2. Убедитесь, что путь к Excel файлу правильный
3. Проверьте логи в файле `bot.log` или в консоли
4. Убедитесь, что токены действительны и не истекли
