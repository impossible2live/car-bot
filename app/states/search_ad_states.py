from aiogram.fsm.state import State, StatesGroup


class SearchAdStates(StatesGroup):
    waiting_filter_city = State()
    waiting_filter_name = State()
    waiting_filter_year = State()
    waiting_filter_condition = State()
    waiting_filter_fuel_type = State()
    waiting_filter_mileage = State()
    waiting_filter_price = State()
    waiting_filter_engine_volume = State()
    waiting_filter_transmission = State()
    waiting_filter_body_type = State()
    waiting_filter_color = State()



