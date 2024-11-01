from fastapi import FastAPI, Body
from fastapi.middleware.cors import CORSMiddleware
from fastapi.exceptions import HTTPException
from pydantic import ValidationError
from openai import OpenAI
from dotenv import load_dotenv
from typing import Any, Dict
import os
import importlib

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

load_dotenv()

client = OpenAI()


# dynamically loading of tools configurations
tool_mapping = {}
tools_dir = "tools"
for file_name in os.listdir(tools_dir):
    if file_name.endswith(".py") and file_name != "__init__.py":
        module_name = f"{tools_dir}.{file_name[:-3]}"  # Strip ".py"
        module = importlib.import_module(module_name)
        tool_mapping.update(module.tool_config)


@app.post("/api/v1/chat-tools")
async def process_tool(
    tool: str,
    inputParameters: Any = Body(...),
) -> Dict[str, Any]:

    if tool not in tool_mapping:
        raise HTTPException(status_code=400, detail="Invalid tool name")

    try:
        prompt_func = tool_mapping[tool]["prompt_func"]
        response_format = tool_mapping[tool]["response_format"]
        input_format = tool_mapping[tool]["input_format"]

        validated_input = input_format(**inputParameters)

        messages = prompt_func(inputParameters=validated_input)
        completion = client.beta.chat.completions.parse(
            model="gpt-4o-mini", messages=messages, response_format=response_format, temperature=0
        )

        response = completion.choices[0].message.parsed

        return {
            "tool": tool,
            "response": response,
        }

    except ValidationError as e:
        raise HTTPException(
            status_code=422,
            detail=e.errors(),
        )

    except Exception as e:
        raise HTTPException(status_code=422, detail=str(e))

@app.get("/api/v1/tools-options")
async def get_tool_options(tool_name: str) -> Dict[str, Any]:
    """
    Get the options for a specific tool.
    If no options are found, return an empty dictionary.
    """
    if tool_name not in tool_mapping:
        raise HTTPException(status_code=400, detail="Invalid tool name")

    # Retrieve the tool's options if they exist
    options = tool_mapping[tool_name].get("options", {})
    
    return {
        "tool": tool_name,
        "options": options
    }