#!/usr/bin/env python3
"""
Single-Command Launcher for the Block-to-Panchayat Weather Downscaling System.

Starts the FastAPI server with integrated React + Leaflet frontend:
  - Backend API: http://127.0.0.1:8000/api/
  - Interactive Map Dashboard: http://127.0.0.1:8000/
  - API Documentation / Swagger: http://127.0.0.1:8000/docs
"""

import sys
import os
import uvicorn
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent

if __name__ == "__main__":
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    
    print("\n" + "=" * 75)
    print("  STARTING IMD DAMU PANCHAYAT WEATHER DOWNSCALING SYSTEM")
    print("=" * 75)
    print("  * Web Dashboard:    http://127.0.0.1:8000/")
    print("  * API Documentation: http://127.0.0.1:8000/docs")
    print("  * Health Endpoint:   http://127.0.0.1:8000/api/health")
    print("=" * 75 + "\n")

    uvicorn.run("src.api.main:app", host="0.0.0.0", port=8000, reload=True)
