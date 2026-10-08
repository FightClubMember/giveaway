"""Group and supergroup auto-detection, connection, and giveaway synchronization handlers."""

import logging
from aiogram import Router, F, Bot
from aiogram.types import ChatMemberUpdated, Message, InlineKeyboardMarkup
from aiogram.filters.chat_member_updated import ChatMemberUpdatedFilter, MEMBER, ADMINISTRATOR, KICKED, LEFT
from keyboards.styled_buttons import InlineKeyboardButton

from database.database import get_session
from database.repositories import ConnectedChatRepository

logger = logging.getLogger(__name__)
router = Router(name="groups")


@router.my_chat_member(ChatMemberUpdatedFilter(member_status_changed=(MEMBER | ADMINISTRATOR)))
async def handle_bot_added_to_chat(event: ChatMemberUpdated, bot: Bot) -> None:
    """Auto-detect when bot is added to a group or made admin."""
    chat = event.chat
    if chat.type not in ["group", "supergroup", "channel"]:
        return

    logger.info("Bot added or promoted in %s %d (%s)", chat.type, chat.id, chat.title)

    async with get_session() as session:
        repo = ConnectedChatRepository(session)
        await repo.register_or_update(
            chat_id=chat.id,
            title=chat.title or "Telegram Community",
            chat_type=chat.type,
            username=chat.username,
            is_active=True,
            auto_post_giveaways=True,
        )

    # If it is a group/supergroup, send an onboarding confirmation message
    if chat.type in ["group", "supergroup"]:
        try:
            bot_info = await bot.get_me()
            text = (
                "🎉 <b>JOHN'S GIVEAWAY BOT CONNECTED! 🔥</b>\n\n"
                f"Bhai ye group ab officially <b>@{bot_info.username}</b> ke sath link ho gaya hai!\n\n"
                "🚀 <b>Auto-Post Active:</b> Jab bhi koi naya giveaway create hoga, "
                "uska HD promotional poster aur direct participation button yahan automatic post hoga!\n\n"
                "<i>Tip: Bot ko 'Pin Messages' permission de dena taaki giveaways top par pin rahein!</i>"
            )
            keyboard = InlineKeyboardMarkup(
                inline_keyboard=[[
                    InlineKeyboardButton(
                        text="🎁 Open Bot DM (Start Loot)",
                        url=f"https://t.me/{bot_info.username}?start=group_{chat.id}",
                        style="success",
                    )
                ]]
            )
            await bot.send_message(
                chat_id=chat.id,
                text=text,
                parse_mode="HTML",
                reply_markup=keyboard,
            )
        except Exception as e:
            logger.warning("Could not send group greeting message: %s", e)


@router.my_chat_member(ChatMemberUpdatedFilter(member_status_changed=(KICKED | LEFT)))
async def handle_bot_removed_from_chat(event: ChatMemberUpdated) -> None:
    """Deactivate auto-post when bot is removed from a chat."""
    chat = event.chat
    logger.info("Bot removed from %s %d (%s)", chat.type, chat.id, chat.title)
    async with get_session() as session:
        repo = ConnectedChatRepository(session)
        await repo.deactivate(chat.id)


@router.message(F.text.startswith("/connect"))
async def handle_manual_connect_command(message: Message, bot: Bot) -> None:
    """Manual trigger in group to verify / sync connection."""
    chat = message.chat
    if chat.type not in ["group", "supergroup"]:
        return

    async with get_session() as session:
        repo = ConnectedChatRepository(session)
        await repo.register_or_update(
            chat_id=chat.id,
            title=chat.title or "Telegram Community",
            chat_type=chat.type,
            username=chat.username,
            is_active=True,
            auto_post_giveaways=True,
        )

    await message.reply(
        "✅ <b>Group Connected & Synced!</b>\n\n"
        "Ye group registered hai. Naye giveaways create hone par yahan auto-post honge! 🔥",
        parse_mode="HTML",
    )
