from aiogram.fsm.state import State, StatesGroup


class AdvertStates(StatesGroup):
    waiting_name = State()
    waiting_year = State()
    waiting_condition = State()
    waiting_fuel_type = State()
    waiting_mileage = State()
    waiting_price = State()
    waiting_engine_volume = State()
    waiting_transmission = State()
    waiting_body_type = State()
    waiting_color = State()
    waiting_vin = State()
    waiting_license_plate = State()
    waiting_contacts = State()
    waiting_city = State()
    waiting_description = State()
    waiting_confirmation = State()
    waiting_photos = State()

    waiting_autoteka_decision = State()
    waiting_autoteka_report = State()


