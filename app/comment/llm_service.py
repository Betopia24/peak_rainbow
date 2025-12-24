import base64
import io
import json
from typing import List, Optional
from fastapi import UploadFile, HTTPException
from app.config import client

# Anthropic/LLM image size limits: Anthropic reports a 5 MB maximum for base64 image payloads
MAX_B64_BYTES = 5 * 1024 * 1024


def _compress_image_bytes(orig_bytes: bytes, target_bytes: int) -> Optional[bytes]:
	try:
		from PIL import Image
	except Exception:
		return None

	try:
		img = Image.open(io.BytesIO(orig_bytes))
		# Handle animated formats (GIF) - use first frame
		if hasattr(img, 'is_animated') and img.is_animated:
			img.seek(0)
		# HEIF/AVIF may need conversion, ensure we can work with it
		img.load()
	except Exception:
		return None

	# Convert to RGB, handling all transparency modes (RGBA, LA, P with transparency, etc.)
	try:
		if img.mode in ("RGBA", "LA", "P"):
			bg = Image.new("RGB", img.size, (255, 255, 255))
			if img.mode == "P":
				img = img.convert("RGBA")
			bg.paste(img, mask=img.split()[-1] if img.mode in ("RGBA", "LA") else None)
			img = bg
		elif img.mode != "RGB":
			img = img.convert("RGB")
	except Exception:
		try:
			img = img.convert("RGB")
		except Exception:
			return None

	# Progressive quality and size reduction for all formats
	for scale in [1.0, 0.85, 0.7, 0.55]:
		for quality in [85, 70, 55, 40]:
			if scale < 1.0:
				new_w = max(64, int(img.width * scale))
				new_h = max(64, int(img.height * scale))
				resized = img.resize((new_w, new_h), Image.LANCZOS)
			else:
				resized = img

			buf = io.BytesIO()
			try:
				resized.save(buf, format="JPEG", quality=quality, optimize=True)
			except Exception:
				continue

			data = buf.getvalue()
			if len(data) <= target_bytes:
				return data

	return None


def _prepare_content(summary: str, details: str, images: List[UploadFile]):
	content = [
		{
			"type": "text",
			"text": f"Service Experience Summary: {summary}\n\nDetailed Description: {details}\n\nPlease analyze the following images of this service:"
		}
	]

	allowed_types = {"image/jpeg", "image/png", "image/gif", "image/webp", "image/heif", "image/heic", "image/avif"}

	for idx, image in enumerate(images, 1):
		if image.content_type not in allowed_types:
			raise HTTPException(
				status_code=400,
				detail=f"Image {idx} has invalid type. Allowed: JPEG, PNG, GIF, WebP"
			)

		image_data = image.file.read()
		base64_image = base64.b64encode(image_data).decode("utf-8")
		media_type = image.content_type

		# Check base64-encoded size; compress if needed
		b64_len = len(base64_image.encode("utf-8"))
		if b64_len > MAX_B64_BYTES:
			compressed = _compress_image_bytes(image_data, MAX_B64_BYTES - 1024)
			if compressed is None:
				raise HTTPException(
					status_code=400,
					detail=(
						f"Image {idx} exceeds 5 MB limit and could not be compressed. "
						"Please upload a smaller image."
					),
				)
			base64_image = base64.b64encode(compressed).decode("utf-8")
			media_type = "image/jpeg"  # Compressed images are JPEG

		content.append({"type": "text", "text": f"\n\nImage {idx}:"})
		content.append({
			"type": "image",
			"source": {
				"type": "base64",
				"media_type": media_type,
				"data": base64_image,
			},
		})

	content.append({
		"type": "text",
		"text": """\n\nBased on the summary, details, and images provided, please:
1. Identify the service category. MUST be one of these exact categories:
   Towing, Car Repairs & Maintenance, Rental Listings, Handyman, Plumbing, Electrical, Carpentry, Concerts, Cleaning Services, Community Events, Food, Food Delivery, Restaurant, Local Markets, Yoga Studios, Gyms, Landlords, Therapists, Car Wash, Tutors
2. Provide a rating from 1.0 to 5.0 (where 5.0 is excellent). Do not give the fraction rating value. 
3. Indicate your confidence level (High, Medium, Low)
4. Create an enhanced, professional version of the user's summary (more detailed and well-written)
5. Create an enhanced, comprehensive version of the user's description (more articulate and complete)

Respond ONLY with a JSON object in this exact format:
{
	"category": "category name",
	"rating": 3,
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

