from dataclasses import dataclass
from enum import Enum

class Role(Enum):
    SYSTEM = 'system'
    ASSISTANT = 'assistant'
    USER = 'user'

@dataclass
class Message:
    role: Role
    content: str

    def to_dict(self) -> dict[str, str]:
        return {
            'role': self.role.value,
            'content': self.content
        }

class Thread:
    def __init__(self, id: int):
        self.id: int = id
        self.messages: list[Message] = []

    def add_system_message(self, content: str) -> Message:
        msg = Message(Role.SYSTEM, content)
        self.messages.append(msg)
        return msg

    def add_user_message(self, content: str) -> Message:
        msg = Message(Role.USER, content)
        self.messages.append(msg)
        return msg

    def add_assistant_message(self, content: str) -> Message:
        msg = Message(Role.ASSISTANT, content)
        self.messages.append(msg)
        return msg

    def to_list(self) -> list[dict[str, str]]:
        return [message.to_dict() for message in self.messages]
