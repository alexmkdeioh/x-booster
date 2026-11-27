FROM mcr.microsoft.com/playwright/python:v1.49.0-noble

WORKDIR /app

# Install dependencies matching the base image
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
RUN playwright install chromium

# Copy all project files
COPY . .

# Default port for Render Web Service
EXPOSE 8080
ENV PORT=8080

CMD ["python", "telegram_bot.py"]
