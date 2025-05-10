from aiogram import Bot, Dispatcher
from handlers import router
from const import TOKEN
import asyncio
import db

bot = Bot(token=TOKEN)
dp = Dispatcher()

dp.include_router(router)

async def main():
    print("Бот запущен...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    db.init_users()
    asyncio.run(main())