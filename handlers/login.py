from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, Contact
from aiogram.fsm.context import FSMContext
from aiogram.filters import StateFilter
from states import LoginStates, RecoveryForm
import keyboard as kb
import db
from other_funch import format_phone, is_correct_mobile_phone_number_ru, is_password_strong
import logging
from handlers.registration import cmd_profile

logger = logging.getLogger(__name__)
router = Router()


@router.callback_query(F.data == "entr")
async def process_login(callback: CallbackQuery, state: FSMContext):
    """
    Хэндлер начала входа.
    Предлагает отправить контакт для авторизации.
    """
    try:
        await callback.message.answer(
            "Нажмите на кнопку ниже, чтобы отправить ваш номер телефона:",
            reply_markup=kb.zam_parol
        )
        await state.set_state(LoginStates.phone)
        await callback.answer()
    except Exception as e:
        logger.error(f"[process_login] Ошибка при начале входа: {e}", exc_info=True)


@router.message(StateFilter(LoginStates.phone), F.contact)
async def login_enter_phone(message: Message, state: FSMContext):
    """
    Обработка контакта при входе.
    Проверяет наличие пользователя в БД.
    """
    contact: Contact = message.contact
    try:
        phone = await format_phone(contact.phone_number.strip())
        correct, answer = await is_correct_mobile_phone_number_ru(phone)
        if not correct:
            await message.answer(answer)
            return
        conn, cur = db.init_users()
        try:
            result = db.check_phon(phone)
        finally:
            conn.close()
        if not result:
            await message.answer("❌ Пользователь с таким телефоном не найден.")
            return
        await state.update_data(phone=phone)
        await message.answer("Введите пароль:")
        await state.set_state(LoginStates.password)

    except Exception as e:
        logger.error(f"[login_enter_phone] Ошибка при обработке контакта: {e}", exc_info=True)


@router.message(StateFilter(LoginStates.password), F.text)
async def login_enter_password(message: Message, state: FSMContext):
    """
    Проверяет совпадение пароля.
    Если всё верно → помечает пользователя как вошедшего.
    """
    try:
        data = await state.get_data()
        phone = data["phone"]
        password = message.text.strip()
        conn, cur = db.init_users()
        try:
            cur.execute("SELECT password FROM users WHERE phone = ?", (phone,))
            result = cur.fetchone()
        finally:
            conn.close()
        if result and result[0] == password:
            conn, cur = db.init_users()
            try:
                cur.execute("UPDATE users SET is_logged_in = 1, last_active = strftime('%s','now') WHERE phone = ?",
                            (phone,))
                conn.commit()
            finally:
                conn.close()
            await message.answer("✅ Вы успешно вошли в аккаунт!")
            await cmd_profile(message)
            await state.clear()
        else:
            await message.answer("❌ Неверный пароль. Попробуйте снова.")

    except Exception as e:
        logger.error(f"[login_enter_password] Ошибка при вводе пароля: {e}", exc_info=True)


@router.callback_query(F.data == "forgot_password")
async def start_recovery(callback: CallbackQuery, state: FSMContext):
    """
    Запуск восстановления пароля.
    Предлагает отправить контакт.
    """
    try:
        await callback.message.answer(
            "Нажмите на кнопку ниже, чтобы отправить ваш номер телефона:",
            reply_markup=kb.zam_parol
        )
        await state.set_state(RecoveryForm.phone)
        await callback.answer()
    except Exception as e:
        logger.error(f"[start_recovery] Ошибка при начале восстановления: {e}", exc_info=True)


@router.message(StateFilter(RecoveryForm.phone), F.contact)
async def recovery_enter_phone(message: Message, state: FSMContext):
    """
    Проверяет, существует ли пользователь с этим телефоном.
    Переходит к вводу нового пароля.
    """
    contact: Contact = message.contact
    try:
        phone = await format_phone(contact.phone_number.strip())
        correct, answer = await is_correct_mobile_phone_number_ru(phone)
        if not correct:
            await message.answer(answer)
            return
        conn, cur = db.init_users()
        try:
            cur.execute("SELECT * FROM users WHERE phone = ?", (phone,))
            user = cur.fetchone()
        finally:
            conn.close()
        if not user:
            await message.answer("Пользователь с таким телефоном не найден.")
            await state.clear()
            return
        await state.update_data(phone=phone)
        await message.answer("Введите новый пароль:")
        await state.set_state(RecoveryForm.new_password)
    except Exception as e:
        logger.error(f"[recovery_enter_phone] Ошибка при вводе телефона: {e}", exc_info=True)


@router.message(StateFilter(RecoveryForm.new_password), F.text)
async def recovery_set_password(message: Message, state: FSMContext):
    """
    Проверяет силу пароля перед сохранением.
    Если проходит → запрашивает повторный ввод.
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
        await state.update_data(new_password=password)
        await message.answer("Повторите пароль:")
        await state.set_state(RecoveryForm.confirm_new_password)
    except Exception as e:
        logger.error(f"[recovery_set_password] Ошибка при установке пароля: {e}", exc_info=True)


@router.message(StateFilter(RecoveryForm.confirm_new_password), F.text)
async def recovery_confirm_password(message: Message, state: FSMContext):
    """
    Сравнивает два введённых пароля.
    Сохраняет новый пароль в БД, если всё верно.
    """
    try:
        data = await state.get_data()
        new_password = data["new_password"]
        confirm_password = message.text.strip()
        if new_password != confirm_password:
            await message.answer("Пароли не совпадают. Попробуйте снова:")
            return
        phone = data["phone"]
        conn, cur = db.init_users()
        try:
            cur.execute("UPDATE users SET password = ? WHERE phone = ?", (new_password, phone))
            conn.commit()
        finally:
            conn.close()
        await message.answer("✅ Пароль успешно изменён!")
        await cmd_profile(message)
        await state.clear()
    except Exception as e:
        logger.error(f"[recovery_confirm_password] Ошибка при подтверждении пароля: {e}", exc_info=True)


