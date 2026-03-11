"""
Сервис для работы с GigaChat API
"""
import logging
import requests
import base64
import uuid
from typing import Dict, Any, Optional
import json
from datetime import datetime, timedelta
import urllib3

# Отключаем предупреждения SSL для dev сервера
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

logger = logging.getLogger(__name__)


class GigaChatService:
    """Класс для работы с GigaChat API"""
    
    def __init__(self, auth_key: str, scope: str, api_auth_url: str, api_chat_url: str):
        """
        Инициализация сервиса GigaChat
        
        Args:
            auth_key: AUTH_KEY для GigaChat API (base64 encoded client_id:client_secret)
            scope: Scope для доступа к API
            api_auth_url: URL для получения токена доступа
            api_chat_url: URL для отправки запросов к чату
        """
        self.auth_key = auth_key
        self.scope = scope
        self.api_auth_url = api_auth_url
        self.api_chat_url = api_chat_url
        self._access_token: Optional[str] = None
        self._token_expires_at: Optional[datetime] = None
        
    def _get_access_token(self) -> str:
        """
        Получение токена доступа к GigaChat API
        
        Returns:
            Токен доступа
        """
        # Проверяем, есть ли валидный токен
        if self._access_token and self._token_expires_at:
            if datetime.now() < self._token_expires_at:
                return self._access_token
        
        try:
            # Получаем новый токен
            headers = {
                'Authorization': f'Basic {self.auth_key}',
                'RqUID': self._generate_rquid(),
                'Content-Type': 'application/x-www-form-urlencoded'
            }
            
            data = {
                'scope': self.scope
            }
            
            response = requests.post(
                self.api_auth_url,
                headers=headers,
                data=data,
                verify=False  # Отключаем проверку SSL для dev сервера
            )
            
            if response.status_code == 200:
                token_data = response.json()
                self._access_token = token_data.get('access_token')
                
                # Обрабатываем expires_at или expires_in
                expires_in = token_data.get('expires_in', 1800)  # По умолчанию 30 минут
                expires_at = token_data.get('expires_at')
                
                if expires_at:
                    # Если expires_at указан как timestamp
                    try:
                        if isinstance(expires_at, (int, float)):
                            # Unix timestamp в секундах или миллисекундах
                            if expires_at > 1e10:  # Если в миллисекундах
                                expires_at = expires_at / 1000
                            self._token_expires_at = datetime.fromtimestamp(expires_at)
                        else:
                            # Пробуем распарсить как строку
                            self._token_expires_at = datetime.now() + timedelta(seconds=expires_in)
                    except (ValueError, OSError) as e:
                        logger.warning(f"Ошибка при парсинге expires_at: {e}, используем expires_in")
                        self._token_expires_at = datetime.now() + timedelta(seconds=expires_in)
                else:
                    # Используем expires_in
                    self._token_expires_at = datetime.now() + timedelta(seconds=expires_in)
                
                logger.info("Токен доступа GigaChat получен успешно")
                return self._access_token
            elif response.status_code == 429:
                logger.error(f"Превышен лимит запросов к GigaChat API (429). Подождите немного.")
                raise Exception("Превышен лимит запросов к GigaChat API. Подождите немного перед повторной попыткой.")
            else:
                logger.error(f"Ошибка получения токена: {response.status_code} - {response.text}")
                raise Exception(f"Не удалось получить токен доступа: {response.status_code}")
                
        except Exception as e:
            logger.error(f"Ошибка при получении токена доступа: {e}")
            raise
    
    def _generate_rquid(self) -> str:
        """Генерация уникального идентификатора запроса"""
        return str(uuid.uuid4())
    
    def _chat_completion(self, messages: list, temperature: float = 0.7) -> str:
        """
        Отправка запроса к GigaChat API
        
        Args:
            messages: Список сообщений для чата
            temperature: Температура генерации (0-1)
            
        Returns:
            Ответ от модели
        """
        try:
            token = self._get_access_token()
            
            headers = {
                'Authorization': f'Bearer {token}',
                'Content-Type': 'application/json'
            }
            
            data = {
                'model': 'GigaChat',
                'messages': messages,
                'temperature': temperature
            }
            
            response = requests.post(
                self.api_chat_url,
                headers=headers,
                json=data,
                verify=False
            )
            
            if response.status_code == 200:
                result = response.json()
                return result.get('choices', [{}])[0].get('message', {}).get('content', '')
            else:
                logger.error(f"Ошибка запроса к GigaChat: {response.status_code} - {response.text}")
                return ""
                
        except Exception as e:
            logger.error(f"Ошибка при запросе к GigaChat: {e}")
            return ""
    
    def extract_intent(self, message: str) -> Dict[str, Any]:
        """
        Определение намерения пользователя из сообщения
        
        Args:
            message: Текстовое сообщение пользователя
            
        Returns:
            Словарь с информацией о намерении:
            {
                'intent': 'change_status' | 'search_application' | 'generate_context' | 'create_task',
                'confidence': float
            }
        """
        prompt = f"""Ты помощник для работы с заявками. Проанализируй запрос пользователя и определи его намерение.

Запрос: "{message}"

Определи одно из следующих намерений:
- search_application - если пользователь хочет найти информацию о заявке (слова: найди, найти, покажи, покажи информацию, какой статус)
- change_status - если пользователь хочет изменить статус заявки (слова: измени, обнови, поменяй статус)
- generate_context - если пользователь хочет получить контекст для звонка/встречи (слова: контекст, звонок, встреча, справка)
- create_task - если пользователь хочет создать задачу или напоминание (слова: создай задачу, напомни)
- get_help - если пользователь просит помощь или справку (слова: помощь, справка, что ты умеешь)
- unknown - если намерение не определено

ВАЖНО: Если в запросе есть ID заявки (формат Z25-XXXXXXX) и слова "найди", "найти", "покажи" - это search_application.

Ответь ТОЛЬКО в формате JSON, без дополнительного текста:
{{"intent": "search_application", "confidence": 0.95}}
"""
        
        messages = [
            {"role": "user", "content": prompt}
        ]
        
        try:
            response = self._chat_completion(messages, temperature=0.3)
            logger.debug(f"Ответ GigaChat для определения намерения: {response}")
            
            # Пытаемся распарсить JSON из ответа (несколько вариантов)
            import re
            
            # Вариант 1: Ищем полный JSON объект
            json_match = re.search(r'\{[^{}]*"intent"[^{}]*\}', response)
            if json_match:
                try:
                    result = json.loads(json_match.group())
                    logger.info(f"Определено намерение: {result.get('intent')}")
                    return result
                except json.JSONDecodeError:
                    pass
            
            # Вариант 2: Ищем просто значение intent в тексте
            intent_match = re.search(r'"intent"\s*:\s*"(\w+)"', response)
            if intent_match:
                intent_name = intent_match.group(1)
                logger.info(f"Определено намерение (из текста): {intent_name}")
                return {'intent': intent_name, 'confidence': 0.8}
            
            # Вариант 3: Ищем намерение без кавычек
            intent_match = re.search(r'intent["\s:]+(\w+)', response, re.IGNORECASE)
            if intent_match:
                intent_name = intent_match.group(1)
                logger.info(f"Определено намерение (без кавычек): {intent_name}")
                return {'intent': intent_name, 'confidence': 0.7}
            
            logger.warning(f"Не удалось распарсить JSON из ответа GigaChat. Ответ: {response}")
            return {'intent': 'unknown', 'confidence': 0.0}
        except Exception as e:
            logger.error(f"Ошибка при определении намерения: {e}", exc_info=True)
            return {'intent': 'unknown', 'confidence': 0.0}
    
    def extract_entities(self, message: str) -> Dict[str, Any]:
        """
        Извлечение сущностей из сообщения
        
        Args:
            message: Текстовое сообщение пользователя
            
        Returns:
            Словарь с извлеченными сущностями:
            {
                'app_id': str | None,
                'date': str | None,
                'action': str | None,
                'task_description': str | None,
                ...
            }
        """
        prompt = f"""Извлеки из запроса пользователя следующие сущности.

Запрос: "{message}"

Извлеки:
- app_id: ID заявки (формат: Z25-XXXXXXX, Z25-1234567 или похожий, начинается с Z и содержит дефис)
- date: Дата в формате YYYY-MM-DD (если упоминается: "15 ноября", "15.11", "15/11")
- action: Действие (изменить, найти, создать и т.д.)
- task_description: Описание задачи (если есть)
- time: Время в формате HH:MM (если есть)

ВАЖНО: Если видишь ID заявки в формате Z25-XXXXXXX, обязательно извлеки его в app_id.

Ответь ТОЛЬКО в формате JSON, без дополнительного текста, используй null для отсутствующих значений:
{{"app_id": "Z25-1234567", "date": null, "action": null, "task_description": null, "time": null}}
"""
        
        messages = [
            {"role": "user", "content": prompt}
        ]
        
        try:
            response = self._chat_completion(messages, temperature=0.3)
            logger.debug(f"Ответ GigaChat для извлечения сущностей: {response}")
            
            import re
            
            # Пытаемся найти JSON объект
            json_match = re.search(r'\{[^{}]*"app_id"[^{}]*\}', response)
            if json_match:
                try:
                    result = json.loads(json_match.group())
                    logger.info(f"Извлечены сущности: {result}")
                    return result
                except json.JSONDecodeError:
                    pass
            
            # Fallback: ищем ID заявки напрямую в тексте
            app_id_pattern = r'Z\d{2}-\d{7}'
            app_id_match = re.search(app_id_pattern, response.upper())
            if app_id_match:
                app_id = app_id_match.group(0)
                logger.info(f"Найден ID заявки в ответе (fallback): {app_id}")
                return {'app_id': app_id}
            
            # Ищем ID в исходном сообщении
            app_id_match = re.search(app_id_pattern, message.upper())
            if app_id_match:
                app_id = app_id_match.group(0)
                logger.info(f"Найден ID заявки в исходном сообщении (fallback): {app_id}")
                return {'app_id': app_id}
            
            logger.warning(f"Не удалось распарсить JSON из ответа GigaChat. Ответ: {response}")
            return {}
        except Exception as e:
            logger.error(f"Ошибка при извлечении сущностей: {e}", exc_info=True)
            # Fallback: ищем ID в исходном сообщении
            import re
            app_id_pattern = r'Z\d{2}-\d{7}'
            app_id_match = re.search(app_id_pattern, message.upper())
            if app_id_match:
                app_id = app_id_match.group(0)
                logger.info(f"Найден ID заявки в исходном сообщении (fallback после ошибки): {app_id}")
                return {'app_id': app_id}
            return {}
    
    def generate_confirmation_message(self, app_id: str, old_date: str, new_date: str) -> str:
        """
        Генерация сообщения подтверждения изменения статуса
        
        Args:
            app_id: ID заявки
            old_date: Старая дата
            new_date: Новая дата
            
        Returns:
            Текст сообщения подтверждения
        """
        prompt = f"""Сгенерируй понятное сообщение подтверждения для пользователя:

ID заявки: {app_id}
Текущая дата статуса: {old_date}
Новая дата статуса: {new_date}

Сообщение должно быть вежливым, понятным и заканчиваться вопросом о подтверждении.
Ответь ТОЛЬКО текстом сообщения, без дополнительных пояснений.
"""
        
        messages = [
            {"role": "user", "content": prompt}
        ]
        
        try:
            response = self._chat_completion(messages, temperature=0.7)
            return response.strip() if response else f"Дата изменения статуса заявки {app_id} изменена с {old_date} на {new_date}. Подтвердить изменение?"
        except Exception as e:
            logger.error(f"Ошибка при генерации сообщения подтверждения: {e}")
            return f"Дата изменения статуса заявки {app_id} изменена с {old_date} на {new_date}. Подтвердить изменение?"
    
    def generate_call_context(self, application_data: Dict[str, Any]) -> str:
        """
        Генерация контекста для звонка/встречи
        
        Args:
            application_data: Данные заявки
            
        Returns:
            Структурированный контекст для звонка
        """
        # Формируем структурированные данные для промпта
        # Фильтруем пустые значения и форматируем данные
        filtered_data = {}
        for k, v in application_data.items():
            if v is not None and str(v) != 'nan' and str(v).strip():
                # Ограничиваем длину значений для промпта
                value_str = str(v)
                if len(value_str) > 500:
                    value_str = value_str[:500] + "..."
                filtered_data[k] = value_str
        
        # Формируем структурированное представление данных
        app_info_lines = []
        for key, value in filtered_data.items():
            app_info_lines.append(f"{key}: {value}")
        
        app_info = "\n".join(app_info_lines)
        
        logger.info(f"Генерация контекста для заявки. Количество полей: {len(filtered_data)}")
        logger.debug(f"Данные заявки: {app_info[:500]}...")
        
        prompt = f"""Ты помощник для сотрудника, который готовится к звонку с клиентом. Проанализируй данные заявки и создай полезный контекст для звонка.

Данные заявки:
{app_info}

Создай структурированный контекст для звонка, который поможет сотруднику эффективно общаться с клиентом. 

ВАЖНО:
- Проанализируй ВСЕ данные из заявки
- Выдели ключевую информацию о клиенте, автомобиле, сумме сделки
- Обрати внимание на статус заявки и историю изменений
- Предложи конкретные темы для обсуждения
- Укажи важные моменты, на которые нужно обратить внимание

Формат ответа:

📞 Контекст для звонка

🎯 Цель звонка:
[Сформулируй основную цель звонка на основе данных заявки]

📋 Ключевая информация о заявке:
- [Основные факты: клиент, автомобиль, сумма, статус]
- [Важные детали из данных заявки]

📝 Что важно знать:
- [Ключевые моменты из истории и статуса заявки]
- [Особенности этой заявки]

⚠️ На что обратить внимание:
- [Важные нюансы, которые нужно учесть при разговоре]

💡 Рекомендации для разговора:
- [Конкретные вопросы, которые стоит задать]
- [Темы для обсуждения]
- [Что уточнить у клиента]

Будь конкретным и полезным. Используй информацию из всех полей заявки.
"""
        
        messages = [
            {"role": "user", "content": prompt}
        ]
        
        try:
            logger.info("Отправка запроса к GigaChat для генерации контекста...")
            response = self._chat_completion(messages, temperature=0.7)
            logger.debug(f"Ответ GigaChat для контекста: {response[:200] if response else 'пустой ответ'}...")
            
            if response and response.strip():
                cleaned_response = response.strip()
                logger.info(f"Контекст для звонка сгенерирован успешно (длина: {len(cleaned_response)} символов)")
                return cleaned_response
            else:
                logger.warning("GigaChat вернул пустой ответ, формирую контекст вручную")
                # Формируем базовый контекст вручную, если GigaChat не ответил
                return self._generate_fallback_context(filtered_data)
        except Exception as e:
            logger.error(f"Ошибка при генерации контекста: {e}", exc_info=True)
            # Формируем базовый контекст вручную при ошибке
            return self._generate_fallback_context(filtered_data)
    
    def _generate_fallback_context(self, application_data: Dict[str, Any]) -> str:
        """Генерация базового контекста вручную, если GigaChat не ответил"""
        lines = ["📞 Контекст для звонка\n"]
        
        # Извлекаем ключевую информацию
        id_field = None
        client_field = None
        car_field = None
        amount_field = None
        status_field = None
        date_field = None
        
        for key, value in application_data.items():
            key_lower = str(key).lower()
            if 'номер' in key_lower or 'id' in key_lower or 'заявк' in key_lower:
                id_field = (key, value)
            elif 'клиент' in key_lower or 'покупатель' in key_lower:
                client_field = (key, value)
            elif 'автомобиль' in key_lower or 'машин' in key_lower or 'модель' in key_lower:
                car_field = (key, value)
            elif 'сумм' in key_lower or 'цена' in key_lower or 'стоимость' in key_lower:
                amount_field = (key, value)
            elif 'статус' in key_lower or 'состояние' in key_lower:
                status_field = (key, value)
            elif 'дата' in key_lower:
                date_field = (key, value)
        
        lines.append("🎯 Цель звонка:")
        lines.append("Обсудить детали заявки и уточнить потребности клиента\n")
        
        lines.append("📋 Ключевая информация:")
        if id_field:
            lines.append(f"- Номер заявки: {id_field[1]}")
        if client_field:
            lines.append(f"- Клиент: {client_field[1]}")
        if car_field:
            lines.append(f"- Автомобиль: {car_field[1]}")
        if amount_field:
            lines.append(f"- Сумма: {amount_field[1]}")
        if status_field:
            lines.append(f"- Статус: {status_field[1]}")
        if date_field:
            lines.append(f"- Дата: {date_field[1]}")
        
        lines.append("\n💡 Рекомендации:")
        lines.append("- Уточнить готовность клиента к оформлению")
        lines.append("- Обсудить условия сделки")
        lines.append("- Ответить на вопросы клиента")
        
        return "\n".join(lines)
