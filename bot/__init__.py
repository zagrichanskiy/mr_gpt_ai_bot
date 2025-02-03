import logging

logging.basicConfig(
    format="%(asctime)s - %(levelname)s - %(message)s",
    level=logging.INFO
)

from .bot import Bot, BotOptions
from .gpt import GPTOptions

__all__ = [
    "Bot",
    "BotOptions",
    "GPTOptions"
]
