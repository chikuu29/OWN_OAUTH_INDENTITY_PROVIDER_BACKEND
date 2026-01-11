from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import BackgroundTasks
from typing import Optional
from app.core.logger import create_logger

class BaseController:
    """
    Base class for all controllers, providing shared utilities for 
    database access, background tasks, and standardized logging.
    """
    def __init__(
        self, 
        db: AsyncSession, 
        background_tasks: Optional[BackgroundTasks] = None, 
        logger_name: str = "controller"
    ):
        self.db = db
        self.background_tasks = background_tasks
        self.logger = create_logger(logger_name)
