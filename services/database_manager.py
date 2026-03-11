"""
Менеджер для работы с базой данных (Excel файл)
"""
import pandas as pd
from pathlib import Path
from typing import Optional, Dict, Any
import logging

logger = logging.getLogger(__name__)


class DatabaseManager:
    """Класс для работы с базой данных заявок"""
    
    def __init__(self, database_path: Path):
        """
        Инициализация менеджера БД
        
        Args:
            database_path: Путь к Excel файлу с данными
        """
        self.database_path = database_path
        self._data: Optional[pd.DataFrame] = None
        self._sheet_name: Optional[str] = None
        
    def load_data(self) -> bool:
        """
        Загрузка данных из Excel файла
        
        Returns:
            True если загрузка успешна, False иначе
        """
        try:
            if not self.database_path.exists():
                logger.error(f"Файл базы данных не найден: {self.database_path}")
                return False
            
            # Определяем имя листа
            excel_file = pd.ExcelFile(self.database_path)
            self._sheet_name = excel_file.sheet_names[0] if excel_file.sheet_names else None
            
            if not self._sheet_name:
                logger.error("В Excel файле не найдены листы")
                return False
            
            # Загружаем данные
            self._data = pd.read_excel(self.database_path, sheet_name=self._sheet_name)
            logger.info(f"Загружено {len(self._data)} записей из {self.database_path}")
            return True
            
        except Exception as e:
            logger.error(f"Ошибка при загрузке данных: {e}")
            return False
    
    def find_application(self, app_id: str) -> Optional[Dict[str, Any]]:
        """
        Поиск заявки по ID
        
        Args:
            app_id: ID заявки (например, Z25-1869607)
            
        Returns:
            Словарь с данными заявки или None если не найдена
        """
        if self._data is None:
            if not self.load_data():
                return None
        
        try:
            # Очищаем app_id от лишних символов
            app_id_clean = app_id.strip().upper()
            
            # Ищем заявку по ID во всех колонках
            # Сначала пробуем точное совпадение в первой колонке (обычно там ID)
            mask = self._data.iloc[:, 0].astype(str).str.upper().str.contains(app_id_clean, case=False, na=False, regex=False)
            
            # Если не нашли, ищем во всех колонках
            if not mask.any():
                for col in self._data.columns:
                    mask = self._data[col].astype(str).str.upper().str.contains(app_id_clean, case=False, na=False, regex=False)
                    if mask.any():
                        break
            
            result = self._data[mask]
            
            if result.empty:
                logger.warning(f"Заявка {app_id} не найдена")
                return None
            
            # Преобразуем первую найденную строку в словарь
            app_data = result.iloc[0].to_dict()
            
            # Очищаем значения от NaN и преобразуем в строки где нужно
            cleaned_data = {}
            for key, value in app_data.items():
                if pd.isna(value):
                    cleaned_data[key] = None
                else:
                    cleaned_data[key] = value
            
            return cleaned_data
            
        except Exception as e:
            logger.error(f"Ошибка при поиске заявки {app_id}: {e}", exc_info=True)
            return None
    
    def get_application_status(self, app_id: str) -> Optional[str]:
        """
        Получение текущего статуса заявки
        
        Args:
            app_id: ID заявки
            
        Returns:
            Статус заявки или None
        """
        app_data = self.find_application(app_id)
        if not app_data:
            return None
        
        # Ищем колонку со статусом по ключевым словам
        status_keywords = ['статус', 'status', 'состояние', 'стадия']
        for key, value in app_data.items():
            if any(keyword in str(key).lower() for keyword in status_keywords):
                if value and str(value) != 'nan':
                    return str(value)
        
        return None
    
    def get_application_full_info(self, app_id: str) -> Optional[Dict[str, Any]]:
        """
        Получение полной информации о заявке
        
        Args:
            app_id: ID заявки
            
        Returns:
            Словарь с полной информацией о заявке
        """
        return self.find_application(app_id)
    
    def update_application_status(self, app_id: str, new_date: str, new_status: Optional[str] = None) -> bool:
        """
        Обновление статуса заявки
        
        Args:
            app_id: ID заявки
            new_date: Новая дата изменения статуса
            new_status: Новый статус (опционально)
            
        Returns:
            True если обновление успешно
        """
        # TODO: Реализовать обновление статуса
        # Пока только логируем
        logger.info(f"Обновление статуса заявки {app_id}: дата={new_date}, статус={new_status}")
        return True
    
    def search_applications(self, query: str) -> list:
        """
        Поиск заявок по различным критериям
        
        Args:
            query: Поисковый запрос
            
        Returns:
            Список найденных заявок
        """
        if self._data is None:
            if not self.load_data():
                return []
        
        # TODO: Реализовать поиск по различным критериям
        return []
