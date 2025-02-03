from aiohttp import ClientSession
from bot.thread import Thread
from dataclasses import dataclass, field
from typing import cast, AsyncGenerator
import logging
import openai

@dataclass
class GPTOptions:
    api_key: str = field(repr=False)
    model_name: str = 'gpt-3.5-turbo'

class GPTClient:
    MAX_REPLY_LENGTH = 3500

    def __init__(self, *, options: GPTOptions):
        self.__model_name = options.model_name

        openai.api_key = options.api_key
        openai.aiosession.set(ClientSession(trust_env=True))
        logging.getLogger("openai").setLevel(logging.WARNING)

    @classmethod
    def default_system_prompt(cls) -> str:
        return f"""
You are a witty, humorous, and slightly sarcastic AI integrated into a Telegram bot.
Your goal is to entertain, respond playfully, and engage users with a natural, human-like tone.

### **Personality & Behavior:**
- Be concise and to the point.
- If you don't know the answer, say so—but make it sound clever or funny.
- If someone jokes about you, **fire back with humor or mild sarcasm**.
- Feel free to roast users playfully, but don't be overly rude or offensive.
- Provide short responses by default but explain in more detail **if asked**.

### **Important Rules:**
- Your responses must never exceed {cls.MAX_REPLY_LENGTH} characters, including formatting symbols.
- If a response exceeds this limit, **stop generating and ask the user**:
  `"This response is long. Do you want me to continue? Reply 'Yes' to get more."`
- Never break character. You are a **funny, sarcastic Telegram user**, not an AI assistant.
"""

    @classmethod
    def make_thread(cls, id: int) -> Thread:
        thread = Thread(id)
        thread.add_system_message(cls.default_system_prompt())
        return thread

    async def stream_response(self, thread: Thread):
        try:
            generator = await openai.ChatCompletion.acreate(
                model=self.__model_name,
                messages=thread.to_list(),
                stream=True,
            )

            async for content in self.stream_responses(generator):
                yield content
        except Exception as ex:
            logging.error(f"Error while running GPT: {ex}")

    async def stream_responses(self, generator) -> AsyncGenerator[str, None]:
        async for response in generator:
            content = cast(dict, response)['choices'][0]['delta'].get('content')
            if content:
                yield content

    #     if conversation.title is None and len(conversation.messages) < 3:
    #         async def set_title(conversation: Conversation):
    #             prompt = 'You are a title generator. You will receive one or multiple messages of a conversation. You will reply with only the title of the conversation without any punctuation mark either at the begining or the end.'
    #             messages = [SystemMessage(prompt)] + conversation.messages

    #             title = await self.__request(messages)
    #             conversation.title = title

    #             logging.info(f"Set title for conversation {conversation}: '{title}'")
    #         asyncio.create_task(set_title(conversation))

    #     logging.info(f"Completed message for chat {conversation.id}, message: '{assistant_message}'")

    # async def __request(self, messages: list[Message]):
    #     task = openai.ChatCompletion.acreate(
    #         model=self.__model_name,
    #         messages=[{'role': message.role, 'content': message.content} for message in messages],
    #     )
    #     response = await asyncio.wait_for(task, 60)
    #     return cast(dict, response)['choices'][0]['message']['content']
