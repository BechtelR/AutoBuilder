# Python Quickstart for Agent Development Kit

Source: https://google.github.io/adk-docs/get-started/python/

## Overview
This guide covers getting started with ADK for Python, requiring Python 3.10+ and pip.

## Installation
Install via: `pip install google-adk`

Create and activate a virtual environment:
- **Creation:** `python -m venv .venv`
- **Windows CMD:** `.venv\Scripts\activate.bat`
- **Windows PowerShell:** `.venv\Scripts\Activate.ps1`
- **macOS/Linux:** `source .venv/bin/activate`

## Project Structure
After running `adk create my_agent`, the structure includes:
- `agent.py` – Main agent control code
- `.env` – API keys and project IDs
- `__init__.py`

## Sample Agent Implementation
The documentation provides a example with a `get_current_time` tool:
```python
from google.adk.agents.llm_agent import Agent

def get_current_time(city: str) -> dict:
    return {"status": "success", "city": city, "time": "10:30 AM"}

root_agent = Agent(
    model='gemini-3-flash-preview',
    name='root_agent',
    description="Tells the current time in a specified city.",
    instruction="Use the 'get_current_time' tool for this purpose.",
    tools=[get_current_time],
)
```

## API Key Configuration
Store your Gemini API key in `.env`: `GOOGLE_API_KEY="YOUR_API_KEY"`

The documentation notes that "ADK supports the use of many generative AI models" with configuration details in the Models & Authentication section.

## Running Your Agent
- **CLI:** `adk run my_agent`
- **Web Interface:** `adk web --port 8000` (run from parent directory)

⚠️ ADK Web is development-only, not for production use.

## Next Steps
Explore building agents through the provided tutorials and build guides.
