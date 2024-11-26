import asyncio
from aiogram import Bot, Dispatcher, types
from aiogram.filters.command import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

from keyboards import yes_or_no_kb, company_or_avitolog


class WelcomeState(StatesGroup):
    clientType = State()
    company = State()

    avitologCompaniesCount = State()
    avitologProblems = State()
    avitologAi = State()

    statistics = State()
    analyze = State()
    testing = State()
    phone = State()
    finish = State()


async def client_type(message: types.Message, state: FSMContext, bot: Bot):
    await state.update_data(clientType=message.text)
    if message.text == "компания":
        await state.set_state(WelcomeState.company)
        await message.answer('💼 Какие у вас бизнесы на Авито? Пожалуйста, прикрепите ссылки на них в одном сообщении.')
    elif message.text == "авитолог":
        await state.set_state(WelcomeState.avitologCompaniesCount)
        await message.answer('📊 Сколько компаний вы поддерживаете?')


async def company(message: types.Message, state: FSMContext, bot: Bot):
    await state.update_data(company=message.text)
    await state.set_state(WelcomeState.statistics)
    await message.answer('📈 Ведете ли вы статистику по рекламным кампаниям на Авито?', reply_markup=yes_or_no_kb)


async def avitolog_companies_count(message: types.Message, state: FSMContext):
    await state.update_data(avitolog_companies_count=message.text)
    await state.set_state(WelcomeState.avitologProblems)
    await message.answer('⚠️ Есть ли у вас проблемы с менеджерами по обработке заявок?', reply_markup=yes_or_no_kb)


async def avitolog_problems(message: types.Message, state: FSMContext):
    await state.update_data(avitolog_problems=message.text)
    if message.text == "да":
        await state.set_state(WelcomeState.avitologAi)
        await message.answer('🤖 Подключен ли у вас ИИ-продавец?', reply_markup=yes_or_no_kb)
    elif message.text == "нет":
        await state.set_state(WelcomeState.statistics)
        await message.answer('📈 Ведете ли вы статистику по рекламным кампаниям на Авито?', reply_markup=yes_or_no_kb)


async def avitolog_ai(message: types.Message, state: FSMContext):
    await state.update_data(avitolog_ai=message.text)
    await state.set_state(WelcomeState.statistics)
    await message.answer('📈 Ведете ли вы статистику по рекламным кампаниям на Авито?', reply_markup=yes_or_no_kb)


async def statistics(message: types.Message, state: FSMContext):
    await state.update_data(statistics=message.text)
    await state.set_state(WelcomeState.analyze)
    await message.answer('🔍 Анализируете ли вы звонки ваших менеджеров?', reply_markup=yes_or_no_kb)


async def analyze(message: types.Message, state: FSMContext):
    await state.update_data(analyze=message.text)
    await state.set_state(WelcomeState.testing)
    await message.answer('🧪 Хотели бы вы протестировать наш сервис аналитики и сервис ИИ-продавца?',
                         reply_markup=yes_or_no_kb)


async def testing(message: types.Message, state: FSMContext):
    await state.update_data(testing=message.text)
    if message.text == 'да':
        await state.set_state(WelcomeState.phone)
        await message.answer('📱 Пожалуйста, укажите ваш номер телефона для связи.')
    elif message.text == 'нет':
        await state.set_state(WelcomeState.finish)
        await message.answer('🎉 Большое спасибо что уделили время, хороших продаж! 🎉')
        data = await state.get_data()
        await message.answer(f"Ваши данные: {data}", )


async def phone(message: types.Message, state: FSMContext):
    await state.update_data(phone=message.text)
    await state.set_state(WelcomeState.finish)
    await message.answer('🎉 Большое спасибо что уделили время, мы с вами скоро свяжемся. 📞')

    data = await state.get_data()
    await bot.send_message(chat_id=-4521744776, text=f"""
🧑‍💼/👨‍💼 Тип клиента: {data.get("clientType")} 
Ссылки на аккаунты: {data.get("company")}
🏢 Количество компаний: {data.get("avitolog_companies_count")}
⚠️ Есть проблемы с менеджером: {data.get("avitolog_problems")}
📈 Ведете ли вы статистику: {data.get("statistics")}
🤖 Подключен ли у вас ИИ-продавец: {data.get("avitolog_ai")}
🔍 Анализируете ли вы звонки: {data.get("analyze")}
🧪 Хотели бы вы протестировать: {data.get("testing")}
📱 Номер телефона: {data.get("phone")}
👤 Ссылка на телеграм  : @{message.from_user.username}
""")


bot = Bot(token="8170279154:AAHbZ7yy_bkX-5T8xodyCCiuxLO3vUsmQbA")
dp = Dispatcher()
dp.message.register(client_type, WelcomeState.clientType)

dp.message.register(company, WelcomeState.company)
dp.message.register(avitolog_companies_count, WelcomeState.avitologCompaniesCount)
dp.message.register(avitolog_problems, WelcomeState.avitologProblems)
dp.message.register(avitolog_ai, WelcomeState.avitologAi)

dp.message.register(statistics, WelcomeState.statistics)
dp.message.register(analyze, WelcomeState.analyze)
dp.message.register(testing, WelcomeState.testing)
dp.message.register(phone, WelcomeState.phone)


@dp.message(Command("start"))
async def cmd_start(message: types.Message, state: FSMContext):
    await message.answer(
        "👋 Здравствуйте, я бот AvitoStata Origin, рад принять вашу заявку по вашему бизнесу."
        " Мы сотрудничаем с компаниями и авитологами, и предоставляем сервисы для того,"
        " чтобы бизнес на Авито работал эффективнее. 🚀"
    )
    await message.answer("❓ Вы компания или вы авитолог?", reply_markup=company_or_avitolog)
    await state.set_state(WelcomeState.clientType)


async def main():
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
