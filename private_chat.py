from telegram import Message
from chat_base import ChatBase

class PrivateChat(ChatBase):
    def is_valid_message(self, message: Message) -> bool:
        return True

    def get_reply_to_message_id(self, message: Message) -> int|None:
        return None
