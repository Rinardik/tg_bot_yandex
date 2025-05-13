from aiogram import Router, F
from aiogram.types import CallbackQuery, Message
from aiogram.fsm.context import FSMContext
from aiogram import Bot
import keyboard as kb
import db
from const import MANAGER_ID

import logging
import json

logger = logging.getLogger(__name__)
router = Router()


async def notify_manager_about_order(bot: Bot, user_id: int, basket: dict, total_price: int):
    """
    Отправляет всем менеджерам сообщение о новом заказе.
    """
    try:
        basket_text = "\n".join([
            f"{db.get_product_by_id(int(pid))[1]} x {qty} шт. = {db.get_product_by_id(int(pid))[4] * qty} руб."
            for pid, qty in basket.items()
        ])
        message_text = (
            f"📦 Новый заказ от пользователя {user_id}\n\n"
            f"Товары:\n{basket_text}\n\n"
            f"🧮 Общая сумма: {total_price} руб."
        )
        for manager_id in MANAGER_ID:
            try:
                await bot.send_message(manager_id, message_text, reply_markup=kb.mened)
            except Exception as e:
                logger.error(f"[notify_manager] Ошибка отправки менеджеру {manager_id}: {e}", exc_info=True)
    except Exception as e:
        logger.error(f"[notify_manager_about_order] Неожиданная ошибка: {e}", exc_info=True)


def format_basket(basket: dict) -> str:
    """
    Преобразует корзину в текстовое представление для вывода.
    """
    lines = []
    for pid, quantity in basket.items():
        product = db.get_product_by_id(int(pid))
        if product:
            _, name, _, _, price, *_ = product
            lines.append(f"{name} x {quantity} шт. = {price * quantity} руб.")
    return "\n".join(lines) or "🛒 Пустой заказ"


@router.callback_query(F.data == "view_orders")
async def view_orders(callback: CallbackQuery):
    """
    Менеджер просматривает список новых заказов.
    Для каждого заказа выводит данные пользователя и товары.
    """
    if callback.from_user.id not in MANAGER_ID:
        await callback.message.answer("❌ У вас нет прав на просмотр заказов.")
        await callback.answer()
        return
    try:
        orders = db.get_new_orders()
        if not orders:
            await callback.message.answer("📋 Нет новых заказов.")
            return
        for order in orders:
            order_id, user_id, basket_json, total_price, created_at = order
            basket = json.loads(basket_json)
            # Получаем данные пользователя
            user_info = db.get_user_info(user_id)
            name, phone = user_info if user_info else ("Не указан", "Не указан")
            caption = (
                f"📦 Заказ #{order_id}\n"
                f"👤 Пользователь: {user_id} ({name})\n"
                f"📞 Телефон: {phone}\n"
                f"📅 Дата: {created_at}\n"
                f"🧮 Итого: {total_price} руб.\n"
                f"Товары:\n{format_basket(basket)}"
            )
            await callback.message.answer(caption, reply_markup=kb.get_order_actions(order_id))
        await callback.answer()
    except Exception as e:
        logger.error(f"[view_orders] Ошибка при выводе заказов: {e}", exc_info=True)
        await callback.message.answer("⚠ Ошибка при загрузке заказов.")


@router.callback_query(F.data.startswith("confirm_order_"))
async def confirm_order(callback: CallbackQuery):
    """
    Подтверждает заказ → изменяет статус на 'confirmed'.
    Отправляет уведомление клиенту.
    """
    try:
        order_id = int(callback.data.split("_")[2])
    except (IndexError, ValueError):
        await callback.message.answer("❌ Неверный формат данных.")
        return
    try:
        db.update_order_status(order_id, "confirmed")
        order = db.get_order_by_id(order_id)
        if not order:
            await callback.message.answer("❌ Заказ не найден.")
            return
        _, user_id, _, _, _ = order
        await callback.bot.send_message(user_id, f"✅ Ваш заказ #{order_id} подтверждён!")
        await callback.message.edit_text(f"Заказ #{order_id} подтверждён.", reply_markup=None)
        await callback.answer()
    except Exception as e:
        logger.error(f"[confirm_order] Ошибка при подтверждении заказа #{order_id}: {e}", exc_info=True)
        await callback.message.answer("⚠ Не удалось подтвердить заказ.")


@router.callback_query(F.data.startswith("cancel_order_"))
async def cancel_order(callback: CallbackQuery):
    """
    Отменяет заказ → изменяет статус на 'cancelled'.
    Отправляет уведомление клиенту.
    """
    try:
        order_id = int(callback.data.split("_")[2])
    except (IndexError, ValueError):
        await callback.message.answer("❌ Неверный формат данных.")
        return
    try:
        db.update_order_status(order_id, "cancelled")
        order = db.get_order_by_id(order_id)
        if not order:
            await callback.message.answer("❌ Заказ не найден.")
            return
        _, user_id, _, _, _ = order
        await callback.bot.send_message(user_id, f"❌ Ваш заказ #{order_id} отменён.")
        await callback.message.edit_text(f"Заказ #{order_id} отменён.", reply_markup=None)
        await callback.answer()
    except Exception as e:
        logger.error(f"[cancel_order] Ошибка при отмене заказа #{order_id}: {e}", exc_info=True)
        await callback.message.answer("⚠ Не удалось отменить заказ.")

    
@router.callback_query(F.data.startswith("view_order_"))
async def view_order_details(callback: CallbackQuery):
    """
    Выводит полные данные по заказу менеджеру.
    """
    if callback.from_user.id not in MANAGER_ID:
        await callback.message.answer("❌ Только менеджеры могут просматривать заказы.")
        await callback.answer()
        return
    try:
        order_id = int(callback.data.split("_")[1])
    except (IndexError, ValueError):
        await callback.message.answer("❌ Неверный ID заказа.")
        return
    try:
        order = db.get_order_by_id(order_id)
        if not order:
            await callback.message.answer("❌ Заказ не найден.")
            return
        _, user_id, basket_json, total_price, status = order
        basket = json.loads(basket_json)
        caption = (
            f"📦 Детали заказа #{order_id}\n"
            f"Пользователь: {user_id}\n"
            f"Статус: {status}\n"
            f"Товары:\n{format_basket(basket)}\n"
            f"🧮 Сумма: {total_price} руб."
        )
        await callback.message.answer(caption)
        await callback.answer()
    except Exception as e:
        logger.error(f"[view_order_details] Ошибка при выводе заказа #{order_id}: {e}", exc_info=True)
        await callback.message.answer("⚠ Не удалось показать детали заказа.")