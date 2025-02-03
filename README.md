# Mr. GPT - Telegram Bot

## 🤖 About
**Mr. GPT** is a **Telegram bot** powered by OpenAI's GPT model, designed to provide interactive and intelligent responses to users. The bot supports **group and personal chats**, processes MarkdownV2 formatting, and keeps track of conversations.

## 🚀 Features
- **Conversational AI**: Responds intelligently to user messages.
- **Group & Private Chat Support**: Works in both personal and group chats.
- **MarkdownV2 Formatting**: Properly formats responses in Telegram messages.
- **Persistent Conversations**: Uses OpenAI threads for better context retention.
- **Streaming Responses**: Sends responses in real-time while generating.
- **Custom Commands**: `/start`, and more.

## 📦 Installation
### **1️⃣ Clone the Repository**
```bash
git clone https://github.com/your-username/mr-gpt-ai-bot.git
cd mr-gpt-ai-bot
```

### **2️⃣ Install Dependencies**
Ensure you have Python **3.10+** installed.
```bash
pip install -r requirements.txt
```

### **3️⃣ Set Up Environment Variables**
Create a `.env` file and define:
```ini
TELEGRAM_BOT_TOKEN=your_telegram_bot_token
OPENAI_API_KEY=your_openai_api_key
```

## 🚀 Deployment
### **Local Run**
```bash
python telegram-gpt.py
```

### **Deploy as a Docker Container**
#### **1️⃣ Build the Image**
```bash
docker build -t mr_gpt .
```
#### **2️⃣ Run the Container**
```bash
docker run -d --name mr_gpt \
  -e TELEGRAM_BOT_TOKEN=your_telegram_bot_token \
  -e OPENAI_API_KEY=your_openai_api_key \
  mr_gpt
```

## ⚙️ Options Reference

| Option | Environment Variable | Description | Default |
|-|-|-|-|
| `--openai-api-key` | `TELEGRAM_GPT_OPENAI_API_KEY` | OpenAI API key created from [OpenAI Platform](https://platform.openai.com/account/api-keys). | |
| `--telegram-token` | `TELEGRAM_GPT_TELEGRAM_TOKEN` | Telegram bot token. Get it from [@BotFather](https://t.me/BotFather). | |
| `--data-dir` | `TELEGRAM_GPT_DATA_DIR` | Directory to store data. If not specified, data won't be persisted. | |
| `--openai-model-name` | `TELEGRAM_GPT_OPENAI_MODEL_NAME` | Chat completion model name. If `--azure-openai-endpoint` is specified, this is the Azure OpenAI Service model deployment name. | `gpt-3.5-turbo` |
| `--parse-mode` | `TELEGRAM_GPT_PARSE_MODE` | Parse mode for telegram messages. | `MarkdownV2` |

## 🛠 Commands
| Command  | Description |
|----------|------------|
| `/start` | Initializes the bot |
| `/help`  | Displays available commands |
| `@botname` | Mentions the bot in group chats to trigger a response |

## 📜 License
This project is licensed under **MIT License**.

## 📬 Contact
For support or feedback open an issue on GitHub.
