"""LLM integration via Ollama for AI features."""
import ollama

from .config import get_config

STYLE_PROMPTS = {
    "formal": "Use formal, professional language. Be polite and precise.",
    "casual": "Use casual, friendly language. Be conversational but clear.",
    "very_casual": "Use very casual language. Be relaxed and informal, like texting a friend.",
}


def _get_client() -> ollama.Client:
    """Get Ollama client."""
    config = get_config().ollama
    return ollama.Client(host=config["base_url"])


def _get_model() -> str:
    """Get configured model name."""
    return get_config().ollama["model"]


def _get_style_prompt() -> str:
    """Get the style instruction based on config."""
    style = get_config().style
    return STYLE_PROMPTS.get(style, STYLE_PROMPTS["casual"])


def rewrite(text: str, instruction: str) -> str:
    """
    Rewrite text according to an instruction.

    Args:
        text: The original text to rewrite
        instruction: How to rewrite it (e.g., "make it more professional")

    Returns:
        Rewritten text
    """
    client = _get_client()
    style = _get_style_prompt()

    prompt = f"""Rewrite the following text according to the instruction.
Only output the rewritten text, nothing else.

Style: {style}

Instruction: {instruction}

Text to rewrite:
{text}

Rewritten text:"""

    response = client.generate(
        model=_get_model(),
        prompt=prompt,
        options={
            "temperature": 0.7,
            "num_predict": 1024,
        },
    )

    return response["response"].strip()


def context_reply(context: str, intent: str) -> str:
    """
    Generate a reply based on context (e.g., a conversation) and user's intent.

    Args:
        context: The conversation or context (usually from clipboard)
        intent: What the user wants to say/reply (e.g., "agree to the meeting")

    Returns:
        Generated reply text
    """
    client = _get_client()
    style = _get_style_prompt()

    prompt = f"""Based on the conversation context below, write a reply that expresses the given intent.
Only output the reply text, nothing else. Do not include greetings unless appropriate for the context.

Style: {style}

Conversation context:
{context}

Intent for reply: {intent}

Reply:"""

    response = client.generate(
        model=_get_model(),
        prompt=prompt,
        options={
            "temperature": 0.7,
            "num_predict": 1024,
        },
    )

    return response["response"].strip()


def improve_transcription(text: str) -> str:
    """
    Clean up a transcription.

    Args:
        text: Raw transcribed text

    Returns:
        Cleaned up text with proper punctuation and formatting
    """
    client = _get_client()

    response = client.chat(
        model=_get_model(),
        messages=[
            {"role": "user", "content": f"Fix punctuation and capitalization in this text. Convert spoken symbols like 'forward slash' to '/'. Output ONLY the fixed text:\n\n{text}"},
        ],
        options={
            "temperature": 0.1,
            "num_predict": 256,
        },
    )

    return response["message"]["content"].strip()


def check_ollama_available() -> bool:
    """Check if Ollama is running and the model is available."""
    try:
        client = _get_client()
        client.list()
        return True
    except Exception:
        return False


def ensure_model_available() -> bool:
    """Check if the configured model is available, pull if not."""
    try:
        client = _get_client()
        model_name = _get_model()

        # Check if model exists
        response = client.list()
        model_names = [m.model.split(":")[0] for m in response.models]

        if model_name.split(":")[0] not in model_names:
            print(f"Pulling model {model_name}...")
            client.pull(model_name)

        return True
    except Exception as e:
        print(f"Error checking/pulling model: {e}")
        return False
