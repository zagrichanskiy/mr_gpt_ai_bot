import argparse
import logging
import os
from bot import BotOptions, Bot, WebhookOptions
from gpt import GPTOptions

logging.basicConfig(
  format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
  level=logging.INFO,
)

if __name__ == "__main__":
  def get_chat_ids_from_env():
    chat_ids = []

    while True:
      chat_id = os.environ.get('TELEGRAM_GPT_CHAT_ID_' + str(len(chat_ids)))
      if chat_id is None:
        break
      chat_ids.append(int(chat_id))

    if 'TELEGRAM_GPT_CHAT_ID' in os.environ:
      chat_ids.append(int(os.environ['TELEGRAM_GPT_CHAT_ID']))

    return chat_ids

  parser = argparse.ArgumentParser()
  parser.add_argument(
    '--openai-api-key',
    type=str,
    default=os.environ.get('TELEGRAM_GPT_OPENAI_API_KEY'),
    required='TELEGRAM_GPT_OPENAI_API_KEY' not in os.environ,
    help="OpenAI API key (https://platform.openai.com/account/api-keys). If --azure-openai-endpoint is specified, this is the Azure OpenAI Service API key.",
  )
  parser.add_argument(
    '--telegram-token',
    type=str,
    default=os.environ.get('TELEGRAM_GPT_TELEGRAM_TOKEN'),
    required='TELEGRAM_GPT_TELEGRAM_TOKEN' not in os.environ,
    help="Telegram bot token. Get it from https://t.me/BotFather.",
  )

  parser.add_argument(
    '--data-dir',
    type=str,
    default=os.environ.get('TELEGRAM_GPT_DATA_DIR'),
    help="Directory to store data. If not specified, data won't be persisted.",
  )
  parser.add_argument(
    '--webhook-url',
    type=str,
    default=os.environ.get('TELEGRAM_GPT_WEBHOOK_URL'),
    help="URL for telegram webhook requests. If not specified, the bot will use polling mode.",
  )
  parser.add_argument(
    '--webhook-listen-address',
    type=str,
    default=os.environ.get('TELEGRAM_GPT_WEBHOOK_LISTEN_ADDRESS') or '0.0.0.0:80',
    help="Address to listen for telegram webhook requests in the format of <ip>:<port>. Only valid when --webhook-url is set. If not specified, 0.0.0.0:80 would be used.",
  )
  parser.add_argument(
    '--parse-mode',
    type=str,
    default=os.environ.get('TELEGRAM_GPT_PARSE_MODE') or 'MarkdownV2',
    help="Parse mode for telegram messages. Default to be MarkdownV2.",
  )

  parser.add_argument(
    '--openai-model-name',
    type=str,
    default=os.environ.get('TELEGRAM_GPT_OPENAI_MODEL_NAME') or 'gpt-3.5-turbo',
    help="Chat completion model name (https://platform.openai.com/docs/models/model-endpoint-compatibility). If --azure-openai-endpoint is specified, this is the Azure OpenAI Service model deployment name. Default to be gpt-3.5-turbo.",
  )

  logging.getLogger("httpx").setLevel(logging.WARNING)

  args = parser.parse_args()

  gpt_options = GPTOptions(args.openai_api_key, args.openai_model_name)

  webhook_options = WebhookOptions(args.webhook_url, args.webhook_listen_address) if args.webhook_url is not None else None
  bot_options = BotOptions(args.telegram_token, args.data_dir, args.parse_mode, webhook_options)
  logging.info(f"Starting bot with options: {bot_options}")

  bot = Bot(bot_options, gpt_options)
  bot.run()
