from pydantic import BaseModel

class RatingResponse(BaseModel):
	category: str
	rating: float
	confidence: str
	enhanced_summary: str
	enhanced_description: str
