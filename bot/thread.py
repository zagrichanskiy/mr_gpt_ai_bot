from enum import Enum
from telegram import Message as TelegramMessage
from abc import ABC, abstractmethod
from datetime import datetime, timezone
from dataclasses import dataclass, field

class Role(Enum):
    SYSTEM = 'system'
    ASSISTANT = 'assistant'
    USER = 'user'

@dataclass
class Message(ABC):
    role: Role
    date: datetime

    @property
    @abstractmethod
    def content(self) -> str:
        pass

    def to_openai_dict(self) -> dict[str, str]:
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

@dataclass
class ChatMessage(Message):
    message_id: int
    text: str|None
    from_user_full_name: str|None
    from_user_id: int|None
    reply_to_message_id: int|None

    def __init__(self, role: Role, message: TelegramMessage):
        super().__init__(role, message.date)
        self.message_id = message.message_id
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
* Message ID: {self.message_id}
* Date: {self.date}
* From User: {self.from_user_full_name or 'None'}
* From User ID: {self.from_user_id or 'None'}
* Reply To Message ID: {self.reply_to_message_id or 'None'}
"""
        return f"{metadata}\n{self.text}" if self.text else metadata

class AssistantMessage(ChatMessage):
    def __init__(self, message: TelegramMessage):
        super().__init__(Role.ASSISTANT, message)

    @property
    def content(self) -> str:
        return self.text

@dataclass
class Thread:
    chat_id: int
    messages: list[Message] = field(default_factory=list)

    def add_system_message(self, content: str) -> Message:
        message = SystemMessage(content)
        self.messages.append(message)
        return message

    def add_user_message(self, message: TelegramMessage) -> Message:
        user_message = UserMessage(message)
        self.messages.append(user_message)
        return user_message

    def add_assistant_message(self, message: TelegramMessage) -> Message:
        assistant_message = AssistantMessage(message)
        self.messages.append(assistant_message)
        return assistant_message

    def to_openai_list(self) -> list[dict[str, str]]:
        return [message.to_openai_dict() for message in self.messages]
