import os
from pathlib import Path

from openai import OpenAI

api_key = os.environ.get("OPENAI_API_KEY")
if not api_key:
    msg = "OpenAI API key not provided."
    raise ValueError(msg)

client = OpenAI(api_key=api_key)

# Generate voice 1
response1 = client.audio.speech.create(model="tts-1", voice="alloy", input="Hello, world...")

# Explicit Gap: Using a string of periods/dashes creates a more forced pause
response_gap = client.audio.speech.create(model="tts-1", voice="alloy", input=". . . . . .")

# Voice 2: Onyx (Deep, low-pitched, very different from Alloy)
response2 = client.audio.speech.create(model="tts-1", voice="onyx", input="Hello, earth...")

# Combine binary data
output_file = Path("hello_voices.mp3")
with open(output_file, "wb") as f:
    f.write(response1.content)
    f.write(response_gap.content)
    f.write(response2.content)

print(f"Success! Audio saved to {output_file}")
