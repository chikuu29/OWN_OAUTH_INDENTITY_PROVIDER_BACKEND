from fastapi import APIRouter, Depends, status
from fastapi.encoders import jsonable_encoder
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from typing import List
from app.db.database import get_db
from app.models.apps import App, AppPricing
from app.models.features import Feature
from app.models.plans import CountryEnum, CurrencyEnum
from app.schemas.apps import AppCreate, AppOut
from app.core.response import ResponseHandler, APIResponse
from sqlalchemy.orm import selectinload

router = APIRouter(prefix="/saas", tags=["SAAS APPLICATIONS"])

@router.post("/register", response_model=APIResponse)
async def register_app(app_data: AppCreate, db: AsyncSession = Depends(get_db)):
    try:
        # Check if app code already exists
        result = await db.execute(select(App).filter(App.code == app_data.code))
        if result.scalars().first():
            return ResponseHandler.error(message=f"App with code '{app_data.code}' already exists")

        # Create App
        new_app = App(
            code=app_data.code,
            name=app_data.name,
            description=app_data.description,
            icon=app_data.icon,
            is_active=app_data.is_active
        )
        db.add(new_app)
        await db.flush()  # Get new_app.id

        # Add Pricing
        for p in app_data.pricing:
            new_pricing = AppPricing(
                app_id=new_app.id,
                price=p.price,
                currency=p.currency,
                country=p.country,
                is_active=p.is_active
            )
            db.add(new_pricing)
        
        # Add Features
        for f in app_data.features:
            new_feature = Feature(
                app_id=new_app.id,
                code=f.code,
                name=f.name,
                description=f.description,
                is_base_feature=f.is_base_feature,
                addon_price=f.addon_price,
                currency=f.currency,
                status=f.status
            )
            db.add(new_feature)

        await db.commit()
        await db.refresh(new_app)
        
        # Reload with relationships for the response
        result = await db.execute(
            select(App).options(
                selectinload(App.pricing),
                selectinload(App.features)
            ).filter(App.id == new_app.id)
        )
        final_app = result.scalars().first()
        
        # Resolve root pricing for response (Mandatory INR)
        app_out = AppOut.from_orm(final_app)
        inr_pricing = next((p for p in final_app.pricing if p.is_active and p.currency == CurrencyEnum.INR), None)
        
        if inr_pricing:
            app_out.base_price = inr_pricing.price
            app_out.primary_currency = inr_pricing.currency
            app_out.primary_country = inr_pricing.country
        else:
            app_out.base_price = 1000.00  # Fallback as requested
            app_out.primary_currency = CurrencyEnum.INR
            app_out.primary_country = CountryEnum.IN
            
        return ResponseHandler.success(
            data=jsonable_encoder([app_out]), 
            message="App registered successfully"
        )
    except Exception as e:
        await db.rollback()
        return ResponseHandler.error(
            message="Failed to register app", 
            error_details={"detail": str(e)}
        )

@router.get("/get_apps", response_model=APIResponse)
async def list_apps(db: AsyncSession = Depends(get_db)):
    try:
        result = await db.execute(
            select(App).options(
                selectinload(App.pricing),
                selectinload(App.features)
            ).filter(App.is_active == True)
        )
        apps = result.scalars().unique().all()
        
        data_out = []
        for app in apps:
            app_out = AppOut.from_orm(app)
            # Find an active INR pricing record
            inr_pricing = next((p for p in app.pricing if p.is_active and p.currency == CurrencyEnum.INR), None)
            
            if inr_pricing:
                app_out.base_price = inr_pricing.price
                app_out.primary_currency = inr_pricing.currency
                app_out.primary_country = inr_pricing.country
            else:
                app_out.base_price = 1000.00  # Fallback as requested
                app_out.primary_currency = CurrencyEnum.INR
                app_out.primary_country = CountryEnum.IN
            data_out.append(app_out)

        return ResponseHandler.success(
            data=jsonable_encoder(data_out), 
            message="Apps retrieved successfully"
        )
    except Exception as e:
        return ResponseHandler.error(
            message="Failed to retrieve apps", 
            error_details={"detail": str(e)}
        )
