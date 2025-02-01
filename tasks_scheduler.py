import asyncio
from dataclasses import dataclass
import logging

class TasksScheduler:
  def __init__(self):
    self._chat_tasks: dict[int, asyncio.Task] = {}

  def task(self, chat_id) -> asyncio.Task|None:
    return self._chat_tasks.get(chat_id)

  def append_task(self, chat_id: int, coro) -> asyncio.Task:
    current_task = self.task(chat_id)

    async def chain_task():
      if current_task:
        try:
          await current_task
        except Exception as ex:
          logging.warning(f"Error {ex} in previous task for chat {chat_id}")
      return await coro

    self._chat_tasks[chat_id] = asyncio.create_task(chain_task())

    return self._chat_tasks[chat_id]

  def remove_task(self, chat_id):
    task = self.task(chat_id)
    if task:
      task.cancel()
      del self._chat_tasks[chat_id]
