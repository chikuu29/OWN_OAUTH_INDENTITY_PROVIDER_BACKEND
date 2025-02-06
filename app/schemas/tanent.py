from pydantic import BaseModel, EmailStr, model_validator

class TenantCreate(BaseModel):
    tenant_email: EmailStr
    tenant_name: str

    @model_validator(mode='before')
    def check_name_and_email(cls, values):
        tenant_name = values.get('tenant_name')
        tenant_email = values.get('tenant_email')

        if len(tenant_name) < 2:
            raise ValueError('Tenant name must be at least 2 characters long')

        if tenant_email and tenant_email.endswith("@example.com"):
            raise ValueError("Emails from example.com are not allowed.")

        return values
    
