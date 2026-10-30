import os
import time
from dotenv import load_dotenv
from google import genai

load_dotenv()

client = genai.Client(
    api_key=os.getenv("GEMINI_API_KEY")
)

start = time.perf_counter()

print("Sending request to Gemini...", flush=True)

response = client.models.generate_content_stream(
    model="gemini-3.6-flash",
    contents="Reply with exactly: OK"
)

first_token = None

for chunk in response:
    if first_token is None:
        first_token = time.perf_counter()
        print(
            f"\nFirst response received in {first_token - start:.2f}s",
            flush=True
        )

    if chunk.text:
        print(chunk.text, end="", flush=True)

print(f"\n\nTotal time: {time.perf_counter() - start:.2f}s")