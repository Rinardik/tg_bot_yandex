from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, Contact
from aiogram.fsm.context import FSMContext
from aiogram.filters import Command, StateFilter
from states import RegistrationForm
import keyboard as kb
import db
from other_funch import format_phone, is_correct_mobile_phone_number_ru, is_password_strong

import logging

# Инициализируем логгер
logger = logging.getLogger(__name__)
router = Router()


@router.callback_query(F.data == "registration")
async def process_registration(callback: CallbackQuery, state: FSMContext):
    """
    Хэндлер начала регистрации.
    Сбрасывает состояние и просит имя.
    """
    try:
        await callback.message.answer("Введите ваше имя:")
        await state.set_state(RegistrationForm.name)
        await callback.answer()
    except Exception as e:
        logger.error(f"[process_registration] Ошибка при начале регистрации: {e}", exc_info=True)


@router.message(StateFilter(RegistrationForm.name), F.text)
async def process_name(message: Message, state: FSMContext):
    """
    Сохраняет имя пользователя и предлагает ввести телефон через контакт.
    """
    try:
        await state.update_data(name=message.text)
        await message.answer(
            "Нажмите на кнопку ниже, чтобы отправить ваш номер телефона:",
            reply_markup=kb.zam_parol
        )
        await state.set_state(RegistrationForm.phone)
    except Exception as e:
        logger.error(f"[process_name] Ошибка при сохранении имени: {e}", exc_info=True)


@router.message(StateFilter(RegistrationForm.phone), F.contact)
async def process_phone(message: Message, state: FSMContext):
    """
    Проверяет уникальность телефона перед регистрацией.
    """
    contact: Contact = message.contact
    try:
        phone = await format_phone(contact.phone_number)
        correct, answer = await is_correct_mobile_phone_number_ru(phone)
        if not correct:
            await message.answer(answer)
            return
        conn, cur = db.init_users()
        try:
            cur.execute("SELECT 1 FROM users WHERE phone = ?", (phone,))
            user_exists = cur.fetchone() is not None
        finally:
            conn.close()
        if user_exists:
            await message.answer(
                "❌ Пользователь с этим телефоном уже зарегистрирован.\n"
                "Если вы забыли пароль — нажмите на кнопку ниже.",
                reply_markup=kb.zam_parol
            )
            await state.clear()
            return
        await state.update_data(phone=phone)
        await message.answer("Придумайте пароль:", reply_markup=kb.get_cancel_kb())
        await state.set_state(RegistrationForm.password)
    except Exception as e:
        logger.error(f"[process_phone] Ошибка при обработке контакта: {e}", exc_info=True)


@router.message(StateFilter(RegistrationForm.password), F.text)
async def process_password(message: Message, state: FSMContext):
    """
    Проверяет силу пароля перед переходом к подтверждению.
    """
    try:
        password = message.text.strip()
        data = await state.get_data()
        name = data.get("name")
        phone = data.get("phone")
        is_strong, msg = is_password_strong(password, name, phone)
        if not is_strong:
            await message.answer(msg)
            return
        await state.update_data(password=password)
        await message.answer("Повторите пароль:", reply_markup=kb.get_cancel_kb())
        await state.set_state(RegistrationForm.password_confirm)
    except Exception as e:
        logger.error(f"[process_password] Ошибка при вводе пароля: {e}", exc_info=True)


@router.message(StateFilter(RegistrationForm.password_confirm), F.text)
async def process_password_confirm(message: Message, state: FSMContext):
    """
    Проверяет совпадение паролей.
    Сохраняет данные, если всё верно.
    """
    try:
        data = await state.get_data()
        password = data["password"]
        confirm_password = message.text.strip()
        if password != confirm_password:
            await message.answer("Пароли не совпадают. Попробуйте снова.")
            await message.answer("Введите пароль:", reply_markup=kb.get_cancel_kb())
            await state.set_state(RegistrationForm.password)
            return
        name = data["name"]
        phone = data["phone"]
        user_id = message.from_user.id
        db.update_or_create_user(user_id, name, phone, password)
        await message.answer("✅ Вы успешно зарегистрированы!")
        await cmd_profile(message)
        await state.clear()
    except Exception as e:
        logger.error(f"[process_password_confirm] Ошибка при подтверждении пароля: {e}", exc_info=True)


@router.message(Command("profile"))
async def cmd_profile(message: Message):
    """
    Вывод данных профиля пользователя.
    """
    try:
        conn, cur = db.init_users()
        cur.execute("SELECT name, phone FROM users WHERE user_id = ?", (message.from_user.id,))
        result = cur.fetchone()
        conn.close()
        if not result:
            await message.answer("Вы не зарегистрированы.")
            return
        name, phone = result
        await message.answer(
            f"Ваш профиль:\n"
            f"Имя: {name}\n"
            f"Телефон: {phone}",
            reply_markup=kb.start_kb
        )
    except Exception as e:
        logger.error(f"[cmd_profile] Ошибка при выводе профиля: {e}", exc_info=True)


@router.callback_query(F.data == "logout")
async def process_logout(callback: CallbackQuery):
    """
    Обработка выхода из аккаунта.
    """
    try:
        user_id = callback.from_user.id
        conn, cur = db.init_users()
        cur.execute("UPDATE users SET is_logged_in = 0 WHERE user_id = ?", (user_id,))
        conn.commit()
        conn.close()
        await callback.message.answer("Вы вышли из аккаунта.", reply_markup=kb.start_kb)
        await callback.answer()
    except Exception as e:
        logger.error(f"[process_logout] Ошибка при выходе: {e}", exc_info=True)


@router.callback_query(F.data == "cancel_registration")
async def cancel_fsm(callback: CallbackQuery, state: FSMContext):
    """
    Прерывает текущее состояние FSM.
    """
    try:
        await state.clear()
        await callback.message.answer("Регистрация/вход отменён.", reply_markup=kb.start_kb)
        await callback.answer()
    except Exception as e:
        logger.error(f"[cancel_fsm] Ошибка при отмене регистрации: {e}", exc_info=True)


