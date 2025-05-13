import db
import time
from datetime import timedelta
import re


def is_password_strong(password: str, name: str = "", phone: str = "") -> tuple[bool, str]:
    """
    Проверяет, насколько безопасен пароль.
    """
    if len(password) < 6:
        return False, "Пароль слишком короткий. Минимум 6 символов."
    if not re.search(r"\d", password):
        return False, "Пароль должен содержать хотя бы одну цифру."
    if not re.search(r"[A-ZА-Я]", password):
        return False, "Пароль должен содержать хотя бы одну заглавную букву."
    if not re.search(r"[a-zа-я]", password):
        return False, "Пароль должен содержать хотя бы одну строчную букву."
    if ' ' in password:
        return False, "Пароль не должен содержать пробелов."
    if name and name.lower() in password.lower():
        return False, "Пароль не должен содержать ваше имя."
    if phone:
        digits = ''.join(filter(str.isdigit, phone))
        if len(digits) >= 4 and any(part in password for part in [digits[-4:], digits[:4]]):
            return False, "Пароль не должен содержать часть вашего номера телефона."
    return True, "Пароль соответствует требованиям безопасности."


async def format_phone(phone: str) -> str:
    """
    Приводит телефон к международному формату +7...
    """
    digits = ''.join(filter(str.isdigit, phone))
    if len(digits) == 11:
        if digits.startswith('8'):
            return '+7' + digits[1:]
        elif digits.startswith('7'):
            return '+' + digits
    elif len(digits) == 10 and phone.startswith('9'):
        return '+7' + digits
    return '+' + digits


async def is_correct_mobile_phone_number_ru(s: str) -> tuple[bool, str]:
    """
    Проверяет, является ли введённый номер российским мобильным.
    """
    if s.startswith('+7'):
        remainder = s[2:]
    elif s.startswith('8'):
        remainder = s[1:]
    else:
        return (False, 'Номер должен начинаться с +7 или 8')
    # Проверяем скобки
    if '(' in remainder or ')' in remainder:
        if not (remainder.count('(') == 1 and remainder.count(')') == 1):
            return (False, "Неправильная последовательность скобок")
        if remainder.find('(') > remainder.find(')'):
            return (False, "Неправильная последовательность скобок")
    # Убираем всё, кроме цифр
    remainder = ''.join(c for c in remainder if c.isdigit())
    # Российский мобильный номер должен быть длиной 10 или 11 знаков после +7/8
    if len(remainder) == 10:
        return (True, "")
    return (False, "Неправильное количество символов")


async def was_inactive_for_24_hours(last_active_time: int) -> bool:
    """
    Проверяет, был ли пользователь неактивен более 24 часов.
    """
    now = time.time()
    inactive_period = now - last_active_time
    return inactive_period > timedelta(days=1).total_seconds()