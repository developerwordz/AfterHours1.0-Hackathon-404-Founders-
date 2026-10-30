
import os
from dotenv import load_dotenv
from google import genai
from google.genai import types

load_dotenv()

client = genai.Client(
    api_key=os.getenv("GEMINI_API_KEY")
)

tool = types.Tool(
    function_declarations=[
        types.FunctionDeclaration(
            name="get_factory_status",
            description="Retrieve the current status of the textile factory.",
            parameters=types.Schema(
                type=types.Type.OBJECT,
                properties={}
            )
        )
    ]
)

response = client.models.generate_content(
    model="gemini-3.8-flash",
    contents="A machine has failed. I need to inspect the factory before deciding what to do. Use the appropriate tool.",
    config=types.GenerateContentConfig(
        tools=[tool],
        tool_config=types.ToolConfig(
            function_calling_config=types.FunctionCallingConfig(
                mode="ANY"
            )
        )
    )
)

for candidate in response.candidates:
    for part in candidate.content.parts:
        if part.function_call:
            print("Gemini selected tool:", part.function_call.name)
            print("Arguments:", part.function_call.args)
