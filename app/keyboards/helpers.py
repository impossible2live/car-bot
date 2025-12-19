from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton


def quick_reply(buttons: list, row_width: int = 3, first_single: bool = True) -> ReplyKeyboardMarkup:

    keyboard = []

    if not buttons:
        return ReplyKeyboardMarkup(keyboard=[], resize_keyboard=True)

    if first_single and buttons:
        keyboard.append([KeyboardButton(text=buttons[0])])
        buttons = buttons[1:]

    row = []
    for i, text in enumerate(buttons):
        row.append(KeyboardButton(text=text))
        if (i + 1) % row_width == 0:
            keyboard.append(row)
            row = []

    if row:
        keyboard.append(row)


    return ReplyKeyboardMarkup(keyboard=keyboard, resize_keyboard=True)


def quick_inline(buttons: list, row_width: int = 3, first_single: bool = True) -> InlineKeyboardMarkup:

    keyboard = []

    if not buttons:
        return InlineKeyboardMarkup(inline_keyboard=[])

    if first_single and buttons:
        text, callback_data = buttons[0]
        keyboard.append([InlineKeyboardButton(text=text, callback_data=callback_data)])
        buttons = buttons[1:]

    row = []
    for i, (text, callback_data) in enumerate(buttons):
        row.append(InlineKeyboardButton(text=text, callback_data=callback_data))
        if (i + 1) % row_width == 0:
            keyboard.append(row)
            row = []

    if row:
        keyboard.append(row)

    return InlineKeyboardMarkup(inline_keyboard=keyboard)