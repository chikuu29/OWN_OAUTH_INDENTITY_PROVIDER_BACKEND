




from sqlalchemy.orm import Session
from app.schemas.client import OAuthClientCreate
from app.models.client import OAuthClient
from sqlalchemy.future import select

async def create_oauth_client(db:Session,client:OAuthClientCreate):
    # Check if the client_id already exists to avoid duplicates
    result = await db.execute(select(OAuthClient).filter(OAuthClient.client_id == client.client_id))
    existing_client = result.scalars().first()
    if existing_client:
        raise ValueError("Client ID already exists")
    
    # Create a new OAuth client
    db_client = OAuthClient(
        client_id=client.client_id,
        client_secret=client.client_secret,
        redirect_url=client.redirect_url,
    )
    
    # Add and commit the new client to the database asynchronously
    db.add(db_client)
    await db.commit()
    
    # Refresh to load the latest state of the client object
    await db.refresh(db_client)
    
    return db_client