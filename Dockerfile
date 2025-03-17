FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
# Copy all Python files, including those in subdirectories
COPY *.py .
COPY handlers/*.py .
# Remove .env copy and rely on Koyeb environment variables
# COPY .env .  # Commented out as we'll use Koyeb's env vars
# No need for EXPOSE since it's a Telegram bot, not a web server
# EXPOSE 8000  # Commented out as it's not needed
ENV PYTHONUNBUFFERED=1
CMD ["python", "bot.py"]
