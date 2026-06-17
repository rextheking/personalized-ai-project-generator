"""AWS Lambda handler that exposes the agent behind API Gateway.

The frontend posts a JSON body like {"prompt": "..."} and gets back
{"response": "..."}. The agent runs once per request and returns text.
"""

import json

from agent.generator import ask

# CORS headers. In production, lock the origin down to your CloudFront domain
# instead of "*". See the README for how to set ALLOWED_ORIGIN.
import os

ALLOWED_ORIGIN = os.environ.get("ALLOWED_ORIGIN", "*")

CORS_HEADERS = {
    "Access-Control-Allow-Origin": ALLOWED_ORIGIN,
    "Access-Control-Allow-Headers": "Content-Type",
    "Access-Control-Allow-Methods": "OPTIONS,POST",
    "Content-Type": "application/json",
}

MAX_PROMPT_CHARS = 4000


def _response(status: int, body: dict) -> dict:
    return {
        "statusCode": status,
        "headers": CORS_HEADERS,
        "body": json.dumps(body),
    }


def handler(event, context):
    """API Gateway proxy integration entry point."""
    method = (
        event.get("requestContext", {}).get("http", {}).get("method")
        or event.get("httpMethod")
    )

    # Browsers send a preflight OPTIONS request before the POST.
    if method == "OPTIONS":
        return _response(200, {"ok": True})

    try:
        body = json.loads(event.get("body") or "{}")
    except json.JSONDecodeError:
        return _response(400, {"error": "Request body must be valid JSON."})

    prompt = (body.get("prompt") or "").strip()
    if not prompt:
        return _response(400, {"error": "Field 'prompt' is required."})
    if len(prompt) > MAX_PROMPT_CHARS:
        return _response(
            400,
            {"error": f"Prompt is too long. Limit is {MAX_PROMPT_CHARS} characters."},
        )

    try:
        answer = ask(prompt)
    except Exception as exc:  # noqa: BLE001
        # Log the detail for CloudWatch, return a generic message to the client.
        print(f"Agent error: {exc}")
        return _response(
            502, {"error": "The agent could not process that request. Try again."}
        )

    return _response(200, {"response": answer})
