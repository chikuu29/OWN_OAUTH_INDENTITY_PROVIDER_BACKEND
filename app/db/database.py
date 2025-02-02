from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine

DATABASE_URL = "postgresql+asyncpg://user:password@localhost/indentity_provider_datbase"

engine = create_async_engine(DATABASE_URL, echo=True)
SessionLocal = sessionmaker(
      bind=engine,
      class_=AsyncSession,
      expire_on_commit=False
    )

# Define base for models
Base = declarative_base()


async def get_db():
    async with SessionLocal() as session:
        print(f"😄===DATABASE CONNECTION SUCCESSFULL===")
        yield session
    # db = SessionLocal()
    # try:
    #     print(f"😄===DATABASE CONNECTION SUCCESSFULL===")
    #     yield db
    # finally:
    #     print(f"😢===DATABASE CONNECTION FAILED===")
    #     db.close()