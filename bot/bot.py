from bot.chat_base import ChatBase
from bot.gpt import GPTClient, GPTOptions
from bot.group_chat import GroupChat
from bot.private_chat import PrivateChat
from bot.tasks_scheduler import TasksScheduler
from dataclasses import dataclass, field
from functools import partial
from telegram import User, Update, constants
from telegram.ext import Application, filters, PicklePersistence, ApplicationBuilder, ContextTypes, CommandHandler, MessageHandler
from telegram.warnings import PTBUserWarning
from uuid import uuid4
from warnings import filterwarnings
import logging
import os

@dataclass
class BotOptions:
    token: str = field(repr=False)
    data_dir: str|None = None
    parse_mode: str = 'MarkdownV2'

@dataclass
class ChatFactory:
    gpt: GPTClient
    bot_options: BotOptions
    bot_user: User

    def create(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> ChatBase:
        chat_id = update.effective_chat.id
        chat_type = update.effective_chat.type
        parse_mode = self.bot_options.parse_mode

        if chat_type in [constants.ChatType.GROUP, constants.ChatType.SUPERGROUP]:
            return GroupChat(self.gpt, context.bot, self.bot_user, chat_id, parse_mode, context.bot_data, context.chat_data)
        else:
            return PrivateChat(self.gpt, context.bot, self.bot_user, chat_id, parse_mode, context.bot_data, context.chat_data)

class Bot:
    def __init__(self, bot_options: BotOptions, gpt_options: GPTOptions):
        self.bot_options = bot_options
        self.gpt_options = gpt_options
        self.tasks_scheduler = TasksScheduler()
        self.chat_dict = dict[int, ChatBase]()

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

        ## Lazy initialization in post_init
        self.chat_factory = None

    async def post_init(self, _: Application):
        logging.debug("Post init, set handlers and commands list")

        bot_user = await self.app.bot.get_me()
        self.chat_factory = ChatFactory(self.gpt, self.bot_options, bot_user)

        self.app.add_handler(CommandHandler('start', self.create_callback(ChatBase.start), block=False))
        self.app.add_handler(MessageHandler(filters.TEXT & filters.UpdateType.MESSAGE & (~filters.COMMAND), self.create_callback(ChatBase.handle_message), block=False))

        # commands = [
        #     ('new', "Start a new conversation"),
        #     ('history', "Show previous conversations"),
        #     ('retry', "Regenerate response for last message"),
        #     ('mode', "Select a mode for current chat and manage modes"),
        #     ('say', "Read out message sent by the bot by replying to it")
        # ]

        # await self.app.bot.set_my_commands(commands)

    async def post_shutdown(self, _: Application):
        logging.debug("Post shutdown")

    def create_callback(self, callback):
        async def handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
            if not update.effective_chat:
                logging.warning(f"Message received but ignored because it doesn't have a chat")
                return

            # Only work in private and group chats
            if update.effective_chat.type not in [constants.ChatType.PRIVATE, constants.ChatType.GROUP, constants.ChatType.SUPERGROUP]:
                logging.warning(f"Message received but ignored because it's not a private or group chat")
                return

            chat_id = update.effective_chat.id

            if chat_id not in self.chat_dict:
                self.chat_dict[chat_id] = self.chat_factory.create(update, context)
            chat = self.chat_dict[chat_id]

            bound_callback = partial(callback, chat)

            await self.tasks_scheduler.append_task(chat_id, bound_callback(update, context.args, context.user_data))
            self.tasks_scheduler.remove_task(chat_id)

        return handler

    def run(self):
        self.app.run_polling()
