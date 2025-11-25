# Base Python image
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Copy libraries for Python
COPY  requirements.txt /app/

RUN pip install -r requirements.txt

COPY . /app

# Expose port
EXPOSE 8080

# Start gateway service
CMD ["python", "gateway.py"]
