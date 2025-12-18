#!/usr/bin/env python
"""Entry point script for running the application."""

import uvicorn

from app.config import settings


def main():
    """Run the FastAPI application with Uvicorn."""
    uvicorn.run(
        "app.main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug,
        log_level=settings.log_level.lower(),
        workers=1 if settings.debug else 4,
    )


if __name__ == "__main__":
    main()
