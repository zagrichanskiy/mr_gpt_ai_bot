FROM python:3.10-slim

WORKDIR /app

COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

COPY . .

ENV TELEGRAM_GPT_DATA_DIR=/data
RUN mkdir -p $TELEGRAM_GPT_DATA_DIR

ENTRYPOINT ["python", "telegram-gpt.py"]
