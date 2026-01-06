# src/web/app.py
#
# FastAPI application for the Layout Verifier "Furnace" UI.

import uvicorn
from pathlib import Path
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from .routes import router

# Paths
BASE_DIR = Path(__file__).parent
STATIC_DIR = BASE_DIR / "static"
TEMPLATES_DIR = BASE_DIR / "templates"

# Create FastAPI app
app = FastAPI(
    title="Layout Verifier",
    description="Verify product layouts against Excel master data",
    version="0.1.0",
)

# Mount static files
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

# Templates
templates = Jinja2Templates(directory=TEMPLATES_DIR)

# Include API routes
app.include_router(router)


def main(port: int = 8000):
    """Entry point for the furnace-ui command."""
    print("Starting Layout Verifier Furnace UI...")
    print(f"Open http://localhost:{port} in your browser")
    print("Press Ctrl+C to stop")
    uvicorn.run(
        "web.app:app",
        host="127.0.0.1",
        port=port,
        reload=True,
    )


if __name__ == "__main__":
    main()
