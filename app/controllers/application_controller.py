




from sqlalchemy.orm import Session
from app.schemas.client import OAuthClientCreate
from app.models.client import OAuthClient
from sqlalchemy.future import select
from passlib.context import CryptContext
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

async def create_oauth_client(db:Session,client_data:OAuthClientCreate):
     # Check if client_id is already taken
    
    existing_client = await db.execute(select(OAuthClient).filter(
       OAuthClient.client_id == client_data.client_id
    ))
    existing_client = existing_client.scalars().first()
    if existing_client:
        raise ValueError(
            {
            'value':{
                "client_id":{
                    "msg":"Client ID already exists"
                }
            }
        })

     # Hash the client secret
    hashed_secret = pwd_context.hash(client_data.client_secret)
    # Create a new OAuth client
    db_client = OAuthClient(
        name=client_data.name,
        client_id=client_data.client_id,
        client_secret=hashed_secret,  # Store hashed secret
        client_type=client_data.client_type,
        authorization_grant_type=client_data.authorization_grant_type,
        redirect_urls=client_data.redirect_urls,
        post_logout_redirect_uris=client_data.post_logout_redirect_uris,
        allowed_origins=client_data.allowed_origins,
        algorithm=client_data.algorithm
    )
    
    # Add and commit the new client to the database asynchronously
    db.add(db_client)
    await db.commit()
    
    # Refresh to load the latest state of the client object
    await db.refresh(db_client)
    
    return db_client