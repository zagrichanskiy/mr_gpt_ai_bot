import asyncio
import logging
import os
from chat import ChatData, ChatManager, ChatState, ChatContext
from dataclasses import dataclass, field
from enum import Enum
from gpt import GPTClient
from speech import SpeechClient
from telegram import Update, constants
from telegram.ext import InlineQueryHandler, Application, CallbackQueryHandler, ConversationHandler, PicklePersistence, filters, ApplicationBuilder, ContextTypes, CommandHandler, MessageHandler
from telegram.warnings import PTBUserWarning
from typing import cast
from uuid import uuid4
from warnings import filterwarnings

async def __start(_: Update, chat_manager: ChatManager):
  chat_id = chat_manager.context.chat_id

  await chat_manager.bot.send_message(chat_id=chat_id, text="Start by sending me a message!")

  logging.info(f"Start command executed for chat {chat_id}")

async def __handle_message(update: Update, chat_manager: ChatManager):
  if not update.message or not update.message.text:
    logging.warning(f"Update received but ignored because it doesn't have a message")
    return

  text = update.message.text
  if (update.message.chat.type in [constants.ChatType.GROUP, constants.ChatType.SUPERGROUP]):
    bot_user = await chat_manager.bot.get_me()
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

  await chat_manager.handle_message(text=text, update=update)

async def __handle_audio(update: Update, chat_manager: ChatManager):
  if not update.message or not update.message.voice:
    logging.warning(f"Update received but ignored because it doesn't have a message")
    return

  file = await update.message.voice.get_file()
  audio = await file.download_as_bytearray()

  logging.info(f"Received audio from chat {chat_manager.context.chat_id}")

  await chat_manager.handle_audio(audio=audio, user_message_id=update.message.id)

async def __retry_last_message(update: Update, chat_manager: ChatManager):
  query = update.callback_query
  if query:
    await query.answer()
    if query.message:
      await chat_manager.bot.delete_message(chat_id=query.message.chat_id, message_id=query.message.message_id)
  await chat_manager.retry_last_message()

async def __resume(update: Update, chat_manager: ChatManager):
  query = update.callback_query

  if query and query.data and query.data.startswith('/resume_'):
    await query.answer()
    conversation_id = int(query.data.split('_')[1])
  elif update.message and update.message.text and update.message.text.startswith('/resume_'):
    conversation_id = int(update.message.text.split('_')[1])
  else:
    raise Exception("Invalid parameters")

  await chat_manager.resume(conversation_id=conversation_id)

async def __new_conversation(_: Update, chat_manager: ChatManager):
  await chat_manager.new_conversation()

async def __show_conversation_history(_: Update, chat_manager: ChatManager):
  await chat_manager.show_conversation_history()

async def __read_out_message(update: Update, chat_manager: ChatManager):
  if not update.message or not update.message.reply_to_message:
    await chat_manager.bot.send_message(chat_id=chat_manager.context.chat_id, text="Please reply to a message to read it out loud")
    return

  await chat_manager.read_out_message(message_id=update.message.reply_to_message.id)

async def __set_mode(update: Update, chat_manager: ChatManager):
  if update.callback_query:
    await update.callback_query.answer()
  await chat_manager.list_modes_for_selection()

async def __edit_modes(_: Update, chat_manager: ChatManager):
  await chat_manager.show_modes()

async def __mode_show_detail(update: Update, chat_manager: ChatManager):
  query = update.callback_query
  if query and query.data and query.data.startswith('/mode_detail_'):
    await query.answer()
    mode_id = query.data[len('/mode_detail_'):]
  else:
    raise Exception("Invalid parameters")

  await chat_manager.show_mode_detail(mode_id)

async def __mode_select(update: Update, chat_manager: ChatManager):
  query = update.callback_query
  if query and query.data and query.data.startswith('/mode_select_') and query.message:
    await query.answer()
    mode_id = query.data[len('/mode_select_'):]
  else:
    raise Exception("Invalid parameters")

  await chat_manager.select_mode(mode_id, query.message.id)

async def __mode_clear(update: Update, chat_manager: ChatManager):
  query = update.callback_query
  if query and query.message:
    await query.answer()
  else:
    raise Exception("Invalid parameters")

  await chat_manager.select_mode(None, query.message.id)

