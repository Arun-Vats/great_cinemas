# Use Python 3.11 slim as the base image
FROM python:3.11-slim

# Set the working directory inside the container
WORKDIR /app

# Copy the requirements file and install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy all the necessary files
COPY . .

# Ensure environment variables are correctly set
ENV PYTHONUNBUFFERED=1

# Run the bot
CMD ["python", "bot.py"]
