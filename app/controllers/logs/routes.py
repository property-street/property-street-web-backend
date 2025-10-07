import os
from fastapi.responses import FileResponse
from fastapi import APIRouter, HTTPException

router = APIRouter(prefix='/logs', tags=['logs'])

# Path to your log file
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
GRANDPARENT_DIR = os.path.abspath(os.path.join(BASE_DIR, "..", "..", ".."))
LOG_FILE_PATH = os.path.join(GRANDPARENT_DIR, "logs", "error.log")

@router.get("/error/", response_class=FileResponse)
async def get_error_log():
    """
    Serve the application's error log file for admin users only.
    """
    if not os.path.exists(LOG_FILE_PATH):
        raise HTTPException(status_code=404, detail="Log file not found")
    
    # Optional: restrict large files (for example >10MB)
    max_size = 10 * 1024 * 1024  # 10 MB
    file_size = os.path.getsize(LOG_FILE_PATH)
    if file_size > max_size:
        raise HTTPException(status_code=413, detail="Log file too large to download")

    # You can return it as attachment 
    # return FileResponse(
    #     LOG_FILE_PATH,
    #     filename="error.log",
    #     media_type="text/plain"
    # )

    # Serve file inline
    response = FileResponse(LOG_FILE_PATH, media_type="text/plain")
    response.headers["Content-Disposition"] = "inline; filename=error.log"
    return response