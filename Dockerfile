# Use Python base image
FROM python:3.9-slim

# Install required packages
RUN apt-get update && apt-get install -y \
    ffmpeg \
    gcc \
    libffi-dev \
    python3-dev

# Set the working directory
WORKDIR /usr/src/app

# Copy the bot's requirements
COPY requirements.txt .

# Install the bot's dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy the bot's source code
COPY . .

# Expose the bot's port
EXPOSE 8080

# Run the bot
CMD ["python", "bot.py"]
