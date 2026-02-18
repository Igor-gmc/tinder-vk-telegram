# обработчики: /start, токен, фильтры, навигация, избранное

import asyncio

from src.presentation.tg.states import AuthState, FilterState, MenuState
from src.presentation.tg.keyboards import (
    kb_favorite_item, kb_main, kb_more, kb_start, kb_after_auth,
    kb_favorites_inline, kb_favorites_delete_inline, kb_favorite_back
)
from src.infrastructure.db.repositories import InMemoryUserRepo

from aiogram import Router, F
from aiogram.filters import CommandStart, Command
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext


def setup_handlers(user_repo: InMemoryUserRepo) -> Router:
    router = Router()

    # функция для реагирования на команду /start
    @router.message(CommandStart())
    async def command_start_handler(message: Message, state: FSMContext) -> None:
        await state.clear()
        await message.answer("Чтобы начать нажмите Старт", reply_markup=kb_start())

    # запрашиваем у пользователя VK токен
    @router.message(F.text == "Старт")
    async def start_auth(message: Message, state: FSMContext) -> None:
        await state.clear()
        await state.set_state(AuthState.waiting_vk_token)
        await message.answer("Шаг 1/2: Введите токен VK")

    # ожидаем токен от пользователя
    @router.message(AuthState.waiting_vk_token)
    async def got_vk_token(message: Message, state: FSMContext) -> None:
        token = message.text.strip()

        if not token:
            await message.answer("Токен не может быть пустым! Введите токен еще раз.")
            return

        # записываем в память VK токен
        await state.update_data(vk_access_token=token)

        # Переключаемся на ожидание VK ID
        await state.set_state(AuthState.waiting_vk_user_id)
        await message.answer("Шаг 2/2: Введите VK_ID")

    # ожидаем от пользователя VK ID
    @router.message(AuthState.waiting_vk_user_id)
    async def got_vk_id(message: Message, state: FSMContext) -> None:
        try:
            vk_user_id = int(message.text.strip())
        except ValueError:
            await message.answer("VK ID должен быть числом! Введите ID еще раз.")
            return

        # читаем токен из FSM
        data = await state.get_data()
        vk_access_token = data.get("vk_access_token")

        if not vk_access_token:
            await message.answer("Что-то пошло не так. Снова авторизуйтесь — нажмите Старт")
            await state.clear()
            return

        tg_user_id = message.from_user.id

        await user_repo.upsert_user_token_and_vk_id(
            tg_user_id=tg_user_id,
            vk_access_token=vk_access_token,
            vk_user_id=vk_user_id,
        )

        # завершаем FSM авторизации
        await state.clear()

        # сообщаем что данные записаны
        await message.answer("Данные авторизации записаны ✅", reply_markup=kb_after_auth())

        # НЕ time.sleep — иначе бот зависнет
        await asyncio.sleep(2)
        await message.answer("Чтобы настроить фильтры для поиска кандидатов нажмите «Настроить фильтры»")

    # старт настройки фильтров
    @router.message(F.text == "Настроить фильтры поиска")
    async def start_filters(message: Message, state: FSMContext) -> None:
        await state.clear()
        await state.set_state(FilterState.waiting_city)
        await message.answer("Шаг 1/4: Введите ваш город для поиска кандидатов")

    @router.message(FilterState.waiting_city)
    async def got_city(message: Message, state: FSMContext) -> None:
        city = message.text.strip()

        if not city:
            await message.answer("Город не может быть пустым. Попробуйте еще раз.")
            return

        # сохраняем в память
        await state.update_data(filter_city=city)

        await state.set_state(FilterState.waiting_gender)
        await message.answer("Шаг 2/4: Укажите пол (1=Муж, 2=Жен)")

    @router.message(FilterState.waiting_gender)
    async def got_gender(message: Message, state: FSMContext) -> None:
        gender_text = message.text.strip()

        if gender_text not in {"1", "2"}:
            await message.answer("Пол должен быть 1 или 2. Попробуйте еще раз.")
            return

        await state.update_data(filter_gender=int(gender_text))

        await state.set_state(FilterState.waiting_age_from)
        await message.answer("Шаг 3/4: Введите возраст ОТ (число, не менее 18)")

    @router.message(FilterState.waiting_age_from)
    async def got_age_from(message: Message, state: FSMContext) -> None:
        text_age_from = message.text.strip()

        if not text_age_from:
            await message.answer("Возраст ОТ не может быть пустым. Введите число.")
            return

        try:
            age_from = int(text_age_from)
        except ValueError:
            await message.answer("Возраст должен быть целым числом. Введите возраст ОТ ещё раз.")
            return

        if age_from < 18 or age_from > 100:
            await message.answer("Возраст ОТ должен быть от 18 до 100. Введите ещё раз.")
            return

        await state.update_data(filter_age_from=age_from)

        await state.set_state(FilterState.waiting_age_to)
        await message.answer("Шаг 4/4: Введите возраст ДО (число)")

    @router.message(FilterState.waiting_age_to)
    async def got_age_to(message: Message, state: FSMContext) -> None:
        text_age_to = message.text.strip()

        if not text_age_to:
            await message.answer("Возраст ДО не может быть пустым. Введите число.")
            return

        try:
            age_to = int(text_age_to)
        except ValueError:
            await message.answer("Возраст должен быть целым числом. Введите возраст ДО ещё раз.")
            return

        if age_to < 18 or age_to > 100:
            await message.answer("Возраст ДО должен быть от 18 до 100. Введите ещё раз.")
            return

        # достаём накопленные значения
        data = await state.get_data()
        city = data.get("filter_city")
        gender = data.get("filter_gender")
        age_from = data.get("filter_age_from")

        if city is None or gender is None or age_from is None:
            await state.clear()
            await message.answer("Что-то пошло не так. Начните настройку фильтров заново: «Настроить фильтры».")
            return

        # логическая проверка диапазона
        if age_to < age_from:
            await message.answer(f"Возраст ДО ({age_to}) не может быть меньше возраста ОТ ({age_from}). Введите ДО ещё раз.")
            return

        tg_user_id = message.from_user.id

        await user_repo.update_filters(
            tg_user_id=tg_user_id,
            city=city,
            gender=gender,
            age_from=age_from,
            age_to=age_to,
        )

        await state.clear()
        await state.set_state(MenuState.main)
        await message.answer(
            "Фильтры настроены ✅\n"
            f"Город: {city}\n"
            f"Пол: {gender}\n"
            f"Возраст: от {age_from} до {age_to}",
            reply_markup=kb_main()
        )

    # Меню Главное MenuState.main
    ## Переход в меню Дополнительно
    @router.message(MenuState.main, F.text == 'Дополнительно')
    async def menu_more(message: Message, state: FSMContext) -> None:
        await state.set_state(MenuState.more)
        await message.answer('Дополнительные действия', reply_markup=kb_more())

    ## Вернуться в главное меню при нажатии Далее
    @router.message(MenuState.main, F.text == 'Далее')
    async def main_next(message: Message, state: FSMContext) -> None:
        # тут будет код пролистывания вперед
        await message.answer('Главное меню', reply_markup=kb_main())

    ## Вернуться в главное меню при нажатии Назад
    @router.message(MenuState.main, F.text == 'Предыдущий')
    async def main_prev(message: Message, state: FSMContext) -> None:
        # тут будет код пролистывания назад
        await message.answer('Главное меню', reply_markup=kb_main())

    # Меню Дополнительно MenuState.more
    ## Вернуться на уровень выше
    @router.message(MenuState.more, F.text == "Назад")
    async def back_from_more(message: Message, state: FSMContext) -> None:
        await state.set_state(MenuState.main)
        await message.answer("Главное меню:", reply_markup=kb_main())

    ## Добавить в избранное
    @router.message(MenuState.more, F.text == 'В избранное')
    async def add_favorite(message: Message, state: FSMContext) -> None:
        # запоминаем данные кто добавляет и кого добавляют
        tg_user_id = message.from_user.id
        vk_profile_id = 123456
        # записываем добавленного в БД
        await user_repo.add_favorite(tg_user_id=tg_user_id, vk_profile_id=vk_profile_id)
        await message.answer(f'Добавлено в избранное vk_id={tg_user_id}', reply_markup=kb_more())
    
    ## Добавить в черны список
    @router.message(MenuState.more, F.text == 'В черный список')
    async def add_to_black_list(message: Message, state: FSMContext) -> None:
        # запоминаем данные кто добавляет и кого нужно добавить в черный список
        tg_user_id = message.from_user.id
        vk_profile_id = 123456
        # записываем в БД черный список
        await user_repo.add_blacklist(tg_user_id=tg_user_id, vk_profile_id=vk_profile_id)
        await message.answer(f'Добавлен в чернй список vk_id={tg_user_id}', reply_markup=kb_more())
    
    ## Показать всех в избранном и перейти в меню действий с избранным
    @router.message(MenuState.more, F.text == 'Показать избранное')
    async def show_all_favorite(message: Message, state: FSMContext) -> None:
        # запоминаем данные кто вызывает избранное
        tg_user_id = message.from_user.id
        # Ищем избранное
        vk_ids = await user_repo.list_favorites(tg_user_id=tg_user_id)

        if not vk_ids:
            await message.answer('Список избранного пуст', reply_markup=kb_more())
            return

        # переходим в меню управления избранным
        await state.set_state(MenuState.favorites)
        # reply клавиатура с кнопками "Удалить из избранного" и "Назад"
        await message.answer('Избранное:', reply_markup=kb_favorite_item())
        # inline кнопки с VK ID для просмотра анкеты
        await message.answer(
            'Кликните на VK ID для просмотра анкеты:',
            reply_markup=kb_favorites_inline(vk_ids)
        )

    # Callback: просмотр анкеты из избранного
    @router.callback_query(F.data.startswith('fav_view:'))
    async def fav_view_callback(callback: CallbackQuery, state: FSMContext) -> None:
        vk_id = int(callback.data.split(':')[1])
        # заглушка — показываем анкету
        await callback.message.answer(
            f'Анкета VK пользователя\n'
            f'ID: {vk_id}\n'
            f'Ссылка: vk.com/id{vk_id}'
        )
        await callback.answer()

    # Меню управления избранным MenuState.favorites
    ## Вернуться на уровень выше
    @router.message(MenuState.favorites, F.text == 'Назад')
    async def back_from_favorite(message: Message, state: FSMContext) -> None:
        await state.set_state(MenuState.more)
        await message.answer("Дополнительные действия:", reply_markup=kb_more())

    ## Переход в режим удаления из избранного
    @router.message(MenuState.favorites, F.text == 'Удалить из избранного')
    async def delete_from_favorite(message: Message, state: FSMContext) -> None:
        tg_user_id = message.from_user.id
        vk_ids = await user_repo.list_favorites(tg_user_id=tg_user_id)

        if not vk_ids:
            await message.answer('Список избранного пуст', reply_markup=kb_more())
            await state.set_state(MenuState.more)
            return

        # переходим в режим удаления
        await state.set_state(MenuState.favorites_delete)
        # reply клавиатура с кнопкой "Назад"
        await message.answer('Режим удаления из избранного:', reply_markup=kb_favorite_back())
        # inline кнопки с VK ID для удаления
        await message.answer(
            'Кликните на VK ID для удаления из избранного:',
            reply_markup=kb_favorites_delete_inline(vk_ids)
        )

    # Callback: удаление из избранного
    @router.callback_query(F.data.startswith('fav_del:'))
    async def fav_del_callback(callback: CallbackQuery, state: FSMContext) -> None:
        vk_id = int(callback.data.split(':')[1])
        tg_user_id = callback.from_user.id

        # удаляем из БД по VK ID
        await user_repo.remove_favorite(tg_user_id=tg_user_id, vk_profile_id=vk_id)

        # показываем обновленный список
        vk_ids = await user_repo.list_favorites(tg_user_id=tg_user_id)

        if not vk_ids:
            # список пуст, возвращаемся в меню Дополнительно
            await callback.message.edit_text('Список избранного пуст')
            await callback.message.answer('Дополнительные действия:', reply_markup=kb_more())
            await state.set_state(MenuState.more)
            await callback.answer('Удалено')
            return

        # обновляем inline клавиатуру с оставшимися VK ID
        await callback.message.edit_text(
            'Кликните на VK ID для удаления из избранного:',
            reply_markup=kb_favorites_delete_inline(vk_ids)
        )
        await callback.answer(f'vk_id={vk_id} удалён из избранного')

    # Вернуться из режима удаления в список избранного
    @router.message(MenuState.favorites_delete, F.text == 'Назад')
    async def back_from_favorites_delete(message: Message, state: FSMContext) -> None:
        tg_user_id = message.from_user.id
        vk_ids = await user_repo.list_favorites(tg_user_id=tg_user_id)

        if not vk_ids:
            await state.set_state(MenuState.more)
            await message.answer('Список избранного пуст. Дополнительные действия:', reply_markup=kb_more())
            return

        await state.set_state(MenuState.favorites)
        await message.answer('Избранное:', reply_markup=kb_favorite_item())
        await message.answer(
            'Кликните на VK ID для просмотра анкеты:',
            reply_markup=kb_favorites_inline(vk_ids)
        )

    return router
