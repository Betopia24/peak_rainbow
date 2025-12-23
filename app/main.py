from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.comment import router as rating_router

app = FastAPI(title="Service Rating API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(rating_router)


@app.get("/")
async def root():
    return {
        "message": "Service Rating API",
        "endpoint": "/rate-service",
        "method": "POST",
        "required_fields": {
            "summary": "string",
            "details": "string",
            "images": "1-5 image files",
        },
    }