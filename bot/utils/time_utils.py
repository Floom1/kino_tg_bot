import pytz
from datetime import datetime
from bot.config import settings
import logging

def get_current_moscow_time():
    """Возвращает текущее время в Москве (UTC+3)"""
    moscow_tz = pytz.timezone(settings.TZ)
    current_time = datetime.now(pytz.utc).astimezone(moscow_tz)
    return current_time

def check_time_difference():
    """Проверяет разницу между серверным временем и московским"""
    utc_time = datetime.now(pytz.utc)
    moscow_time = get_current_moscow_time()
    diff = moscow_time - utc_time
    hours_diff = diff.total_seconds() / 3600
    logging.info(f"Разница между серверным временем и московским: {hours_diff:.2f} часов")
    return hours_diff

def get_current_moscow_date():
    """Возвращает текущую дату в Москве (UTC+3)"""
    return get_current_moscow_time().date()

def format_date_for_db(date_obj):
    """Форматирует дату для хранения в БД (YYYY-MM-DD)"""
    return date_obj.strftime("%Y-%m-%d")

def parse_date_from_str(date_str):
    """Парсит строку даты в объект datetime.date"""
    return datetime.strptime(date_str, "%Y-%m-%d").date()

def is_date_in_future(date_str):
    """Проверяет, что дата не в прошлом (с учетом московского времени)"""
    current_date = get_current_moscow_date()
    event_date = parse_date_from_str(date_str)
    return event_date >= current_date