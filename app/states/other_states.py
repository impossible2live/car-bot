from aiogram.fsm.state import State, StatesGroup


class InputBalance(StatesGroup):
    waiting_balance = State()
