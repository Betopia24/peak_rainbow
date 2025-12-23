import base64
import json
from typing import List
from fastapi import UploadFile, HTTPException
from app.config import client


def _prepare_content(summary: str, details: str, images: List[UploadFile]):
	content = [
		{
			"type": "text",
			"text": f"Service Experience Summary: {summary}\n\nDetailed Description: {details}\n\nPlease analyze the following images of this service:"
		}
	]

	allowed_types = {"image/jpeg", "image/png", "image/gif", "image/webp"}

	for idx, image in enumerate(images, 1):
		if image.content_type not in allowed_types:
			raise HTTPException(
				status_code=400,
				detail=f"Image {idx} has invalid type. Allowed: JPEG, PNG, GIF, WebP"
			)

		image_data = image.file.read()
		base64_image = base64.b64encode(image_data).decode("utf-8")

		content.append({"type": "text", "text": f"\n\nImage {idx}:"})
		content.append({
			"type": "image",
			"source": {
				"type": "base64",
				"media_type": image.content_type,
				"data": base64_image,
			},
		})

	content.append({
		"type": "text",
		"text": """\n\nBased on the summary, details, and images provided, please:
1. Identify the service category (e.g., Restaurant, Hotel, Salon, Transportation, Healthcare, Retail, etc.)
2. Provide a rating from 1.0 to 5.0 (where 5.0 is excellent). Do not give the fraction rating value. 
3. Indicate your confidence level (High, Medium, Low)
4. Create an enhanced, professional version of the user's summary (more detailed and well-written)
5. Create an enhanced, comprehensive version of the user's description (more articulate and complete)

Respond ONLY with a JSON object in this exact format:
{
	"category": "category name",
	"rating": 4.5,
	"confidence": "High/Medium/Low",
	"enhanced_summary": "enhanced professional summary",
	"enhanced_description": "enhanced comprehensive description"
}""",
	})

	return content


def analyze_with_claude(summary: str, details: str, images: List[UploadFile]):
	content = _prepare_content(summary, details, images)

	message = client.messages.create(
		model="claude-sonnet-4-5",
		max_tokens=2048,
		messages=[{"role": "user", "content": content}],
	)

	# Extract and sanitize response text
	response_text = message.content[0].text
	response_text = response_text.strip()

	if response_text.startswith("```json"):
		response_text = response_text[7:]
	if response_text.startswith("```"):
		response_text = response_text[3:]
	if response_text.endswith("```"):
		response_text = response_text[:-3]

	response_text = response_text.strip()

	try:
		return json.loads(response_text)
	except json.JSONDecodeError as e:
		raise HTTPException(status_code=500, detail=f"Failed to parse Claude's response: {str(e)}")

