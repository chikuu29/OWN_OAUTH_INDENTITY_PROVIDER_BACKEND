import os
from fastapi import APIRouter, HTTPException

router = APIRouter(prefix="/logs", tags=["logs"])

# Path to the logs directory (relative to the project root)
logs_dir = os.path.join(os.path.dirname(__file__), "..", "..", "logs")

@router.get("/categories")
def get_log_categories():
    """Get list of log categories (subfolders in logs directory)"""
    try:
        if not os.path.exists(logs_dir):
            raise HTTPException(status_code=404, detail="Logs directory not found")
        categories = [d for d in os.listdir(logs_dir) if os.path.isdir(os.path.join(logs_dir, d))]
        return {"categories": categories}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/{category}")
def get_logs_in_category(category: str):
    """Get list of log files in a specific category"""
    category_path = os.path.join(logs_dir, category)
    if not os.path.exists(category_path):
        raise HTTPException(status_code=404, detail="Category not found")
    try:
        files = [f for f in os.listdir(category_path) if os.path.isfile(os.path.join(category_path, f))]
        return {"logs": files}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/{category}/{filename}")
def get_log_content(category: str, filename: str):
    """Get the content of a specific log file"""
    file_path = os.path.join(logs_dir, category, filename)
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="Log file not found")
    try:
        with open(file_path, 'r') as f:
            content = f.read()
        return {"content": content}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))