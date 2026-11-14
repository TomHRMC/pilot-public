import logging

import httpx

from core.config import settings

logger = logging.getLogger(__name__)


async def transcribe_audio(file_bytes: bytes, filename: str) -> str:
    """
    POSTs to Whisper's /audio/transcriptions endpoint as multipart/form-data.
    """
    url = f"{settings.WHISPER_API_URL.rstrip('/')}/audio/transcriptions"

    # We simulate a file payload for httpx.
    # The whisper API expects a 'file' and 'model' field typically.
    files = {
        "file": (
            filename,
            file_bytes,
            "audio/mpeg",
        )  # Content-type might vary but generic works for whisper
    }
    data = {"model": settings.WHISPER_MODEL}

    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(url, files=files, data=data)
            response.raise_for_status()
            result = response.json()
            return result.get("text", "")
        except Exception as e:
            logger.error(f"Error transcribing audio: {e}")
            raise e


async def get_embedding(text: str) -> list[float]:
    """
    POSTs to Ollama's /embeddings endpoint using OLLAMA_EMBED_MODEL.
    """
    # Note: older ollama uses /api/embeddings, newer might use /api/embed.
    # We use /api/embeddings which is compatible with the standard model.
    url = f"{settings.OLLAMA_API_URL.rstrip('/')}/embeddings"

    payload = {"model": settings.OLLAMA_EMBED_MODEL, "prompt": text}

    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(url, json=payload)
            response.raise_for_status()
            result = response.json()
            return result.get("embedding", [])
        except Exception as e:
            logger.error(f"Error getting embedding: {e}")
            raise e


async def parse_intent(text: str, context: list) -> str:
    """
    POSTs to Ollama's /chat endpoint asking it to extract JSON entities.
    """
    url = f"{settings.OLLAMA_API_URL.rstrip('/')}/chat"

    system_prompt = (
        "You are an AI assistant that extracts intent and entities from user text. "
        "Return ONLY a valid JSON object with the following structure: "
        "{'intent': 'the_intent', 'entities': {'key': 'value'}}. "
        "Do not include any explanation or markdown formatting."
    )

    messages = [{"role": "system", "content": system_prompt}]

    # Optionally append previous context messages
    for msg in context:
        messages.append(msg)

    messages.append({"role": "user", "content": text})

    payload = {
        "model": settings.OLLAMA_CHAT_MODEL,
        "messages": messages,
        "stream": False,
        "format": "json",
    }

    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(url, json=payload, timeout=60.0)
            response.raise_for_status()
            result = response.json()
            # result is typically: {"message": {"role": "assistant", "content": "..."}}
            return result.get("message", {}).get("content", "{}")
        except Exception as e:
            logger.error(f"Error parsing intent: {e}")
            raise e


def generate_text_sync(prompt: str, max_tokens: int = 200) -> str:
    """
    Synchronous text generation via Ollama — for use in Celery tasks and
    the voice_persona_renderer.

    Uses httpx.Client (synchronous) to avoid asyncio.run() issues in
    environments where an event loop is already running (e.g., tests,
    FastAPI background tasks).

    Args:
        prompt: The prompt to send to Ollama
        max_tokens: Maximum number of tokens to generate (via num_predict)

    Returns:
        Generated text string from Ollama, or raises on failure.
    """
    url = f"{settings.OLLAMA_API_URL.rstrip('/')}/chat"
    messages = [{"role": "user", "content": prompt}]
    payload = {
        "model": settings.OLLAMA_CHAT_MODEL,
        "messages": messages,
        "stream": False,
        "options": {"num_predict": max_tokens},
    }
    with httpx.Client() as client:
        response = client.post(url, json=payload, timeout=60.0)
        response.raise_for_status()
        result = response.json()
        return result.get("message", {}).get("content", "")
