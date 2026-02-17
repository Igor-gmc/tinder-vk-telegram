# FSM: ввод токена, настройка фильтров (4 вопроса)  

from aiogram.fsm.state import StatesGroup, State

# ввод токена VK, затем ввод VK ID
class AuthState(StatesGroup):
    waiting_vk_token = State()
    waiting_vk_user_id = State()

# состояние фильтров
class FilterState(StatesGroup):
    waiting_city = State()
    waiting_gender = State()
    waiting_age_from = State()
    waiting_age_to = State()