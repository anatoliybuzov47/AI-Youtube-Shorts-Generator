from pydantic import BaseModel,Field
from dotenv import load_dotenv
import os
import requests
import json

load_dotenv()

model_base_url = os.getenv("MODEL_BASE_URL")
api_key = os.getenv("OPENROUTER_API")
model = "tngtech/deepseek-r1t2-chimera:free"

if not api_key:
    raise ValueError("API key not found. Make sure it is defined in the .env file.")

class JSONResponse(BaseModel):
    """
    The response should strictly follow the following structure: -
     [
        {
        start: "Start time of the clip",
        content: "Highlight Text",
        end: "End Time for the highlighted clip"
        }
     ]
    """
    start: float = Field(description="Start time of the clip")
    content: str= Field(description="Highlight Text")
    end: float = Field(description="End time for the highlighted clip")

system = """
The input contains a timestamped transcription of a video.
Select a 1-miniute segment from the transcription that contains something interesting, useful, surprising, controversial, or thought-provoking.
The selected text should contain only complete sentences.
Do not cut the sentences in the middle.
The selected text should form a complete thought.
Return a JSON object with the following structure:
## Output 
{
    "start": "Start time of the segment in seconds (number)",
    "content": "The transcribed text from the selected segment (clean text only, NO timestamps)",
    "end": "End time of the segment in seconds (number)"
}
"""

def GetHighlight(Transcription):
    try:
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}"
        }

        payload = {
            "model": model,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": Transcription}
            ],
            "temperature": 1.0,
            "response_format": { "type": "json_object" }
        }

        print(f"Calling LLM ({model}) for highlight selection via HTTP...")
        response = requests.post(model_base_url, headers=headers, json=payload)
        response.raise_for_status()

        result = response.json()
        content_str = result['choices'][0]['message']['content']

        try:
            data = json.loads(content_str)
        except json.JSONDecodeError:
            # Fallback: try to find JSON in the string if it's wrapped in markdown
            import re
            match = re.search(r'\{.*\}', content_str, re.DOTALL)
            if match:
                data = json.loads(match.group(0))
            else:
                raise ValueError("Could not parse JSON from response")

        # Validate structure
        if 'start' not in data or 'end' not in data:
            print(f"Warning: Unexpected JSON structure: {data.keys()}")

        # Use Pydantic for validation if available, or manual
        try:
            response_obj = JSONResponse(**data)
            Start = float(response_obj.start)
            End = float(response_obj.end)
            Content = response_obj.content
        except Exception as e:
            # Manual fallback
            Start = float(data.get('start', 0))
            End = float(data.get('end', 0))
            Content = data.get('content', "")

        # Validate times
        if Start < 0 or End < 0:
            print(f"ERROR: Negative time values - Start: {Start}s, End: {End}s")
            return None, None

        if End <= Start:
            print(f"ERROR: Invalid time range - Start: {Start}s, End: {End}s (end must be > start)")
            return None, None

        # Log the selected segment
        print(f"\n{'='*60}")
        print(f"SELECTED SEGMENT DETAILS:")
        print(f"Time: {Start}s - {End}s ({End-Start}s duration)")
        print(f"Content: {Content}")
        print(f"{'='*60}\n")

        if Start==End:
            Ask = input("Error - Get Highlights again (y/n) -> ").lower()
            if Ask == "y":
                return GetHighlight(Transcription)
            return Start, End

        return Start,End

    except Exception as e:
        print(f"\n{'='*60}")
        print(f"ERROR IN GetHighlight FUNCTION:")
        print(f"{'='*60}")
        print(f"Exception type: {type(e).__name__}")
        print(f"Exception message: {str(e)}")
        if isinstance(e, requests.exceptions.HTTPError):
            print(f"Response: {e.response.text}")
        print(f"\nTranscription length: {len(Transcription)} characters")
        print(f"First 200 chars: {Transcription[:200]}...")
        print(f"{'='*60}\n")
        import traceback
        traceback.print_exc()
        return None, None

if __name__ == "__main__":
    print(GetHighlight(User))
