


from sqlalchemy import Column, Integer, String, func
from app.db.database import Base


class OAuthClient(Base):
    __tablename__='oauth_clients'

    id = Column(Integer, primary_key=True, index=True)
    client_id = Column(String, unique=True, index=True)
    client_secret = Column(String)
    redirect_url = Column(String)
    # created_at = Column(func.now())


