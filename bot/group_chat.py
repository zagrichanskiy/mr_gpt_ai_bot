from bot.chat_base import ChatBase
from telegram import Message

class GroupChat(ChatBase):
    def is_valid_message(self, message: Message) -> bool:
        text = message.text

        mentioned = f"@{self.bot_user.username}" in text
        quoted = (
            message.reply_to_message # message is a reply in thread
            and message.reply_to_message.from_user.id == self.bot_user.id # message is a reply to the bot's message
            and message.from_user.id != self.bot_user.id # message is not from the bot
        )

        return mentioned or quoted

    def get_reply_to_message_id(self, message: Message) -> int|None:
        return message.message_id
