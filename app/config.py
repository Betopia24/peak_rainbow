import os
from dotenv import load_dotenv
import anthropic

load_dotenv()

# Expose an initialized Anthropic client for other modules to use
client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
