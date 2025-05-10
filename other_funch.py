import db
import time
from datetime import timedelta
import random

async def generate_code():
    return str(random.randint(100000, 999999))

async def user_exists(user_id: int) -> bool:
    conn, cur = db.init_users()
    cur.execute("SELECT 1 FROM users WHERE user_id = ?", (user_id,))
    result = cur.fetchone()
    conn.close()
    return result is not None


async def is_correct_mobile_phone_number_ru(s: str) -> tuple[bool, str]:
    if s.startswith('+7'):
        remainder = s[2:]
    elif s.startswith('8'):
        remainder = s[1:]
    else:
        return (False, 'Номер должен начитнаться с +7 или 8')
    
    if '(' in remainder or ')' in remainder:
        if not (remainder.count('(') == 1 and remainder.count(')') == 1):
            return (False, "Неправильная последовательность скобок")
        if remainder.find('(') > remainder.find(')'):
            return (False, "Неправильная последовательность скобок")
    
    remainder = ''.join(c for c in remainder if c.isdigit())
    if len(remainder) == 10:
        return (True, "")
    return (False, "Неправильное количество символов")


async def was_inactive_for_24_hours(last_active_time: int) -> bool:
    now = time.time()
    inactive_period = now - last_active_time
    return inactive_period > timedelta(days=1).total_seconds()