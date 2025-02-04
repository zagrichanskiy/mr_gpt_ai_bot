from enum import Enum
from telegram import Message as TelegramMessage
from abc import ABC, abstractmethod
from datetime import datetime, timezone

class Role(Enum):
    SYSTEM = 'system'
    ASSISTANT = 'assistant'
    USER = 'user'

class Message(ABC):
    def __init__(self, role: Role, date: datetime):
        self.role = role
        self.date = date

    @property
    @abstractmethod
    def content(self) -> str:
        pass

    def to_dict(self) -> dict[str, str]:
        return {
            "role": self.role.value,
            "content": self.content
        }

class SystemMessage(Message):
    def __init__(self, content: str):
        super().__init__(Role.SYSTEM, datetime.now(timezone.utc))
        self._content = content

    @property
    def content(self) -> str:
        return self._content

class ChatMessage(Message):
    def __init__(self, role: Role, message: TelegramMessage):
        super().__init__(role, message.date)
        self.id = message.message_id
        self.text = message.text
        self.from_user_full_name = message.from_user.full_name if message.from_user else None
        self.from_user_id = message.from_user.id if message.from_user else None
        self.reply_to_message_id = message.reply_to_message.message_id if message.reply_to_message else None

class UserMessage(ChatMessage):
    def __init__(self, message: TelegramMessage):
        super().__init__(Role.USER, message)

    @property
    def content(self) -> str:
        metadata = f"""[Metadata]
* Message ID: {self.id}
* Date: {self.date}
* From User: {self.from_user_full_name or 'None'}
* From User ID: {self.from_user_id or 'None'}
* Reply To Message ID: {self.reply_to_message_id or 'None'}
"""
        return f"{metadata}\n{self.text}" if self.text else metadata

class AssistantMessage(ChatMessage):
    def __init__(self, message):
        super().__init__(Role.ASSISTANT, message)

    @property
    def content(self) -> str:
        return self.text

class Thread:
    def __init__(self, id: int):
        self.id: int = id
        self.messages: dict[datetime, Message] = {}

    def add_system_message(self, content: str) -> Message:
        message = SystemMessage(content)
        self.messages[message.date] = message
        return message

    def add_user_message(self, message: TelegramMessage) -> Message:
        user_message = UserMessage(message)
        self.messages[user_message.date] = user_message
        return user_message

    def add_assistant_message(self, message: TelegramMessage) -> Message:
        assistant_message = AssistantMessage(message)
        self.messages[assistant_message.date] = assistant_message
        return assistant_message

    def to_list(self) -> list[dict[str, str]]:
        return [message.to_dict() for _, message in self.messages.items()]
