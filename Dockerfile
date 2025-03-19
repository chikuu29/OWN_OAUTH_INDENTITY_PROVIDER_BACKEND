
# Use the official Python image as base
FROM python:3.11-slim

# Set the working directory inside the container
WORKDIR /app

# Copy the requirements file and install dependencies
COPY requirements.txt .

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy the FastAPI app files to the container
COPY . .

# Expose the port FastAPI runs on
EXPOSE 8000

# CMD ["fastapi", "run", "app/main.py", "--port", "8000"]


# Run Alembic migrations and start the FastAPI app
CMD ["sh", "-c", "alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4"]
