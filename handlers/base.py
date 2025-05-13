from aiogram import Router, F
from aiogram.types import Message
from aiogram.filters import CommandStart
import keyboard as kb
import db
from other_funch import was_inactive_for_24_hours
import logging

# Логируем только ошибки
logger = logging.getLogger(__name__)
router = Router()


@router.message(CommandStart())
async def cmd_start(message: Message):
    try:
        await message.answer(
            "Добро пожаловать в магазин Rinard Shop!\n"
            "Выбирайте товары из каталога.",
            reply_markup=kb.start_kb
        )
        conn, cur = db.init_users()
        cur.execute(
            "SELECT is_logged_in, last_active FROM users WHERE user_id = ?",
            (message.from_user.id,)
        )
        result = cur.fetchone()
        if result:
            is_logged_in, last_active = result
            if is_logged_in and not await was_inactive_for_24_hours(last_active):
                await message.answer("Вы уже вошли в аккаунт.", reply_markup=kb.get_logout_kb())
                conn.close()
                return
            else:
                cur.execute(
                    "UPDATE users SET is_logged_in = 0 WHERE user_id = ?", 
                    (message.from_user.id,)
                )
                conn.commit()
        conn.close()
        exists = await db.user_exists(message.from_user.id)
        if exists:
            entr = kb.get_login_kb()
            await message.answer("Хотите войти в аккаунт?", reply_markup=entr)
        else:
            registration = kb.get_registration_kb()
            await message.answer("Хотите зарегистрироваться?", reply_markup=registration)
    except Exception as e:
        logger.error(f"[cmd_start] Ошибка у пользователя {message.from_user.id}: {e}", exc_info=True)


@router.message(F.text)
async def handle_unknown_message(message: Message):
    try:
        await message.answer(
            "❌ Я не понимаю это сообщение.\n"
            "Пожалуйста, воспользуйтесь меню или командами:\n"
            "/start — начать\n"
            "/profile — посмотреть профиль",
            reply_markup=kb.start_kb
        )
    except Exception as e:
        logger.error(f"[handle_unknown_message] Ошибка: {e}", exc_info=True)