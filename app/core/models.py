from pydantic import BaseModel
from typing import List, Optional

# Define the custom response model
class APIResponse(BaseModel):
    success: bool
    message: str
    data: List[dict]  # This could be an empty list or a list of clients
    error: Optional[dict] = None  # Optional error details, default is None
