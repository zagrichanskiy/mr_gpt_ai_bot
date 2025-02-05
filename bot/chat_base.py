from abc import ABC, abstractmethod
from bot.gpt import GPTClient
from bot.thread import Thread
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from telegram import constants, error, Update, Message, User
from telegram.ext import Application, ExtBot
from telegramify_markdown import markdownify
from typing import Any
import asyncio
import logging
import tempfile
import os, json

@dataclass
class Formatter:
    parse_mode: constants.ParseMode|None = None

    def format(self, text: str) -> str:
        if not self.parse_mode:
            return text
        elif (self.parse_mode == constants.ParseMode.MARKDOWN_V2):
            return markdownify(text)
        return text

class ChatBase(ABC):
    EDIT_TIMEOUT = 2

    def __init__(self, gpt: GPTClient, app: Application, bot: ExtBot, bot_user: User, chat_id: int, parse_mode: constants.ParseMode, bot_data: dict[Any, Any], chat_data: dict[Any, Any]):
        self.gpt: GPTClient = gpt
        self.app = app
        self.bot = bot
        self.bot_user = bot_user
        self.chat_id = chat_id
        self.formatter = Formatter(parse_mode)
        self.bot_data = bot_data
        self.chat_data = chat_data
        self.thread = self.chat_data.setdefault('thread', gpt.make_thread(self.chat_id))

        logging.info(f"New Chat[{self.chat_id}] opened")

    @abstractmethod
    def is_valid_message(self, message: Message) -> bool:
        pass

    @abstractmethod
    def get_reply_to_message_id(self, message: Message) -> int|None:
        pass

    async def edit_message_text(self, message: Message, text: str) -> Message:
        try:
            return await message.edit_text(
                text=self.formatter.format(text),
                parse_mode=self.formatter.parse_mode
            )
        except error.BadRequest as ex:
            what = str(ex)
            if self.formatter.parse_mode and "Can't parse entities" in what:
                logging.warning(f"Error editing message: {text}: {ex}, falling back to plain text format")
                return await message.edit_text(text)
            else:
                raise

    async def reply_message_text(self, message: Message, text: str) -> Message:
        try:
            return await message.reply_text(
                reply_to_message_id=self.get_reply_to_message_id(message),
                text=self.formatter.format(text),
                parse_mode=self.formatter.parse_mode
            )
        except error.BadRequest as ex:
            what = str(ex)
            if self.formatter.parse_mode and "Can't parse entities" in what:
                logging.warning(f"Error sending the message: {text}: {ex}, falling back to plain text format")
                return await message.reply_text(
                    reply_to_message_id=self.get_reply_to_message_id(message),
                    text=text
                )
            else:
                raise

    async def reply_message_document(self, message: Message, document, filename, caption) -> Message:
        return await message.reply_document(
            reply_to_message_id=self.get_reply_to_message_id(message),
            document=document,
            filename=filename,
            caption=self.formatter.format(caption),
        )

    async def start(self, update: Update, args: list[str] | None, user_data: dict[Any, Any]):
        await self.bot.send_message(chat_id=self.chat_id, text="Start by sending me a message!")
        logging.info(f"Start command executed for chat {self.chat_id}")

    async def show_chats(self, update: Update, args: list[str] | None, user_data: dict[Any, Any]):
        app_chat_data = self.app.chat_data

        chat_list = []
        for chat_id in app_chat_data.keys():
            chat = await self.bot.get_chat(chat_id)
            chat_name = chat.title or chat.full_name or f"Chat {chat_id}"
            chat_name += f" (@{chat.username})" if chat.username else ""
            chat_list.append(f"{len(chat_list) + 1}. {chat_name}: *{chat_id}*")

        message = f"📋 **Active Chats:**\n\n" + "\n".join(chat_list)

        await self.reply_message_text(update.message, message)

    async def show_history(self, update: Update, args: list[str] | None, user_data: dict[Any, Any]):
        if not args:
            chat_id = self.chat_id
        else:
            try:
                chat_id = int(args[0])
            except ValueError:
                await self.reply_message_text(update.message, "Invalid chat ID format. Must be an integer.")

        chat_data = self.app.chat_data.get(chat_id)
        if not chat_data:
            await self.reply_message_text(update.message, f"Chat {chat_id} not found")
            return

        thread = chat_data.get("thread")

        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.txt') as temp_file:
            json.dump(asdict(thread), temp_file, default=str, indent=2, ensure_ascii=False)

        try:
            await self.reply_message_document(
                update.message,
                open(temp_file.name, 'rb'),
                f"chat_{chat_id}_history_{datetime.now(timezone.utc).isoformat()}.txt",
                f"History of chat {chat_id}"
            )
        finally:
            os.remove(temp_file.name)

    async def handle_message(self, update: Update, args: list[str] | None, user_data: dict[Any, Any]):
        if not update.message or not update.message.text:
            logging.warning(f"Update received but ignored because it doesn't have a message")
            return

        if not self.is_valid_message(update.message):
            return

        sent_message = await self.reply_message_text(update.message, "Generating response...")
        self.thread.add_user_message(update.message)

        await self.edit_with_gpt_response(sent_message)

    async def edit_with_gpt_response(self, sent_message: Message):
        try:
            assistant_response: str = ''
            last_update_time = asyncio.get_running_loop().time()

            async for chunk in self.gpt.stream_response(self.thread):
                assistant_response += chunk

                if asyncio.get_running_loop().time() - last_update_time >= self.EDIT_TIMEOUT:
                    sent_message = await self.edit_message_text(sent_message, assistant_response + '\n\nGenerating...')
                    last_update_time = asyncio.get_running_loop().time()

            if assistant_response:
                sent_message = await self.edit_message_text(sent_message, assistant_response)

            self.thread.add_assistant_message(sent_message)

            logging.debug(f"Replied chat {self.chat_id} with message '{assistant_response}'")

        except Exception as ex:
            await self.edit_message_text(sent_message, f"Error generating response: {ex}")
            logging.error(f"Error generating response for chat {self.chat_id}: {str(type(ex).__name__)}: {ex}")