async def __mode_delete(update: Update, chat_manager: ChatManager):
  query = update.callback_query
  if query and query.data and query.data.startswith('/mode_delete_') and query.message:
    await query.answer()
    mode_id = query.data[len('/mode_delete_'):]
  else:
    raise Exception("Invalid parameters")

  await chat_manager.delete_mode(mode_id, query.message.id)


class ModeEditState(Enum):
  INIT = 0
  ENTER_TITLE = 1
  ENTER_PROMPT = 2

async def __mode_add_start(_: Update, chat_manager: ChatManager) -> ModeEditState:
  chat_id = chat_manager.context.chat_id
  await chat_manager.bot.send_message(chat_id=chat_id, text="Enter a title for the new mode:")

  return ModeEditState.ENTER_TITLE

async def __mode_edit_start(update: Update, chat_manager: ChatManager) -> ModeEditState|None:
  query = update.callback_query
  if query and query.data and query.data.startswith('/mode_edit_'):
    await query.answer()
    mode_id = query.data[len('/mode_edit_'):]
  else:
    raise Exception("Invalid parameters")

  if not await chat_manager.edit_mode(mode_id):
    return

  return ModeEditState.ENTER_PROMPT

async def __mode_enter_title(update: Update, chat_manager: ChatManager) -> ModeEditState|None:
  if not update.message or not update.message.text:
    await chat_manager.bot.send_message(chat_id=chat_manager.context.chat_id, text="Invalid title. Please try again.")
    logging.warning(f"Update received but ignored because it doesn't have a message")
    return

  if not await chat_manager.update_mode_title(update.message.text):
    return

  await chat_manager.bot.send_message(chat_id=chat_manager.context.chat_id, text="Enter a prompt for the new mode:")

  return ModeEditState.ENTER_PROMPT

async def __mode_enter_prompt(update: Update, chat_manager: ChatManager) -> int|None:
  if not update.message or not update.message.text:
    await chat_manager.bot.send_message(chat_id=chat_manager.context.chat_id, text="Invalid prompt. Please try again.")
    logging.warning(f"Update received but ignored because it doesn't have a message")
    return

  await chat_manager.add_or_edit_mode(update.message.text)

  return ConversationHandler.END

async def __mode_add_cancel(_: Update, chat_manager: ChatManager) -> int:
  await chat_manager.bot.send_message(chat_id=chat_manager.context.chat_id, text="Mode creation cancelled.")

  return ConversationHandler.END


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

def __create_callback(gpt: GPTClient, speech: SpeechClient|None, chat_tasks: dict[int, asyncio.Task], allowed_chat_ids: set[int], conversation_timeout: int|None, chat_states: dict[int, ChatState], callback):
  async def invoke(update: Update, context: ContextTypes.DEFAULT_TYPE, chat_id: int):
    if chat_id not in chat_states:
      chat_states[chat_id] = ChatState()
    chat_state = chat_states[chat_id]

    chat_data = cast(ChatData, context.chat_data)
    chat_context = ChatContext(chat_id, chat_state, chat_data)

    chat_manager = ChatManager(gpt=gpt, speech=speech, bot=context.bot, context=chat_context, conversation_timeout=conversation_timeout)

    return await callback(update, chat_manager)

  async def handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.effective_chat:
      logging.warning(f"Message received but ignored because it doesn't have a chat")
      return

    chat_id = update.effective_chat.id

    if len(allowed_chat_ids) > 0 and not chat_id in allowed_chat_ids:
      logging.info(f"Message received for chat {chat_id} but ignored because it's not the configured chat")
      return

    current_task = chat_tasks.get(chat_id)
    async def task():
      if current_task:
        try:
          await current_task
        except Exception as e:
          logging.warning(f"Error {e} in previous task for chat {chat_id}")
      return await invoke(update, context, chat_id)

    chat_tasks[chat_id] = asyncio.create_task(task())
    result = await chat_tasks[chat_id]
    if chat_id in chat_tasks:
      del chat_tasks[chat_id]

    return result

  return handler

