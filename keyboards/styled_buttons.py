"""Telegram Bot API 9.4 Colorful Button Subclasses.

Subclasses KeyboardButton and InlineKeyboardButton for both aiogram and pyTelegramBotAPI (telebot)
so that passing style='primary' (Blue 🔵), style='success' (Green 🟢), and style='danger' (Red 🔴)
adds the 'style' field into the button JSON dictionary.
"""

from typing import Optional, Literal, Dict, Any
from aiogram.types import (
    InlineKeyboardButton as AiogramBaseInlineButton,
    KeyboardButton as AiogramBaseKeyboardButton,
)

# Style type definition matching Telegram Bot API 9.4 specification
StyleType = Optional[Literal["primary", "success", "danger"]]


# ==========================================
# 1. AIOGRAM 3.x SUBCLASSES (Used by Bot)
# ==========================================
class InlineKeyboardButton(AiogramBaseInlineButton):
    """Aiogram InlineKeyboardButton with Telegram Bot API 9.4 colorful button styles.

    Styles supported:
    - 'primary': Blue 🔵
    - 'success': Green 🟢
    - 'danger':  Red 🔴
    """
    style: StyleType = None


class KeyboardButton(AiogramBaseKeyboardButton):
    """Aiogram KeyboardButton with Telegram Bot API 9.4 colorful button styles.

    Styles supported:
    - 'primary': Blue 🔵
    - 'success': Green 🟢
    - 'danger':  Red 🔴
    """
    style: StyleType = None


# ==========================================
# 2. TELEBOT / PyTelegramBotAPI SUBCLASSES
# ==========================================
try:
    import telebot.types as telebot_types

    class TelebotInlineKeyboardButton(telebot_types.InlineKeyboardButton):
        """pyTelegramBotAPI (telebot) InlineKeyboardButton with API 9.4 style support."""

        def __init__(self, text: str, style: StyleType = None, **kwargs):
            super().__init__(text, **kwargs)
            self.style = style

        def to_dict(self) -> Dict[str, Any]:
            data = super().to_dict()
            if self.style:
                data["style"] = self.style
            return data

    class TelebotKeyboardButton(telebot_types.KeyboardButton):
        """pyTelegramBotAPI (telebot) KeyboardButton with API 9.4 style support."""

        def __init__(self, text: str, style: StyleType = None, **kwargs):
            super().__init__(text, **kwargs)
            self.style = style

        def to_dict(self) -> Dict[str, Any]:
            data = super().to_dict()
            if self.style:
                data["style"] = self.style
            return data

    def patch_telebot():
        """Monkey-patch telebot.types to automatically support the 'style' keyword argument."""
        orig_inline_init = telebot_types.InlineKeyboardButton.__init__
        orig_inline_to_dict = telebot_types.InlineKeyboardButton.to_dict
        orig_kb_init = telebot_types.KeyboardButton.__init__
        orig_kb_to_dict = telebot_types.KeyboardButton.to_dict

        def patched_inline_init(self, text, style=None, **kwargs):
            orig_inline_init(self, text, **kwargs)
            self.style = style

        def patched_inline_to_dict(self):
            d = orig_inline_to_dict(self)
            if getattr(self, "style", None):
                d["style"] = self.style
            return d

        def patched_kb_init(self, text, style=None, **kwargs):
            orig_kb_init(self, text, **kwargs)
            self.style = style

        def patched_kb_to_dict(self):
            d = orig_kb_to_dict(self)
            if getattr(self, "style", None):
                d["style"] = self.style
            return d

        telebot_types.InlineKeyboardButton.__init__ = patched_inline_init
        telebot_types.InlineKeyboardButton.to_dict = patched_inline_to_dict
        telebot_types.KeyboardButton.__init__ = patched_kb_init
        telebot_types.KeyboardButton.to_dict = patched_kb_to_dict

    # Auto-patch telebot upon import
    patch_telebot()

except ImportError:
    # Telebot not installed in this environment
    TelebotInlineKeyboardButton = None  # type: ignore
    TelebotKeyboardButton = None  # type: ignore
