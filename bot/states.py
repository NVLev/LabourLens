from aiogram.fsm.state import State, StatesGroup


class SituationStates(StatesGroup):
    choosing_group = State()  # выбор группы из SECTOR_GROUPS
    choosing_sector = State()  # выбор сектора внутри группы
    choosing_topic = State()  # выбор темы
    entering_details = State()  # опционально: тип договора, стаж
    showing_result = State()  # показ ответа
