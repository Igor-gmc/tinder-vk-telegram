# клавиатуры согласно новой архитектуре кнопок

from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton

def kb_start():
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text='Старт')]],
        resize_keyboard=True
    )

def kb_after_auth():
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text='Настроить фильтры поиска')]],
        resize_keyboard=True
    )

def kb_main():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text='Предыдущий'), KeyboardButton(text='Далее')],
            [KeyboardButton(text='Дополнительно')]
            ],
        resize_keyboard=True,
        input_field_placeholder='Нажмите Далее или Предыдущий для подбора пары',
        one_time_keyboard=False
    )

def kb_more():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text='В избранное'), KeyboardButton(text='В черный список')],
            [KeyboardButton(text='Показать избранное'), KeyboardButton(text='Настроить фильтры поиска')],
            [KeyboardButton(text='Назад')]
            ],
        resize_keyboard=True,
        input_field_placeholder='Дополнительные действия, анкеты из ЧС показываться не будут',
        one_time_keyboard=False
    )

def kb_favorite_item():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text='Удалить из избранного'), KeyboardButton(text='Назад')],
            ],
        resize_keyboard=True,
        input_field_placeholder="Действия с избранным",
        one_time_keyboard=False
    )

def kb_favorite_back():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text='Назад')],
            ],
        resize_keyboard=True,
        input_field_placeholder="Кликните на VK ID для удаления",
        one_time_keyboard=False
    )

def kb_favorites_inline(vk_ids: list[int]) -> InlineKeyboardMarkup:
    """Inline кнопки с VK ID для просмотра анкеты"""
    buttons = [
        [InlineKeyboardButton(text=str(vk_id), callback_data=f'fav_view:{vk_id}')]
        for vk_id in vk_ids
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def kb_favorites_delete_inline(vk_ids: list[int]) -> InlineKeyboardMarkup:
    """Inline кнопки с VK ID для удаления из избранного"""
    buttons = [
        [InlineKeyboardButton(text=str(vk_id), callback_data=f'fav_del:{vk_id}')]
        for vk_id in vk_ids
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)
