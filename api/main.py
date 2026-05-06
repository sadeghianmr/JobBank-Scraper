"""FastAPI application for JobBank scraper API."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .routes import scraper, jobs
from src.logging_config import configure_logging

logger = configure_logging(__name__, "api/api.log")

# Create FastAPI app
app = FastAPI(
    title="JobBank Scraper API",
    description="API for scraping and managing job postings",
    version="1.0.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify actual origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(scraper.router, prefix="/api/v1/scraper", tags=["scraper"])
app.include_router(jobs.router, prefix="/api/v1/jobs", tags=["jobs"])


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "message": "JobBank Scraper API",
        "version": "1.0.0",
        "docs": "/docs"
    }


@app.get("/health")
async def health():
    """Health check endpoint."""
    return {"status": "healthy"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
