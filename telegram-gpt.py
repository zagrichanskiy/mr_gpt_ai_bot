import argparse
import logging
import os
from bot import Bot, GPTOptions, BotOptions

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        '--openai-api-key',
        type=str,
        default=os.environ.get('TELEGRAM_GPT_OPENAI_API_KEY'),
        required='TELEGRAM_GPT_OPENAI_API_KEY' not in os.environ,
        help="OpenAI API key (https://platform.openai.com/account/api-keys).",
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
        '--parse-mode',
        type=lambda x: None if x.lower() == "none" else x,
        default=(lambda val: None if val and val.lower() == "none" else val or "MarkdownV2")(os.getenv("TELEGRAM_GPT_PARSE_MODE")),
        help="Parse mode for telegram messages.",
    )
    parser.add_argument(
        '--openai-model-name',
        type=str,
        default=os.environ.get('TELEGRAM_GPT_OPENAI_MODEL_NAME') or 'gpt-3.5-turbo',
        help="Chat completion model name (https://platform.openai.com/docs/models/model-endpoint-compatibility). Default to be gpt-3.5-turbo.",
    )

    logging.getLogger("httpx").setLevel(logging.WARNING)

    args = parser.parse_args()
    gpt_options = GPTOptions(args.openai_api_key, args.openai_model_name)
    bot_options = BotOptions(args.telegram_token, args.data_dir, args.parse_mode)

    logging.info(f"Starting bot with options: {bot_options}")

    bot = Bot(bot_options, gpt_options)
    bot.run()
