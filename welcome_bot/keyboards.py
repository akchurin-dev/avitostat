from aiogram.types import ReplyKeyboardMarkup, KeyboardButton

company_or_avitolog = ReplyKeyboardMarkup(
    keyboard=[
        [
            KeyboardButton(text="компания"),
        ],
        [
            KeyboardButton(text="авитолог"),
        ],
    ],
    resize_keyboard=False,
    one_time_keyboard=True,
    selective=True
)

yes_or_no_kb = ReplyKeyboardMarkup(
    keyboard=[
        [
            KeyboardButton(text="да"),
        ],
        [
            KeyboardButton(text="нет"),
        ],
    ],
    resize_keyboard=False,
    one_time_keyboard=True,
    selective=True
)