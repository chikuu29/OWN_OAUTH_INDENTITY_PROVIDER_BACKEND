




from sqlalchemy import and_, or_
from sqlalchemy.orm import Session
from app.schemas.tanent import TenantCreate
from app.models.tenant import Tenant
from sqlalchemy.future import select

async def create_tenant(db:Session,client:TenantCreate):
    # Check if the client_id already exists to avoid duplicates
  
    result = await db.execute(select(Tenant).filter(or_(
        Tenant.tenant_name == client.tenant_name,
        Tenant.tenant_email == client.tenant_email  # Either name or email should be unique
    )))
    existing_in_db = result.scalars().first()

    if existing_in_db:
        raise ValueError("Tenant with this name or email already exists")
    
    # Create a new OAuth client
    db_client = Tenant(
        tenant_name=client.tenant_name,
        tenant_email=client.tenant_email
    )
    
    # Add and commit the new client to the database asynchronously
    db.add(db_client)
    await db.commit()
    
    # Refresh to load the latest state of the client object
    await db.refresh(db_client)
    
    return db_client