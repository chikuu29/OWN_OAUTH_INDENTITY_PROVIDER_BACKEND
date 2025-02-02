from fastapi import HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from typing import List, Optional
from pydantic import BaseModel
from fastapi import status  # To use HTTP status codes like 404, 403, etc.

# Define the custom response model
class APIResponse(BaseModel):
    success: bool
    message: str
    data:  Optional[List[dict]] = None  # Can be an empty list or a list of clients
    error: Optional[dict] = None  # Optional error details, default is None

class ResponseHandler:
    
    


    @staticmethod
    def success(message: str, data: List[dict] = None) -> JSONResponse:
        """
        Return a successful response.
        
        Args:
            message (str): A success message.
            data (List[dict]): Data to be returned in the response.

        Returns:
            JSONResponse: A FastAPI response object with success status.
        """
        if data is None:
            data = []
        response_data = APIResponse(
            success=True,
            message=message,
            data=data,
            error={},
        )
        return JSONResponse(content=response_data.dict(), status_code=status.HTTP_200_OK)

    @staticmethod
    def error(message: str, error_details: dict = None) -> JSONResponse:
        """
        Return an error response.
        
        Args:
            message (str): Error message to be returned.
            error_details (dict): Additional details about the error.
        
        Returns:
            JSONResponse: A FastAPI response object with error status.
        """
        if error_details is None:
            error_details = {}
        response_data = APIResponse(
            success=False,
            message=message,
            data=[],
            error=error_details,
        )
        return JSONResponse(content=response_data.dict(), status_code=status.HTTP_400_BAD_REQUEST)

    @staticmethod
    def raise_http_error(message: str, error_details: dict = None, status_code: int = status.HTTP_400_BAD_REQUEST):
        """
        Raise an HTTP error (for non-200 status codes).
        
        Args:
            message (str): Error message to be returned.
            error_details (dict): Additional details about the error.
        
        Raises:
            HTTPException: Raises a custom HTTPException with a detailed error message.
        """
        if error_details is None:
            error_details = {}
        response_data = APIResponse(
            success=False,
            message=message,
            data=[],
            error=error_details,
        )
        raise HTTPException(
            status_code=status_code,
            detail=response_data.dict()
        )

    @staticmethod
    def not_found(message: str, error_details: dict = None) -> JSONResponse:
        """
        Handle a 'Not Found' error (HTTP 404).
        
        Args:
            message (str): Error message to be returned.
            error_details (dict): Additional details about the error.
        
        Returns:
            JSONResponse: A FastAPI response object with status 404 (Not Found).
        """
        if error_details is None:
            error_details = {}
        response_data = APIResponse(
            success=False,
            message=message,
            data=[],
            error=error_details,
        )
        return JSONResponse(content=response_data.dict(), status_code=status.HTTP_404_NOT_FOUND)

    @staticmethod
    def forbidden(message: str, error_details: dict = None) -> JSONResponse:
        """
        Handle a 'Forbidden' error (HTTP 403).
        
        Args:
            message (str): Error message to be returned.
            error_details (dict): Additional details about the error.
        
        Returns:
            JSONResponse: A FastAPI response object with status 403 (Forbidden).
        """
        if error_details is None:
            error_details = {}
        response_data = APIResponse(
            success=False,
            message=message,
            data=[],
            error=error_details,
        )
        return JSONResponse(content=response_data.dict(), status_code=status.HTTP_403_FORBIDDEN)

    @staticmethod
    def handle_exception(request:Request, exc: Exception)->JSONResponse:
        # Check for validation errors
        if isinstance(exc, RequestValidationError):
            # Extract details from the validation exception
            errors = {str(error["loc"]): {"type": error["type"], "msg": error["msg"]} for error in exc.errors()} 
            if errors is None:
                errors = {}

            response_data = APIResponse(
                        success=False,
                         message="message",
                        #  data=None,
                         error=errors,
            )
            return JSONResponse(content=response_data.dict(), status_code=status.HTTP_400_BAD_REQUEST)

        # Handle other exceptions as a general internal server error
        else:
            response_data = APIResponse(
                success=False,
                message="Internal Server Error",
                error={"detail": str(exc)}
            )
            return JSONResponse(content=response_data.to_dict(), status_code=500)


