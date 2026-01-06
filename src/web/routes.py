# src/web/routes.py
#
# API routes for the Layout Verifier Furnace UI.
# Uses local file paths instead of uploads since this runs on the same machine.

import uuid
import shutil
import tempfile
from pathlib import Path
from typing import Optional
from dataclasses import dataclass, field

from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel

from layout_verifier.core import verify_and_color_excel

# Templates
TEMPLATES_DIR = Path(__file__).parent / "templates"
templates = Jinja2Templates(directory=TEMPLATES_DIR)

router = APIRouter()


# Request models
class SetExcelRequest(BaseModel):
    path: str


class SetLayoutsRequest(BaseModel):
    paths: list[str] = []
    folder: str = ""  # Alternative: scan a folder for .ai files


class ProcessRequest(BaseModel):
    session_id: str


# In-memory storage for sessions
@dataclass
class Session:
    """Tracks file paths and processing state for a session."""
    id: str
    temp_dir: Path
    excel_path: Optional[Path] = None
    excel_name: Optional[str] = None
    layout_paths: list[Path] = field(default_factory=list)
    layout_names: list[str] = field(default_factory=list)
    status: str = "idle"  # idle, processing, complete, error
    result_path: Optional[Path] = None
    error_message: Optional[str] = None


sessions: dict[str, Session] = {}


def get_or_create_session(session_id: Optional[str] = None) -> Session:
    """Get existing session or create a new one."""
    if session_id and session_id in sessions:
        return sessions[session_id]

    # Create new session
    new_id = str(uuid.uuid4())[:8]
    temp_dir = Path(tempfile.mkdtemp(prefix=f"furnace_{new_id}_"))
    session = Session(id=new_id, temp_dir=temp_dir)
    sessions[new_id] = session
    return session


def cleanup_session(session_id: str) -> None:
    """Clean up session temp files."""
    if session_id in sessions:
        session = sessions[session_id]
        if session.temp_dir.exists():
            shutil.rmtree(session.temp_dir)
        del sessions[session_id]


@router.get("/", response_class=HTMLResponse)
async def index(request: Request):
    """Serve the main UI page."""
    session = get_or_create_session()
    return templates.TemplateResponse(
        "index.html",
        {"request": request, "session_id": session.id}
    )


@router.post("/api/set/excel")
async def set_excel(request: SetExcelRequest, session_id: Optional[str] = None):
    """Set the Excel file path (the 'fuel'). No upload needed - just the path."""
    session = get_or_create_session(session_id)

    file_path = Path(request.path)

    # Validate file exists
    if not file_path.exists():
        raise HTTPException(status_code=400, detail=f"File not found: {request.path}")

    # Validate file extension
    ext = file_path.suffix.lower()
    if ext not in (".xlsx", ".xls", ".xlsm"):
        raise HTTPException(
            status_code=400,
            detail=f"Invalid file type: {ext}. Expected .xlsx, .xls, or .xlsm"
        )

    session.excel_path = file_path
    session.excel_name = file_path.name
    session.status = "idle"
    session.result_path = None

    return {
        "session_id": session.id,
        "filename": file_path.name,
        "path": str(file_path),
    }


@router.post("/api/set/layouts")
async def set_layouts(request: SetLayoutsRequest, session_id: Optional[str] = None):
    """Set layout file paths (.ai files). No upload needed - just the paths or folder."""
    session = get_or_create_session(session_id)

    # Clear previous layouts
    session.layout_paths = []
    session.layout_names = []

    valid_files = []
    invalid_files = []

    # Collect paths - either from direct list or by scanning folder
    paths_to_check = list(request.paths)

    if request.folder:
        folder_path = Path(request.folder)
        if folder_path.exists() and folder_path.is_dir():
            # Scan folder for .ai files
            ai_files = list(folder_path.glob("*.ai"))
            paths_to_check.extend([str(f) for f in ai_files])
        else:
            raise HTTPException(
                status_code=400,
                detail=f"Folder not found or not a directory: {request.folder}"
            )

    for path_str in paths_to_check:
        file_path = Path(path_str)

        # Check if file exists
        if not file_path.exists():
            invalid_files.append({"path": path_str, "reason": "not found"})
            continue

        # Validate extension (.ai only)
        ext = file_path.suffix.lower()
        if ext != ".ai":
            invalid_files.append({"path": path_str, "reason": f"invalid type: {ext}"})
            continue

        session.layout_paths.append(file_path)
        session.layout_names.append(file_path.name)
        valid_files.append({"filename": file_path.name, "path": str(file_path)})

    if not valid_files:
        raise HTTPException(
            status_code=400,
            detail="No valid .ai layout files found"
        )

    session.status = "idle"
    session.result_path = None

    return {
        "session_id": session.id,
        "files": valid_files,
        "count": len(valid_files),
        "invalid": invalid_files if invalid_files else None,
    }


@router.post("/api/process")
async def process(session_id: str):
    """Start processing - verify layouts against Excel and color the result."""
    if session_id not in sessions:
        raise HTTPException(status_code=404, detail="Session not found")

    session = sessions[session_id]

    # Validate we have both inputs
    if not session.excel_path or not session.excel_path.exists():
        raise HTTPException(status_code=400, detail="No Excel file selected")

    if not session.layout_paths:
        raise HTTPException(status_code=400, detail="No layout files selected")

    # Set processing status
    session.status = "processing"
    session.error_message = None

    try:
        # Create output path in temp dir
        output_filename = f"verified_{session.excel_name}"
        output_path = session.temp_dir / output_filename

        # Run verification (uses original file paths - no copying needed)
        result = verify_and_color_excel(
            layout_files=session.layout_paths,
            excel_path=session.excel_path,
            output_path=output_path,
        )

        session.status = "complete"
        session.result_path = output_path

        return {
            "status": "complete",
            "products_found": result.products_found,
            "products_not_found": result.products_not_found,
            "cells_green": result.cells_green,
            "cells_red": result.cells_red,
            "cells_yellow": result.cells_yellow,
        }

    except Exception as e:
        session.status = "error"
        session.error_message = str(e)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/api/status/{session_id}")
async def get_status(session_id: str):
    """Get the current status of a session."""
    if session_id not in sessions:
        raise HTTPException(status_code=404, detail="Session not found")

    session = sessions[session_id]

    return {
        "session_id": session.id,
        "status": session.status,
        "excel_file": session.excel_name,
        "layout_files": session.layout_names,
        "layout_count": len(session.layout_names),
        "error": session.error_message,
        "has_result": session.result_path is not None and session.result_path.exists(),
    }


@router.get("/api/download/{session_id}")
async def download_result(session_id: str):
    """Download the colored Excel result."""
    if session_id not in sessions:
        raise HTTPException(status_code=404, detail="Session not found")

    session = sessions[session_id]

    if session.status != "complete":
        raise HTTPException(status_code=400, detail="Processing not complete")

    if not session.result_path or not session.result_path.exists():
        raise HTTPException(status_code=404, detail="Result file not found")

    return FileResponse(
        path=session.result_path,
        filename=session.result_path.name,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )


@router.post("/api/reset/{session_id}")
async def reset_session(session_id: str):
    """Reset a session to start fresh."""
    if session_id in sessions:
        cleanup_session(session_id)

    session = get_or_create_session()
    return {"session_id": session.id}