def run(token: str, gpt: GPTClient, speech: SpeechClient|None, options: BotOptions):
  chat_tasks = {}
  chat_states = {}

  def create_callback(callback):
    return __create_callback(gpt, speech, chat_tasks, options.allowed_chat_ids, options.conversation_timeout, chat_states, callback)

  async def post_init(app: Application):
    commands = [
      ('new', "Start a new conversation"),
      ('history', "Show previous conversations"),
      ('retry', "Regenerate response for last message"),
      ('mode', "Select a mode for current chat and manage modes"),
      ('say', "Read out message sent by the bot by replying to it")
    ]
    await app.bot.set_my_commands(commands)
    logging.info("Set command list")

  async def post_shutdown(_: Application):
    if speech:
      await speech.close()

  app_builder = ApplicationBuilder().token(token).post_init(post_init).post_shutdown(post_shutdown)
  if options.data_dir:
    persistence = PicklePersistence(os.path.join(options.data_dir, 'data'))
    app_builder.persistence(persistence)
  app = app_builder.build()

  filterwarnings(action="ignore", message=r".*CallbackQueryHandler", category=PTBUserWarning)

  app.add_handler(CommandHandler('start', create_callback(__start), block=False))

  app.add_handler(CommandHandler('new', create_callback(__new_conversation), block=False))

  app.add_handler(CommandHandler('retry', create_callback(__retry_last_message), block=False))
  app.add_handler(CallbackQueryHandler(create_callback(__retry_last_message), pattern=r'^/retry$', block=False))

  app.add_handler(MessageHandler(filters.COMMAND & filters.Regex(r'\/resume_\d+'), create_callback(__resume), block=False))
  app.add_handler(CallbackQueryHandler(create_callback(__resume), pattern=r'^\/resume_\d+$', block=False))

  app.add_handler(CommandHandler('history', create_callback(__show_conversation_history), block=False))
  app.add_handler(CommandHandler('say', create_callback(__read_out_message), block=False))

  app.add_handler(CommandHandler('mode', create_callback(__set_mode), block=False))
  app.add_handler(CallbackQueryHandler(create_callback(__set_mode), pattern=r'^/mode$', block=False))
  app.add_handler(CallbackQueryHandler(create_callback(__edit_modes), pattern=r'^\/mode_show$', block=False))
  app.add_handler(CallbackQueryHandler(create_callback(__mode_show_detail), pattern=r'\/mode_detail_.+', block=False))
  app.add_handler(CallbackQueryHandler(create_callback(__mode_select), pattern=r'\/mode_select_.+', block=False))
  app.add_handler(CallbackQueryHandler(create_callback(__mode_clear), pattern=r'^\/mode_clear$', block=False))
  app.add_handler(CallbackQueryHandler(create_callback(__mode_delete), pattern=r'\/mode_delete_.+', block=False))

  app.add_handler(ConversationHandler(
                    entry_points=[
                      CallbackQueryHandler(create_callback(__mode_add_start), pattern=r'^\/mode_add$', block=False),
                      CallbackQueryHandler(create_callback(__mode_edit_start), pattern=r'\/mode_edit_.+', block=False),
                    ],
                    states={
                      ModeEditState.ENTER_TITLE: [MessageHandler(filters.TEXT & filters.UpdateType.MESSAGE & (~filters.COMMAND), create_callback(__mode_enter_title), block=False)],
                      ModeEditState.ENTER_PROMPT: [MessageHandler(filters.TEXT & filters.UpdateType.MESSAGE & (~filters.COMMAND), create_callback(__mode_enter_prompt), block=False)],
                    },
                    fallbacks=[CommandHandler('cancel', create_callback(__mode_add_cancel), block=False)],
                  ))

  app.add_handler(MessageHandler(filters.TEXT & filters.UpdateType.MESSAGE & (~filters.COMMAND), create_callback(__handle_message), block=False))
  app.add_handler(MessageHandler(filters.VOICE & filters.UpdateType.MESSAGE, create_callback(__handle_audio), block=False))

  if options.webhook:
    host, port = options.webhook.host_and_port
    app.run_webhook(
      host,
      port,
      webhook_url=options.webhook.url,
      secret_token=str(uuid4()),
    )
  else:
    app.run_polling()
