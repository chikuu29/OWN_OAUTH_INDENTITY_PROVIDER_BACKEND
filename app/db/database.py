
# from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker,DeclarativeBase
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from app.config import DATABASE_URL
# load_dotenv()

# DATABASE_URL = "postgresql+asyncpg://postgres:password@localhost/identity_provider_database"
# DATABASE_URL=os.getenv('DATABASE_URL')


engine = create_async_engine(DATABASE_URL, echo=False)
AsyncSessionLocal  = sessionmaker(
      bind=engine,
      class_=AsyncSession,
      expire_on_commit=False
    )

# Define base for models
# ✅ Correct way to define Base
class Base(DeclarativeBase):
    pass

async def get_db():
    async with AsyncSessionLocal() as session:
        print(f"=== ✅ DATABASE CONNECTION SUCCESSFULL ✅ ===")
        yield session
    # db = SessionLocal()
    # try:
    #     print(f"😄===DATABASE CONNECTION SUCCESSFULL===")
    #     yield db
    # finally:
    #     print(f"😢===DATABASE CONNECTION FAILED===")
    #     db.close()