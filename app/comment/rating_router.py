from fastapi import APIRouter, File, UploadFile, Form, HTTPException
from fastapi.responses import JSONResponse
from typing import List

from .rating_request import RatingResponse
from .llm_service import analyze_with_claude

router = APIRouter()


@router.post("/rate-service", response_model=RatingResponse)
async def rate_service(
	summary: str = Form(..., description="Short summary of the experience"),
	details: str = Form(..., description="Detailed description of the service"),
	images: List[UploadFile] = File(..., description="1-5 images of the service"),
):
	if len(images) < 1 or len(images) > 5:
		raise HTTPException(status_code=400, detail="Please upload between 1 and 5 images")

	try:
		# Delegate to LLM service for analysis
		result = analyze_with_claude(summary, details, images)
		return RatingResponse(**result)
	except HTTPException:
		raise
	except Exception as e:
		raise HTTPException(status_code=500, detail=f"Error processing request: {str(e)}")

