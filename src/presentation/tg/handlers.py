# обработчики: /start, токен, фильтры, навигация, избранное

import asyncio
from pathlib import Path

from src.application.services.auth_service import AuthService
from src.application.services.dating_service import DatingService
from src.application.services.photo_processing_service import PhotoProcessingService
from src.presentation.tg.states import AuthState, FilterState, MenuState
from src.core.exceptions import VkApiError
from src.presentation.tg.keyboards import (
    kb_favorite_item, kb_main, kb_more, kb_start, kb_after_auth,
    kb_favorites_inline, kb_favorites_delete_inline, kb_favorite_back
)
from src.infrastructure.db.repositories import InMemoryUserRepo

from aiogram import Router, F
from aiogram.filters import CommandStart
from aiogram.types import Message, CallbackQuery, InputMediaPhoto, FSInputFile
from aiogram.fsm.context import FSMContext


def setup_handlers(
        user_repo: InMemoryUserRepo,
        auth_service: AuthService,
        dating_service: DatingService,
        photo_service: PhotoProcessingService
) -> Router:
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

    # ожидаем токен от пользователя (Шаг 1/2)
    @router.message(AuthState.waiting_vk_token)
    async def got_vk_token(message: Message, state: FSMContext) -> None:
        """
        Срабатывает, когда бот находится в состоянии ожидания токена.
        1) валидируем что токен не пустой
        2) кладём токен в FSM (state data)
        3) переводим пользователя на шаг 2/2: ввод VK_ID
        """
        token = message.text.strip()

        if not token:
            await message.answer("Токен не может быть пустым! Введите токен еще раз.")
            return

        # сохраняем токен в FSM (в оперативной памяти FSM storage)
        await state.update_data(vk_access_token=token)

        # переключаемся на ожидание VK ID
        await state.set_state(AuthState.waiting_vk_user_id)
        await message.answer("Шаг 2/2: Введите VK_ID")


    # ожидаем от пользователя VK ID (Шаг 2/2)
    @router.message(AuthState.waiting_vk_user_id)
    async def got_vk_id(message: Message, state: FSMContext) -> None:
        """
        Срабатывает, когда бот ждёт VK_ID.
        1) парсим VK_ID
        2) берём токен из FSM
        3) вызываем auth_service.authorize (там VK users.get + сверка владельца токена)
        4) если всё ок — показываем кнопку настройки фильтров
        """
        # 1) Парсим VK_ID
        try:
            vk_user_id = int(message.text.strip())
        except ValueError:
            await message.answer("VK ID должен быть числом! Введите ID еще раз.")
            return

        # 2) Берём токен из FSM (который сохранили на шаге 1/2)
        data = await state.get_data()
        vk_access_token = data.get("vk_access_token")

        if not vk_access_token:
            await message.answer("Токен не найден. Снова авторизуйтесь — нажмите Старт")
            await state.clear()
            return

        tg_user_id = message.from_user.id

        # 3) Валидация + сохранение внутри AuthService
        try:
            await auth_service.authorize(
                tg_user_id=tg_user_id,
                access_token=vk_access_token,
                expected_vk_user_id=vk_user_id,
            )
        except VkApiError as e:
            await message.answer(f"Ошибка VK: {e.msg}\nВведите токен заново.")
            await state.clear()
            await state.set_state(AuthState.waiting_vk_token)
            return

        # 4) Успех: очищаем FSM и показываем следующий шаг
        await state.clear()
        await message.answer("Токен валиден ✅ Данные авторизации записаны ✅", reply_markup=kb_after_auth())

        await asyncio.sleep(1)
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
        await message.answer("Шаг 2/4: Укажите пол для поиска (1=Жен, 2=Муж)")

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
            f"Пол: {'Жен' if gender == 1 else 'Муж'}\n"
            f"Возраст: от {age_from} до {age_to}",
            reply_markup=kb_main()
        )

    # Вспомогательная функция — показать карточку кандидата
    MAX_SKIP = 10  # максимум пропусков кандидатов без фото подряд

    async def show_candidate_card(
            message: Message, state: FSMContext, vk_id: int,
            direction: str = 'next', skip_count: int = 0,
    ) -> None:
        """
        Показывает карточку кандидата: профиль + фото.
        Если фото нет — автопропуск к следующему/предыдущему.
        """
        tg_user_id = message.from_user.id
        await state.update_data(current_vk_profile_id=vk_id)

        # получаем профиль и фото
        profile, photos = await dating_service.get_candidate_card(tg_user_id)

        # скачиваем и обрабатываем фото если ещё не готовы
        if not photos:
            user = await user_repo.get_or_create_user(tg_user_id)
            if user.vk_access_token:
                loading_msg = await message.answer("Ищу фото кандидата...")
                try:
                    photos = await photo_service.fetch_and_save_photos(
                        access_token=user.vk_access_token,
                        vk_user_id=vk_id,
                    )
                except VkApiError:
                    photos = []
                finally:
                    try:
                        await loading_msg.delete()
                    except Exception:
                        pass

        local_photos = [p for p in photos if p.local_path and Path(p.local_path).exists()]

        # если фото нет — пропускаем кандидата автоматически
        if not local_photos:
            if skip_count >= MAX_SKIP:
                await message.answer(
                    "Не удалось найти кандидатов с фото. Попробуйте изменить фильтры.",
                    reply_markup=kb_main()
                )
                return

            try:
                if direction == 'next':
                    next_vk_id = await dating_service.next_candidate(tg_user_id)
                else:
                    next_vk_id = await dating_service.prev_candidate(tg_user_id)
            except VkApiError:
                next_vk_id = None

            if not next_vk_id or next_vk_id == vk_id:
                await message.answer(
                    "Не удалось найти кандидатов с фото. Попробуйте изменить фильтры.",
                    reply_markup=kb_main()
                )
                return

            await show_candidate_card(message, state, next_vk_id, direction, skip_count + 1)
            return

        # формируем текст карточки
        if profile:
            name = f"{profile.first_name} {profile.last_name}".strip()
            link = f"vk.com/{profile.domain}" if profile.domain else f"vk.com/id{vk_id}"
            text = f"{name}\n{link}"
        else:
            text = f"vk.com/id{vk_id}"

        # отправляем фото
        if len(local_photos) >= 2:
            media = []
            for i, photo in enumerate(local_photos):
                inp = FSInputFile(photo.local_path)
                if i == 0:
                    media.append(InputMediaPhoto(media=inp, caption=text))
                else:
                    media.append(InputMediaPhoto(media=inp))
            await message.answer_media_group(media=media)
            await message.answer("Выберите действие:", reply_markup=kb_main())
        else:
            inp = FSInputFile(local_photos[0].local_path)
            await message.answer_photo(photo=inp, caption=text, reply_markup=kb_main())

    # Меню Главное MenuState.main
    ## Переход в меню Дополнительно
    @router.message(MenuState.main, F.text == 'Дополнительно')
    async def menu_more(message: Message, state: FSMContext) -> None:
        await state.set_state(MenuState.more)
        await message.answer('Дополнительные действия', reply_markup=kb_more())

    ## Показать следующего кандидата
    @router.message(MenuState.main, F.text == 'Далее')
    async def main_next(message: Message, state: FSMContext) -> None:
        tg_user_id = message.from_user.id
        try:
            vk_id = await dating_service.next_candidate(tg_user_id)
        except VkApiError as e:
            await message.answer(f"Ошибка VK: {e.msg}", reply_markup=kb_main())
            return

        if not vk_id:
            await message.answer("Кандидаты не найдены. Проверьте фильтры и попробуйте снова.", reply_markup=kb_main())
            return

        await show_candidate_card(message, state, vk_id, direction='next')

        # фоновая предзагрузка следующих 5 анкет
        asyncio.create_task(dating_service.preload_ahead(tg_user_id))

    ## Показать предыдущего кандидата
    @router.message(MenuState.main, F.text == 'Предыдущий')
    async def main_prev(message: Message, state: FSMContext) -> None:
        tg_user_id = message.from_user.id
        try:
            vk_id = await dating_service.prev_candidate(tg_user_id)
        except VkApiError as e:
            await message.answer(f"Ошибка VK: {e.msg}", reply_markup=kb_main())
            return

        if not vk_id:
            await message.answer("Вы в начале списка.", reply_markup=kb_main())
            return

        await show_candidate_card(message, state, vk_id, direction='prev')

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

        data = await state.get_data()
        vk_profile_id = data.get('current_vk_profile_id')
        if not vk_profile_id:
            await message.answer("Сначала нажмите «Далее», чтобы выбрать кандидата.", reply_markup=kb_more())
            return 
        # записываем добавленного в БД
        await user_repo.add_favorite(tg_user_id=tg_user_id, vk_profile_id=vk_profile_id)
        await message.answer(f'Добавлено в избранное vk_id={vk_profile_id}', reply_markup=kb_more())
    
    ## Добавить в черны список
    @router.message(MenuState.more, F.text == 'В черный список')
    async def add_to_black_list(message: Message, state: FSMContext) -> None:
        tg_user_id = message.from_user.id

        data = await state.get_data()
        vk_profile_id = data.get("current_vk_profile_id")

        if not vk_profile_id:
            await message.answer("Сначала нажмите «Далее», чтобы выбрать кандидата.", reply_markup=kb_more())
            return

        await user_repo.add_blacklist(tg_user_id=tg_user_id, vk_profile_id=vk_profile_id)
        await message.answer(f'Добавлен в черный список vk_id={vk_profile_id}', reply_markup=kb_more())
   
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
        vk_profile_id = int(callback.data.split(':')[1])
        tg_user_id = callback.from_user.id

        # профиль и фото из репозитория
        profile = await user_repo.get_profile(vk_profile_id)
        photos = await user_repo.get_photos(vk_profile_id)

        # если фото ещё нет — попробуем скачать
        if not photos:
            user = await user_repo.get_or_create_user(tg_user_id)
            if user.vk_access_token:
                loading_msg = await callback.message.answer("Ищу фото кандидата...")
                try:
                    photos = await photo_service.fetch_and_save_photos(
                        access_token=user.vk_access_token,
                        vk_user_id=vk_profile_id,
                    )
                except VkApiError:
                    photos = []
                finally:
                    try:
                        await loading_msg.delete()
                    except Exception:
                        pass

        # текст карточки
        if profile:
            name = f"{profile.first_name} {profile.last_name}".strip()
            link = f"vk.com/{profile.domain}" if profile.domain else f"vk.com/id{vk_profile_id}"
            text = f"{name}\n{link}"
        else:
            text = f"vk.com/id{vk_profile_id}"

        # отправляем фото
        local_photos = [p for p in photos if p.local_path and Path(p.local_path).exists()]
        if local_photos:
            if len(local_photos) >= 2:
                media = []
                for i, photo in enumerate(local_photos):
                    inp = FSInputFile(photo.local_path)
                    if i == 0:
                        media.append(InputMediaPhoto(media=inp, caption=text))
                    else:
                        media.append(InputMediaPhoto(media=inp))
                await callback.message.answer_media_group(media=media)
            else:
                inp = FSInputFile(local_photos[0].local_path)
                await callback.message.answer_photo(photo=inp, caption=text)
        else:
            await callback.message.answer(text)

        # повторно показываем список избранного
        vk_ids = await user_repo.list_favorites(tg_user_id=tg_user_id)
        if vk_ids:
            await callback.message.answer(
                'Кликните на VK ID для просмотра анкеты:',
                reply_markup=kb_favorites_inline(vk_ids)
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
        vk_profile_id = int(callback.data.split(':')[1])
        tg_user_id = callback.from_user.id

        # удаляем из БД по VK ID
        await user_repo.remove_favorite(tg_user_id=tg_user_id, vk_profile_id=vk_profile_id)

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
        await callback.answer(f'vk_id={vk_profile_id} удалён из избранного')

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
