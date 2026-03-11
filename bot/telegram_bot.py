"""
Основной класс Telegram бота
"""
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes
from typing import Dict, Any, Optional

from services.gigachat_service import GigaChatService
from services.database_manager import DatabaseManager
from config.settings import settings
from utils.date_utils import normalize_date, format_date_for_display

logger = logging.getLogger(__name__)


class TelegramBot:
    """Класс для работы с Telegram ботом"""
    
    def __init__(self, token: str, gigachat_service: GigaChatService, database_manager: DatabaseManager):
        """
        Инициализация бота
        
        Args:
            token: Токен Telegram бота
            gigachat_service: Сервис для работы с GigaChat
            database_manager: Менеджер базы данных
        """
        self.token = token
        self.gigachat_service = gigachat_service
        self.database_manager = database_manager
        self.application = None
        # Хранилище для ожидающих подтверждения операций
        self.pending_operations: Dict[int, Dict[str, Any]] = {}
        
    def initialize(self):
        """Инициализация приложения бота"""
        try:
            self.application = Application.builder().token(self.token).build()
            self._register_handlers()
            logger.info("Telegram бот инициализирован")
        except Exception as e:
            logger.error(f"Ошибка инициализации бота: {e}")
            raise
    
    def _register_handlers(self):
        """Регистрация обработчиков команд и сообщений"""
        # Команды
        self.application.add_handler(CommandHandler("start", self._handle_start))
        self.application.add_handler(CommandHandler("help", self._handle_help))
        self.application.add_handler(CommandHandler("tasks", self._handle_tasks))
        
        # Обработчик текстовых сообщений
        self.application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self._handle_message))
        
        # Обработчик callback-кнопок
        self.application.add_handler(CallbackQueryHandler(self._handle_callback))
    
    async def _handle_start(self, update: Update, context):
        """Обработчик команды /start"""
        welcome_message = """
👋 Привет! Я бот для работы с заявками.

Я умею:
• Искать информацию по заявкам
• Изменять статусы заявок
• Генерировать контекст для звонков
• Создавать задачи и напоминания

Используйте /help для получения справки.

Попробуйте: "найди заявку Z25-1869607"
        """
        await update.message.reply_text(welcome_message, reply_markup=self._create_main_menu_keyboard())
    
    async def _handle_help(self, update: Update, context):
        """Обработчик команды /help"""
        help_message = """
📖 Справка по использованию бота

Команды:
/start - Начать работу с ботом
/help - Показать эту справку
/tasks - Список ваших задач

Примеры запросов:
• "найди заявку Z25-1869607"
• "измени статус заявки Z12345 на 15 ноября"
• "подготовь контекст для звонка по заявке Z12345"
• "создай задачу позвонить клиенту завтра в 14:00"

💡 Используйте кнопки навигации для быстрого доступа к функциям.
        """
        await update.message.reply_text(help_message, reply_markup=self._create_main_menu_keyboard())
    
    async def _handle_tasks(self, update: Update, context):
        """Обработчик команды /tasks"""
        # TODO: Реализовать получение списка задач
        await update.message.reply_text("📋 Список задач будет реализован")
    
    async def _handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик текстовых сообщений"""
        message_text = update.message.text
        user_id = update.effective_user.id
        logger.info(f"Получено сообщение от {user_id}: {message_text}")
        
        # Показываем индикатор печати
        await context.bot.send_chat_action(chat_id=update.effective_chat.id, action="typing")
        
        try:
            # Определяем намерение пользователя
            intent_result = self.gigachat_service.extract_intent(message_text)
            intent = intent_result.get('intent', 'unknown')
            
            logger.info(f"Определено намерение: {intent}")
            
            # Извлекаем сущности
            entities = self.gigachat_service.extract_entities(message_text)
            logger.info(f"Извлечены сущности: {entities}")
            
            # Fallback: если намерение не определено, но есть ID заявки в тексте или сущностях
            if intent == 'unknown':
                # Пытаемся найти ID заявки в тексте напрямую
                import re
                app_id_pattern = r'Z\d{2}-\d{7}'
                app_id_match = re.search(app_id_pattern, message_text.upper())
                
                if app_id_match:
                    app_id = app_id_match.group(0)
                    logger.info(f"Найден ID заявки в тексте (fallback): {app_id}")
                    entities['app_id'] = app_id
                    
                    # Определяем намерение по ключевым словам
                    message_lower = message_text.lower()
                    if any(word in message_lower for word in ['найди', 'найти', 'покажи', 'показать', 'информация', 'заявк']):
                        intent = 'search_application'
                    elif any(word in message_lower for word in ['измени', 'изменить', 'обнови', 'обновить', 'поменяй', 'поменять', 'статус']):
                        intent = 'change_status'
                    elif any(word in message_lower for word in ['контекст', 'звонок', 'встреч', 'справка']):
                        intent = 'generate_context'
                    else:
                        # По умолчанию считаем поиском, если есть ID
                        intent = 'search_application'
            
            # Обрабатываем в зависимости от намерения
            if intent == 'search_application':
                await self._handle_search(update, context, entities)
            elif intent == 'change_status':
                await self._handle_change_status(update, context, entities)
            elif intent == 'generate_context':
                await self._handle_generate_context(update, context, entities)
            elif intent == 'create_task':
                await self._handle_create_task(update, context, entities)
            elif intent == 'get_help':
                await self._handle_help(update, context)
            else:
                await update.message.reply_text(
                    "Извините, я не понял ваш запрос. Попробуйте переформулировать или используйте /help для справки.",
                    reply_markup=self._create_main_menu_keyboard()
                )
                
        except Exception as e:
            logger.error(f"Ошибка при обработке сообщения: {e}", exc_info=True)
            error_message = "Произошла ошибка при обработке вашего запроса."
            
            # Специальная обработка ошибки лимита запросов
            if "429" in str(e) or "лимит" in str(e).lower():
                error_message = "⚠️ Превышен лимит запросов к GigaChat API. Подождите немного и попробуйте снова."
            
            await update.message.reply_text(
                error_message,
                reply_markup=self._create_main_menu_keyboard()
            )
    
    async def _handle_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик callback-кнопок"""
        query = update.callback_query
        await query.answer()
        
        user_id = update.effective_user.id
        callback_data = query.data
        
        try:
            if callback_data.startswith('confirm_'):
                # Подтверждение операции
                operation_id = callback_data.replace('confirm_', '')
                await self._handle_confirmation(query, context, operation_id, user_id)
            elif callback_data.startswith('cancel_'):
                # Отмена операции
                operation_id = callback_data.replace('cancel_', '')
                await self._handle_cancellation(query, context, operation_id)
            elif callback_data.startswith('context_'):
                # Показать контекст для заявки
                app_id = callback_data.replace('context_', '')
                logger.info(f"Обработка callback context_ для заявки: {app_id}")
                await self._show_context_for_callback(query, context, app_id)
            elif callback_data.startswith('status_'):
                # Изменение статуса через кнопку
                app_id = callback_data.replace('status_', '')
                logger.info(f"Обработка callback status_ для заявки: {app_id}")
                await query.answer("Отправьте сообщение для изменения статуса")
                await query.message.reply_text(
                    f"Для изменения статуса заявки {app_id} отправьте сообщение:\n"
                    f"'измени статус заявки {app_id} на [дата]'\n\n"
                    f"Например: 'измени статус заявки {app_id} на 15 ноября'",
                    reply_markup=self._create_navigation_keyboard(app_id)
                )
            elif callback_data.startswith('show_'):
                # Показать информацию о заявке
                app_id = callback_data.replace('show_', '')
                logger.info(f"Обработка callback show_ для заявки: {app_id}")
                await query.answer("Загружаю информацию о заявке...")
                app_data = self.database_manager.find_application(app_id)
                if app_data:
                    message = self._format_application_info(app_data)
                    await query.message.reply_text(message, reply_markup=self._create_navigation_keyboard(app_id), parse_mode='HTML')
                else:
                    await query.message.reply_text(f"❌ Заявка {app_id} не найдена.", reply_markup=self._create_navigation_keyboard())
            elif callback_data == 'search_new':
                # Новый поиск
                await query.answer("Введите ID заявки для поиска")
                await query.message.reply_text(
                    "🔍 Введите ID заявки для поиска:\n\n"
                    "Например: 'найди заявку Z25-1869607' или просто 'Z25-1869607'",
                    reply_markup=self._create_main_menu_keyboard()
                )
            elif callback_data == 'main_menu':
                # Главное меню
                await query.answer("Главное меню")
                await query.message.reply_text(
                    "🏠 Главное меню\n\n"
                    "Выберите действие или отправьте запрос:\n"
                    "• Найти заявку\n"
                    "• Изменить статус\n"
                    "• Сгенерировать контекст\n\n"
                    "Используйте /help для справки",
                    reply_markup=self._create_main_menu_keyboard()
                )
            elif callback_data == 'help_menu':
                # Помощь
                await query.answer("Справка")
                await self._handle_help(query.message, context)
            elif callback_data.startswith('task_'):
                # Действия с задачами
                await query.answer("Управление задачами")
                await query.message.reply_text(
                    "Управление задачами будет реализовано в следующей версии.",
                    reply_markup=self._create_main_menu_keyboard()
                )
            else:
                await query.answer("Неизвестная операция")
                await query.message.reply_text(
                    "Неизвестная операция",
                    reply_markup=self._create_main_menu_keyboard()
                )
        except Exception as e:
            logger.error(f"Ошибка при обработке callback: {e}", exc_info=True)
            await query.answer("Произошла ошибка")
            await query.message.reply_text(
                "Произошла ошибка. Попробуйте позже.",
                reply_markup=self._create_main_menu_keyboard()
            )
    
    async def _handle_search(self, update: Update, context: ContextTypes.DEFAULT_TYPE, entities: Dict[str, Any]):
        """Обработка поиска заявки"""
        app_id = entities.get('app_id')
        
        if not app_id:
            await update.message.reply_text(
                "Не удалось найти ID заявки в вашем запросе. Попробуйте указать ID явно, например: 'найди заявку Z25-1869607'",
                reply_markup=self._create_navigation_keyboard()
            )
            return
        
        # Ищем заявку в базе данных
        app_data = self.database_manager.find_application(app_id)
        
        if not app_data:
            await update.message.reply_text(
                f"❌ Заявка {app_id} не найдена в базе данных.",
                reply_markup=self._create_navigation_keyboard()
            )
            return
        
        # Форматируем информацию о заявке
        message = self._format_application_info(app_data)
        
        # Создаем кнопки навигации с действиями для этой заявки
        reply_markup = self._create_navigation_keyboard(app_id)
        
        logger.info(f"Отправка сообщения с кнопками для заявки {app_id}")
        
        try:
            # Пробуем сначала с HTML
            sent_message = await update.message.reply_text(message, reply_markup=reply_markup, parse_mode='HTML')
            logger.info(f"Сообщение с кнопками отправлено успешно (message_id: {sent_message.message_id})")
        except Exception as e:
            logger.error(f"Ошибка при отправке сообщения с кнопками (HTML): {e}")
            # Пробуем без HTML форматирования
            try:
                # Убираем HTML теги для простого текста
                simple_message = message.replace('<b>', '').replace('</b>', '').replace('<i>', '').replace('</i>', '')
                sent_message = await update.message.reply_text(simple_message, reply_markup=reply_markup)
                logger.info(f"Сообщение с кнопками отправлено без HTML (message_id: {sent_message.message_id})")
            except Exception as e2:
                logger.error(f"Ошибка при отправке сообщения с кнопками (без HTML): {e2}")
                # Последняя попытка - просто текст с кнопками
                try:
                    sent_message = await update.message.reply_text(message, reply_markup=reply_markup)
                    logger.info(f"Сообщение с кнопками отправлено (простой текст)")
                except Exception as e3:
                    logger.error(f"Критическая ошибка при отправке: {e3}")
                    await update.message.reply_text("Ошибка при отправке сообщения. Попробуйте еще раз.")
    
    async def _handle_change_status(self, update: Update, context: ContextTypes.DEFAULT_TYPE, entities: Dict[str, Any]):
        """Обработка изменения статуса"""
        app_id = entities.get('app_id')
        new_date = entities.get('date')
        
        if not app_id:
            await update.message.reply_text(
                "Не удалось найти ID заявки. Укажите ID явно, например: 'измени статус заявки Z25-1869607 на 15 ноября'",
                reply_markup=self._create_navigation_keyboard()
            )
            return
        
        if not new_date:
            await update.message.reply_text(
                "Не удалось найти дату в вашем запросе. Укажите дату, например: 'на 15 ноября' или 'на 15.11'",
                reply_markup=self._create_navigation_keyboard()
            )
            return
        
        # Находим заявку
        app_data = self.database_manager.find_application(app_id)
        if not app_data:
            await update.message.reply_text(
                f"❌ Заявка {app_id} не найдена.",
                reply_markup=self._create_navigation_keyboard()
            )
            return
        
        # Получаем текущую дату статуса
        # Ищем колонки с датами
        date_columns = [col for col in app_data.keys() if 'дата' in str(col).lower() or 'date' in str(col).lower()]
        old_date = "текущая дата"
        if date_columns and app_data.get(date_columns[0]):
            old_date = str(app_data[date_columns[0]])
        
        # Нормализуем новую дату
        normalized_date = normalize_date(new_date)
        if not normalized_date:
            await update.message.reply_text(
                f"Не удалось распознать дату '{new_date}'. Попробуйте указать дату в формате '15.11' или '15 ноября'",
                reply_markup=self._create_navigation_keyboard(app_id)
            )
            return
        
        # Генерируем сообщение подтверждения
        confirmation_text = self.gigachat_service.generate_confirmation_message(
            app_id, 
            format_date_for_display(old_date) if old_date != "текущая дата" else old_date,
            format_date_for_display(normalized_date)
        )
        
        # Сохраняем операцию для подтверждения
        user_id = update.effective_user.id
        operation_id = f"{user_id}_{app_id}_{normalized_date}"
        self.pending_operations[operation_id] = {
            'app_id': app_id,
            'old_date': old_date,
            'new_date': normalized_date,
            'new_date_display': format_date_for_display(normalized_date),
            'user_id': user_id
        }
        
        # Создаем кнопки подтверждения
        # Ограничиваем длину callback_data
        operation_id_short = operation_id[:50] if len(operation_id) > 50 else operation_id
        
        keyboard = [
            [
                InlineKeyboardButton("✅ Подтвердить", callback_data=f"confirm_{operation_id_short}"),
                InlineKeyboardButton("❌ Отменить", callback_data=f"cancel_{operation_id_short}")
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        logger.info(f"Отправка подтверждения с кнопками для операции {operation_id_short}")
        logger.debug(f"Кнопки подтверждения: confirm_{operation_id_short}, cancel_{operation_id_short}")
        try:
            sent_message = await update.message.reply_text(confirmation_text, reply_markup=reply_markup)
            logger.info(f"Подтверждение с кнопками отправлено успешно (message_id: {sent_message.message_id})")
        except Exception as e:
            logger.error(f"Ошибка при отправке подтверждения с кнопками: {e}")
            # Создаем кнопки навигации вместо подтверждения
            nav_keyboard = self._create_navigation_keyboard(app_id)
            await update.message.reply_text(
                confirmation_text + "\n\n(Кнопки подтверждения не удалось отправить)",
                reply_markup=nav_keyboard
            )
    
    async def _handle_generate_context(self, update: Update, context: ContextTypes.DEFAULT_TYPE, entities: Dict[str, Any]):
        """Обработка генерации контекста"""
        app_id = entities.get('app_id')
        
        if not app_id:
            await update.message.reply_text(
                "Не удалось найти ID заявки. Укажите ID явно, например: 'подготовь контекст для звонка по заявке Z25-1869607'",
                reply_markup=self._create_navigation_keyboard()
            )
            return
        
        await self._show_context(update.message, context, app_id)
    
    async def _show_context(self, message, context: ContextTypes.DEFAULT_TYPE, app_id: str):
        """Показать контекст для заявки (из сообщения)"""
        await context.bot.send_chat_action(chat_id=message.chat.id, action="typing")
        
        # Отправляем сообщение о генерации
        status_msg = await message.reply_text("⏳ Генерирую контекст для звонка...")
        
        # Находим заявку
        app_data = self.database_manager.find_application(app_id)
        if not app_data:
            await status_msg.edit_text(f"❌ Заявка {app_id} не найдена.")
            await message.reply_text("", reply_markup=self._create_navigation_keyboard())
            return
        
        # Генерируем контекст
        try:
            context_text = self.gigachat_service.generate_call_context(app_data)
            
            # Создаем клавиатуру навигации
            nav_keyboard = self._create_navigation_keyboard(app_id)
            
            # Если контекст слишком длинный, разбиваем на части
            if len(context_text) > 4000:
                parts = context_text.split('\n\n')
                current_message = ""
                first_part = True
                for part in parts:
                    if len(current_message + part) > 3500:
                        if current_message:
                            if first_part:
                                await status_msg.edit_text(current_message.strip(), parse_mode='HTML')
                                first_part = False
                            else:
                                await message.reply_text(current_message.strip(), parse_mode='HTML')
                            current_message = part + "\n\n"
                        else:
                            current_message += part + "\n\n"
                    else:
                        current_message += part + "\n\n"
                if current_message:
                    if first_part:
                        await status_msg.edit_text(current_message.strip(), parse_mode='HTML', reply_markup=nav_keyboard)
                    else:
                        await message.reply_text(current_message.strip(), parse_mode='HTML', reply_markup=nav_keyboard)
            else:
                await status_msg.edit_text(context_text, parse_mode='HTML', reply_markup=nav_keyboard)
        except Exception as e:
            logger.error(f"Ошибка при генерации контекста: {e}", exc_info=True)
            await status_msg.edit_text("❌ Ошибка при генерации контекста. Попробуйте позже.")
            await message.reply_text("", reply_markup=self._create_navigation_keyboard(app_id))
    
    async def _show_context_for_callback(self, query, context: ContextTypes.DEFAULT_TYPE, app_id: str):
        """Показать контекст для заявки (из callback)"""
        await query.answer("Генерирую контекст...")
        await context.bot.send_chat_action(chat_id=query.message.chat.id, action="typing")
        
        # Отправляем сообщение о генерации (не редактируем предыдущее)
        status_msg = await query.message.reply_text("⏳ Генерирую контекст для звонка...")
        
        # Находим заявку
        app_data = self.database_manager.find_application(app_id)
        if not app_data:
            await status_msg.edit_text(f"❌ Заявка {app_id} не найдена.")
            await query.message.reply_text("", reply_markup=self._create_navigation_keyboard())
            return
        
        # Генерируем контекст
        try:
            context_text = self.gigachat_service.generate_call_context(app_data)
            
            # Создаем клавиатуру навигации
            nav_keyboard = self._create_navigation_keyboard(app_id)
            
            # Если контекст слишком длинный для одного сообщения, разбиваем на части
            if len(context_text) > 4000:
                # Разбиваем на части по абзацам
                parts = context_text.split('\n\n')
                current_message = ""
                first_part = True
                for part in parts:
                    if len(current_message + part) > 3500:
                        if current_message:
                            if first_part:
                                await status_msg.edit_text(current_message.strip(), parse_mode='HTML')
                                first_part = False
                            else:
                                await query.message.reply_text(current_message.strip(), parse_mode='HTML')
                            current_message = part + "\n\n"
                        else:
                            current_message += part + "\n\n"
                    else:
                        current_message += part + "\n\n"
                if current_message:
                    if first_part:
                        await status_msg.edit_text(current_message.strip(), parse_mode='HTML', reply_markup=nav_keyboard)
                    else:
                        await query.message.reply_text(current_message.strip(), parse_mode='HTML', reply_markup=nav_keyboard)
            else:
                await status_msg.edit_text(context_text, parse_mode='HTML', reply_markup=nav_keyboard)
        except Exception as e:
            logger.error(f"Ошибка при генерации контекста: {e}", exc_info=True)
            await status_msg.edit_text("❌ Ошибка при генерации контекста. Попробуйте позже.")
            await query.message.reply_text("", reply_markup=self._create_navigation_keyboard(app_id))
    
    async def _handle_create_task(self, update: Update, context: ContextTypes.DEFAULT_TYPE, entities: Dict[str, Any]):
        """Обработка создания задачи"""
        app_id = entities.get('app_id')
        await update.message.reply_text(
            "Создание задач будет реализовано в следующей версии.",
            reply_markup=self._create_navigation_keyboard(app_id)
        )
    
    async def _handle_confirmation(self, query, context: ContextTypes.DEFAULT_TYPE, operation_id: str, user_id: int):
        """Обработка подтверждения операции"""
        operation = self.pending_operations.get(operation_id)
        
        if not operation or operation['user_id'] != user_id:
            await query.answer("Операция не найдена или истекла")
            await query.message.reply_text("❌ Операция не найдена или истекла.", reply_markup=self._create_navigation_keyboard())
            return
        
        app_id = operation['app_id']
        new_date = operation['new_date']
        
        await query.answer("Изменяю статус...")
        
        # Выполняем изменение статуса
        success = self.database_manager.update_application_status(app_id, new_date)
        
        if success:
            new_date_display = operation.get('new_date_display', new_date)
            # Удаляем операцию из ожидающих
            del self.pending_operations[operation_id]
            
            # Отправляем новое сообщение с подтверждением (не редактируем предыдущее)
            await query.message.reply_text(
                f"✅ Статус заявки {app_id} успешно изменен!\n"
                f"Новая дата: {new_date_display}",
                reply_markup=self._create_navigation_keyboard(app_id)
            )
        else:
            await query.message.reply_text(
                "❌ Ошибка при изменении статуса. Попробуйте позже.",
                reply_markup=self._create_navigation_keyboard(app_id)
            )
    
    async def _handle_cancellation(self, query, context: ContextTypes.DEFAULT_TYPE, operation_id: str):
        """Обработка отмены операции"""
        await query.answer("Операция отменена")
        if operation_id in self.pending_operations:
            app_id = self.pending_operations[operation_id].get('app_id')
            del self.pending_operations[operation_id]
            await query.message.reply_text("❌ Операция отменена.", reply_markup=self._create_navigation_keyboard(app_id))
        else:
            await query.message.reply_text("❌ Операция отменена.", reply_markup=self._create_navigation_keyboard())
    
    def _create_navigation_keyboard(self, app_id: Optional[str] = None) -> InlineKeyboardMarkup:
        """
        Создание клавиатуры навигации
        
        Args:
            app_id: ID заявки (если есть, добавляются действия с заявкой)
            
        Returns:
            Клавиатура с кнопками навигации
        """
        keyboard = []
        
        if app_id:
            app_id_short = app_id[:30]
            keyboard.append([
                InlineKeyboardButton("📞 Контекст для звонка", callback_data=f"context_{app_id_short}"),
            ])
            keyboard.append([
                InlineKeyboardButton("✏️ Изменить статус", callback_data=f"status_{app_id_short}"),
            ])
            keyboard.append([
                InlineKeyboardButton("📋 Показать заявку", callback_data=f"show_{app_id_short}"),
            ])
        
        keyboard.append([
            InlineKeyboardButton("🔍 Найти другую заявку", callback_data="search_new"),
            InlineKeyboardButton("🏠 Главное меню", callback_data="main_menu"),
        ])
        
        return InlineKeyboardMarkup(keyboard)
    
    def _create_main_menu_keyboard(self) -> InlineKeyboardMarkup:
        """Создание клавиатуры главного меню"""
        keyboard = [
            [
                InlineKeyboardButton("🔍 Найти заявку", callback_data="search_new"),
            ],
            [
                InlineKeyboardButton("📖 Помощь", callback_data="help_menu"),
            ],
        ]
        return InlineKeyboardMarkup(keyboard)
    
    def _format_application_info(self, app_data: Dict[str, Any]) -> str:
        """Форматирование информации о заявке для отправки"""
        # Формируем сообщение с основной информацией
        lines = ["<b>📋 Информация о заявке</b>\n"]
        
        # Берем первые несколько важных полей
        important_fields = ['Номер заявки', 'Дата создания', 'Статус', 'Клиент', 'Автомобиль', 'Сумма']
        
        for field in important_fields:
            # Ищем поле в данных (может быть с разными названиями)
            for key, value in app_data.items():
                if field.lower() in str(key).lower() and value and str(value) != 'nan':
                    lines.append(f"<b>{key}:</b> {value}")
                    break
        
        # Если важных полей не нашлось, показываем первые несколько непустых
        if len(lines) == 1:
            count = 0
            for key, value in list(app_data.items())[:10]:
                if value and str(value) != 'nan' and count < 5:
                    lines.append(f"<b>{key}:</b> {value}")
                    count += 1
        
        return "\n".join(lines)
    
    def run(self):
        """Запуск бота"""
        if not self.application:
            self.initialize()
        
        logger.info("Запуск Telegram бота...")
        self.application.run_polling(allowed_updates=Update.ALL_TYPES)
