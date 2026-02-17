# клавиатуры согласно новой архитектуре кнопок  

from aiogram.types import ReplyKeyboardMarkup, KeyboardButton

def kb_start():
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text='Старт')]],
        resize_keyboard=True
    )

def kb_after_auth():
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text='Настроить фильтры')]],
        resize_keyboard=True
    )
