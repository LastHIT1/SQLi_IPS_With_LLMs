# Base python image
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install libraries
COPY requirements.txt /app/

RUN pip install -r requirements.txt

# Copy application code
COPY . /app

# Expose port so web app can listen
EXPOSE 5000

# Start the app
CMD ["python", "app.py"]
