# Use a lightweight Python base image
FROM python:3.10-slim

# Set the working directory in the container
WORKDIR /app

# Install system dependencies required for build-time operations
RUN apt-get update && apt-get install -y \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copy the requirements file first to leverage Docker cache
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application code
COPY . .

# Create the templates directory if it doesn't exist (failsafe)
RUN mkdir -p templates

# Expose the port FastAPI will run on
EXPOSE 8000

# Use Gunicorn with Uvicorn workers for high-performance production handling
# -w 4: Four worker processes
# -k uvicorn.workers.UvicornWorker: The worker class for ASGI
# --bind 0.0.0.0:8000: Binds to all interfaces for cloud access
CMD ["gunicorn", "-w", "4", "-k", "uvicorn.workers.UvicornWorker", "main:app", "--bind", "0.0.0.0:8000", "--timeout", "600"]
