import logging
from typing import Any, cast
from telegram import Update
from gpt import GPTClient
from telegram.ext import ExtBot
from telegram import constants
from models import UserMessage, Conversation, SystemMessage
import asyncio
from dataclasses import dataclass

@dataclass
class ChatState:
  timeout_task: asyncio.Task|None = None
  current_conversation: Conversation|None = None

class ChatV2:
  def __init__(self, gpt: GPTClient, bot: ExtBot, chat_id: int, bot_data: dict[Any, Any], chat_data: dict[Any, Any]):
    self.gpt = gpt
    self.bot = bot
    self.chat_id = chat_id
    self.bot_data = bot_data
    self.chat_data = chat_data
    self.chat_state = ChatState()

  async def start(self, update: Update, args: list[str] | None, user_data: dict[Any, Any]):
    await self.bot.send_message(chat_id=self.chat_id, text="Start by sending me a message!")

    logging.info(f"Start command executed for chat {self.chat_id}")

  async def handle_message(self, update: Update, args: list[str] | None, user_data: dict[Any, Any]):
    if not update.message or not update.message.text:
      logging.warning(f"Update received but ignored because it doesn't have a message")
      return

    text = update.message.text
    if (update.message.chat.type in [constants.ChatType.GROUP, constants.ChatType.SUPERGROUP]):
      bot_user = await self.bot.get_me()
      bot_username = bot_user.username
      bot_id = bot_user.id
      mentioned = False
      quouted = False

      if bot_username in text:
        mentioned = True
        text = text.replace(f"@{bot_username}", "").strip()

      if update.message.reply_to_message and update.message.reply_to_message.from_user.id == bot_id:
        quouted = True

      if not mentioned and not quouted:
        return

    user_message_id = update.message.message_id

    # sent_message = await self.bot.send_message(chat_id=self.context.chat_id, text="Generating response...")
    sent_message = await update.effective_message.reply_text(
      message_thread_id=self.get_thread_id(update),
      reply_to_message_id=self.get_reply_to_message_id(update),
      text="Generating response..."
    )

    user_message = UserMessage(user_message_id, text)

    conversation = self.chat_state.current_conversation
    if conversation:
      conversation.messages.append(user_message)
    else:
      conversation = self.__create_conversation(user_message)

    await self.__complete(conversation, sent_message.id)

  def get_thread_id(self, update: Update) -> int | None:
    if update.effective_message and update.effective_message.is_topic_message:
      return update.effective_message.message_thread_id
    return None
  
  def is_group_chat(self, update: Update) -> bool:
      if not update.effective_chat:
          return False
      return update.effective_chat.type in [
          constants.ChatType.GROUP,
          constants.ChatType.SUPERGROUP
      ]
  
  def get_reply_to_message_id(self, update: Update):
    if self.is_group_chat(update):
      return update.message.message_id
    return None

  def all_conversations(self) -> dict[int, Conversation]:
    if 'conversations' not in self.chat_data:
      self.chat_data['conversations'] = {}
    return self.chat_data['conversations']

  def __create_conversation(self, user_message: UserMessage) -> Conversation:
    current_conversation = self.chat_state.current_conversation
    if current_conversation:
      current_conversation.messages.append(user_message)
      return current_conversation
    else:
      conversations = self.all_conversations()
      conversation = self.gpt.new_conversation(len(conversations), user_message)
      conversations[conversation.id] = conversation

      return conversation

  async def __complete(self, conversation: Conversation, sent_message_id: int):
    chat_id = self.chat_id
    try:
      system_prompt = None
      final_message = None

      last_update_task = None
      last_update_time = asyncio.get_running_loop().time()

      async for message in self.gpt.complete(conversation, cast(UserMessage, conversation.last_message), sent_message_id, system_prompt):
        final_message = message

        if last_update_task and not last_update_task.done():
          continue

        now = asyncio.get_running_loop().time()
        if now - last_update_time < 2:
          continue

        last_update_time = now
        last_update_task = asyncio.create_task(self.bot.edit_message_text(chat_id=chat_id, message_id=sent_message_id, text=message.content + '\n\nGenerating...'))

      if final_message:
        await self.bot.edit_message_text(chat_id=chat_id, message_id=sent_message_id, text=final_message.content)

      logging.info(f"Replied chat {chat_id} with message '{final_message}'")
    except TimeoutError:
      await self.bot.edit_message_text(chat_id=chat_id, message_id=sent_message_id, text="Generation timed out.")
      logging.info(f"Timed out generating response for chat {chat_id}")
    except Exception as e:
      await self.bot.edit_message_text(chat_id=chat_id, message_id=sent_message_id, text="Error generating response")
      logging.error(f"Error generating response for chat {chat_id}: {e}")

    self.chat_state.current_conversation = conversation
