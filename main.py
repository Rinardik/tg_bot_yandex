from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
import const
from handlers.base import router as base_router
from handlers.registration import router as registration_router
from handlers.login import router as login_router
from handlers.catalog import router as catalog_router
from handlers.cart import router as cart_router
from handlers.admin import router as admin_router
from handlers.orders import router as orders_router

bot = Bot(token=const.TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
dp = Dispatcher()

dp.include_router(registration_router)
dp.include_router(login_router)
dp.include_router(catalog_router)
dp.include_router(cart_router)
dp.include_router(admin_router)
dp.include_router(orders_router)
dp.include_router(base_router)

if __name__ == "__main__":
    dp.run_polling(bot)