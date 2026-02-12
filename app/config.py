from dotenv import load_dotenv
import os

# Get the environment, defaulting to development
env = os.getenv("FASTAPI_ENV", "development").lower()
print(f"===== 🚀 {env.upper()} SERVER STARTED 🚀 =====")

# Correct usage with f-string for interpolation
load_dotenv(f'.env.{env}')
# print("===== Loaded .env file for environment: ", env, " =====")
# for key, value in os.environ.items():
#     print(f"{key}={value}")

# Access environment variables
print("DATABASE_URL:", os.getenv('DATABASE_URL'))
DATABASE_URL = os.getenv("DATABASE_URL")
DB_URL = os.getenv("DB_URL")
ENV=env
