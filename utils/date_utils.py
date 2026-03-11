"""
Утилиты для работы с датами
"""
from datetime import datetime
from typing import Optional
import re
import logging

logger = logging.getLogger(__name__)


def normalize_date(date_str: Optional[str]) -> Optional[str]:
    """
    Нормализация даты в формат YYYY-MM-DD
    
    Args:
        date_str: Дата в произвольном формате
        
    Returns:
        Дата в формате YYYY-MM-DD или None
    """
    if not date_str:
        return None
    
    date_str = str(date_str).strip()
    
    # Пытаемся распарсить различные форматы
    formats = [
        '%Y-%m-%d',
        '%d.%m.%Y',
        '%d/%m/%Y',
        '%d-%m-%Y',
        '%Y.%m.%d',
    ]
    
    for fmt in formats:
        try:
            dt = datetime.strptime(date_str, fmt)
            return dt.strftime('%Y-%m-%d')
        except ValueError:
            continue
    
    # Пытаемся извлечь дату из текста (например, "15 ноября" или "15.11")
    try:
        # Формат "DD.MM" или "DD/MM"
        match = re.match(r'(\d{1,2})[./](\d{1,2})', date_str)
        if match:
            day, month = match.groups()
            current_year = datetime.now().year
            dt = datetime(current_year, int(month), int(day))
            return dt.strftime('%Y-%m-%d')
        
        # Формат "DD месяц" (например, "15 ноября")
        month_names = {
            'января': 1, 'февраля': 2, 'марта': 3, 'апреля': 4,
            'мая': 5, 'июня': 6, 'июля': 7, 'августа': 8,
            'сентября': 9, 'октября': 10, 'ноября': 11, 'декабря': 12
        }
        
        for month_name, month_num in month_names.items():
            if month_name in date_str.lower():
                match = re.search(r'(\d{1,2})', date_str)
                if match:
                    day = int(match.group(1))
                    current_year = datetime.now().year
                    dt = datetime(current_year, month_num, day)
                    return dt.strftime('%Y-%m-%d')
    except Exception as e:
        logger.warning(f"Ошибка при нормализации даты '{date_str}': {e}")
    
    return None


def format_date_for_display(date_str: Optional[str]) -> str:
    """
    Форматирование даты для отображения пользователю
    
    Args:
        date_str: Дата в формате YYYY-MM-DD
        
    Returns:
        Отформатированная дата
    """
    if not date_str:
        return "не указана"
    
    try:
        dt = datetime.strptime(date_str, '%Y-%m-%d')
        return dt.strftime('%d.%m.%Y')
    except ValueError:
        return date_str
