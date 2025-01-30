import logging
import os
from chat import ChatData, ChatManager, ChatState, ChatContext
from dataclasses import dataclass, field
from enum import Enum
from tasks_scheduler import TasksScheduler
from gpt import GPTClient
from telegram import Chat, Update, constants
from telegram.ext import Application, filters, ConversationHandler, PicklePersistence, ApplicationBuilder, ContextTypes, CommandHandler, MessageHandler
from telegram.warnings import PTBUserWarning
from typing import cast
from uuid import uuid4
from warnings import filterwarnings
from gpt import GPTClient, GPTOptions
from chat_v2 import ChatV2
from functools import partial

@dataclass
class WebhookOptions:
  url: str
  listen_address: str

  @property
  def host_and_port(self):
    parts = self.listen_address.split(':')
    host = parts[0]
    port = int(parts[1] if len(parts) > 1 else 80)
    return (host, port)

  def __init__(self, url: str, listen_address: str):
    self.url = url
    self.listen_address = listen_address

@dataclass
class BotOptions:
  token: str = field(repr=False)
  allowed_chat_ids: set[int]
  conversation_timeout: int|None = None
  data_dir: str|None = None
  webhook: WebhookOptions|None = None

class Bot:
  def __init__(self, bot_options: BotOptions, gpt_options: GPTOptions):
    self.bot_options = bot_options
    self.gpt_options = gpt_options
    self.tasks_scheduler = TasksScheduler()
    self.chat_dict = dict[int, ChatV2]()

    filterwarnings(action="ignore", message=r".*CallbackQueryHandler", category=PTBUserWarning)

    token = bot_options.token
    app_builder = ApplicationBuilder().token(token).post_init(self.post_init).post_shutdown(self.post_shutdown)
    if bot_options.data_dir:
      persistence = PicklePersistence(os.path.join(bot_options.data_dir, 'data'))
      app_builder.persistence(persistence)
    self.app = app_builder.build()
    self.bot_data = self.app.bot_data

    logging.info(f"Initializing GPTClient with options: {gpt_options}")
    self.gpt = GPTClient(options=gpt_options)

  async def post_init(self, _: Application):
    logging.info("Post init")

    self.app.add_handler(CommandHandler('start', self.create_callback(ChatV2.start), block=False))
    self.app.add_handler(MessageHandler(filters.TEXT & filters.UpdateType.MESSAGE & (~filters.COMMAND), self.create_callback(ChatV2.handle_message), block=False))

    commands = [
      ('new', "Start a new conversation"),
      ('history', "Show previous conversations"),
      ('retry', "Regenerate response for last message"),
      ('mode', "Select a mode for current chat and manage modes"),
      ('say', "Read out message sent by the bot by replying to it")
    ]

    await self.app.bot.set_my_commands(commands)
    logging.info("Set command list")

  async def post_shutdown(self, _: Application):
    logging.info("Post shutdown")

  def create_callback(self, callback):
    async def handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
      if not update.effective_chat:
        logging.warning(f"Message received but ignored because it doesn't have a chat")
        return

      chat_id = update.effective_chat.id

      if chat_id not in self.chat_dict:
        self.chat_dict[chat_id] = ChatV2(self.gpt, context.bot, chat_id, context.bot_data, context.chat_data)
      chat = self.chat_dict[chat_id]

      bound_callback = partial(callback, chat)

      result = await self.tasks_scheduler.append_task(chat_id, bound_callback(update, context.args, context.user_data))
      self.tasks_scheduler.remove_task(chat_id)

      return result
    return handler

  def run(self):
    if self.bot_options.webhook:
      host, port = self.bot_options.webhook.host_and_port
      self.app.run_webhook(
        host,
        port,
        webhook_url=self.bot_options.webhook.url,
        secret_token=str(uuid4()),
      )
    else:
      self.app.run_polling()
