"""
LLM Provider Manager - Supports OpenAI, Anthropic, and Google with fallback.

Provider and fallback behavior is controlled by environment variables:

- LLM_PROVIDER: primary provider (e.g., 'anthropic', 'openai', 'google')
- LLM_FALLBACK_ORDER: comma-separated list of providers in order of preference,
  e.g. 'anthropic,google,openai'

Model names are also configurable via env:

- OPENAI_MODEL
- ANTHROPIC_MODEL
- GOOGLE_MODEL
"""

import os
import time
from typing import Optional, Dict, List, Tuple
from dotenv import load_dotenv
from .logging_utils import get_conversation_logger

# Import global system prompt
try:
    from ..policy.system_behavior import GLOBAL_SYSTEM_PROMPT
except ImportError:
    # Fallback if policy module not available
    GLOBAL_SYSTEM_PROMPT = ""


# Load environment variables
load_dotenv()

# Initialize clients lazily
_openai_client = None
_anthropic_client = None
_google_client = None

USE_LLM = False


def _get_openai_client():
    """Get or create OpenAI client."""
    global _openai_client
    if _openai_client is None:
        try:
            from openai import OpenAI
            _openai_client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        except Exception:
            pass
    return _openai_client


def _get_anthropic_client():
    """Get or create Anthropic client."""
    global _anthropic_client
    if _anthropic_client is None:
        try:
            import anthropic
            api_key = os.getenv("ANTHROPIC_API_KEY")
            _anthropic_client = anthropic.Anthropic(api_key=api_key)
        except Exception:
            pass
    return _anthropic_client


def _get_google_client():
    """Get or create Google Gemini client."""
    global _google_client
    if _google_client is None:
        try:
            import google.generativeai as genai
            genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))
            _google_client = genai
        except Exception:
            pass
    return _google_client


def _get_available_providers() -> List[str]:
    """Get list of available providers based on API keys in environment."""
    available: List[str] = []
    if os.getenv("OPENAI_API_KEY"):
        available.append("openai")
    if os.getenv("ANTHROPIC_API_KEY"):
        available.append("anthropic")
    if os.getenv("GOOGLE_API_KEY"):
        available.append("google")
    return available


def _normalize_provider_name(name: str) -> str:
    """
    Normalize provider aliases from env (e.g., 'open' -> 'openai', 'gemini' -> 'google').
    """
    if not name:
        return ""
    n = name.strip().lower()
    if n in {"open", "openai", "oai", "gpt"}:
        return "openai"
    if n in {"anthropic", "claude"}:
        return "anthropic"
    if n in {"google", "gemini", "g"}:
        return "google"
    return n


def _get_fallback_order() -> List[str]:
    """
    Compute fallback order from environment:

    - LLM_PROVIDER is the preferred primary, defaulting to 'openai'.
    - LLM_FALLBACK_ORDER is a comma-separated list, e.g.:
        'openai,anthropic,google'

    We normalize names and deduplicate while preserving order.
    If configuration is missing or invalid, a sane default is used.
    """
    # Default primary: openai
    primary = _normalize_provider_name(
        os.getenv("LLM_PROVIDER", "openai")
    )

    # Default fallback list: openai -> anthropic -> google
    raw_order = os.getenv(
        "LLM_FALLBACK_ORDER",
        "openai,anthropic,google"
    )
    parts = [
        _normalize_provider_name(p)
        for p in raw_order.split(",")
        if p.strip()
    ]

    # Ensure primary is first
    if primary and primary not in parts:
        parts.insert(0, primary)

    # Deduplicate while preserving order
    unique_order: List[str] = []
    for p in parts:
        if p and p not in unique_order:
            unique_order.append(p)

    # Fallback safety: if env is empty or invalid, use a sane default
    if not unique_order:
        unique_order = ["openai", "anthropic", "google"]

    return unique_order


def get_default_model(provider: Optional[str] = None) -> str:
    """
    Get default model name for specified provider.

    Model names must match current API offerings:

    - OpenAI: 'gpt-4o-mini', 'gpt-4o', etc.
    - Anthropic: 'claude-3.7-sonnet' (or updated Claude model)
    - Google: 'gemini-1.5-flash' or 'gemini-1.5-pro'
    """
    # DEFAULT PROVIDER: openai
    env_provider = os.getenv("LLM_PROVIDER", "openai")
    provider_val = provider or env_provider
    provider_str = provider_val.lower() if provider_val else "openai"

    if provider_str == "openai":
        return os.getenv("OPENAI_MODEL", "gpt-4o-mini")
    elif provider_str == "anthropic":
        return os.getenv("ANTHROPIC_MODEL", "claude-3.7-sonnet")
    elif provider_str == "google":
        return os.getenv("GOOGLE_MODEL", "gemini-1.5-flash")
    else:
        # Default to OpenAI if provider not recognized
        return os.getenv("OPENAI_MODEL", "gpt-4o-mini")


def _try_openai_completion(
    messages: List[Dict[str, str]],
    model: str,
    temperature: float,
) -> Optional[str]:
    """Try OpenAI completion."""
    client = _get_openai_client()
    if client is None:
        return None
    try:
        response = client.chat.completions.create(
            model=model,
            messages=messages,
            temperature=temperature,
        )
        return response.choices[0].message.content
    except Exception as e:
        logger = get_conversation_logger()
        logger.error(f"[LLM Error] OpenAI: {e}")
        return None


def _try_google_completion(
    messages: List[Dict[str, str]],
    model: str,
    temperature: float,
) -> Optional[str]:
    """
    Try Google Gemini completion.

    Uses the model name from get_default_model(), which returns a current model.
    """
    genai = _get_google_client()
    if genai is None:
        return None

    # Remove 'models/' prefix if present (API might add it)
    actual_model = model
    if actual_model.startswith("models/"):
        actual_model = actual_model.replace("models/", "")

    try:
        # Convert messages for Google format
        model_instance = genai.GenerativeModel(actual_model)

        # Google format: combine system + user messages into a single prompt
        prompt_parts: List[str] = []
        for msg in messages:
            if msg["role"] == "system":
                prompt_parts.append(f"System: {msg['content']}")
            elif msg["role"] == "user":
                prompt_parts.append(f"User: {msg['content']}")
            elif msg["role"] == "assistant":
                prompt_parts.append(f"Assistant: {msg['content']}")

        prompt = "\n\n".join(prompt_parts)

        gen_config = genai.types.GenerationConfig(
            temperature=temperature
        )
        response = model_instance.generate_content(
            prompt,
            generation_config=gen_config,
        )
        return response.text
    except Exception as e:
        error_msg = str(e)
        logger = get_conversation_logger()
        # Provide helpful error message for model name issues
        if "not found" in error_msg or "404" in error_msg:
            logger.warning(
                f"[LLM Error] Google: Model '{model}' not found. "
                f"Update GOOGLE_MODEL in .env to use current model, e.g.: "
                f"'gemini-2.0-flash' or 'gemini-pro-latest'. "
                f"Error: {e}"
            )
        else:
            logger.error(f"[LLM Error] Google: {e}")
        return None


def _try_anthropic_completion(
    messages: List[Dict[str, str]],
    model: str,
    temperature: float,
) -> Optional[str]:
    """
    Try Anthropic Claude completion.

    Model names should be like 'claude-3-5-sonnet-20240620'.
    """
    client = _get_anthropic_client()
    if client is None:
        return None
    try:
        # Convert messages format for Anthropic
        system_msg = None
        conversation: List[Dict[str, str]] = []
        for msg in messages:
            if msg["role"] == "system":
                system_msg = msg["content"]
            else:
                # Anthropic uses 'user' and 'assistant' roles
                role = "user" if msg["role"] in ["user", "system"] else "assistant"
                conversation.append(
                    {
                        "role": role,
                        "content": msg["content"],
                    }
                )

        response = client.messages.create(
            model=model,
            max_tokens=4096,
            temperature=temperature,
            system=system_msg or "",
            messages=conversation,
        )
        # Anthropic returns content as a list
        if response.content and len(response.content) > 0:
            return response.content[0].text
        return None
    except Exception as e:
        error_msg = str(e)
        logger = get_conversation_logger()
        # Provide helpful error message for model name issues
        if "not found" in error_msg or "404" in error_msg:
            logger.warning(
                f"[LLM Error] Anthropic: Model '{model}' not found. "
                f"Update ANTHROPIC_MODEL in .env to use a current model, e.g.: "
                f"'claude-3-5-sonnet-20240620'. "
                f"Error: {e}"
            )
        else:
            logger.error(f"[LLM Error] Anthropic: {e}")
        return None


def _inject_system_prompt(
    messages: List[Dict[str, str]]
) -> List[Dict[str, str]]:
    """
    Inject GLOBAL_SYSTEM_PROMPT into messages if not already present.
    If a system message exists, prepend global prompt to it.
    """
    if not GLOBAL_SYSTEM_PROMPT.strip():
        return messages

    # Check if system message already exists
    has_system = any(msg.get("role") == "system" for msg in messages)

    if has_system:
        # Prepend global prompt to existing system message
        enhanced_messages: List[Dict[str, str]] = []
        for msg in messages:
            if msg.get("role") == "system":
                global_prompt = GLOBAL_SYSTEM_PROMPT.strip()
                existing_content = msg.get("content", "")
                combined = f"{global_prompt}\n\n{existing_content}"
                enhanced_messages.append(
                    {"role": "system", "content": combined}
                )
            else:
                enhanced_messages.append(msg)
        return enhanced_messages
    else:
        # Prepend system message with global prompt
        global_content = GLOBAL_SYSTEM_PROMPT.strip()
        return [{"role": "system", "content": global_content}] + messages


def chat_completion(
    messages: List[Dict[str, str]],
    model: Optional[str] = None,
    temperature: float = 0,
    provider: Optional[str] = None,
) -> Optional[Tuple[str, str, str, int]]:
    """
    Unified chat completion interface with automatic fallback.

    Fallback behavior is controlled by environment variables:

    - LLM_PROVIDER: primary provider (e.g., 'openai', 'anthropic', 'google')
      Defaults to 'openai'.
    - LLM_FALLBACK_ORDER: comma-separated list of providers in order of
      preference, e.g. 'openai,anthropic,google'.
      Defaults to 'openai,anthropic,google'.

    Only providers with valid API keys are actually attempted.
    
    Returns:
        Tuple of (response_text, provider_name, model_name) or None if all providers failed.
    """
    # Inject global system prompt
    messages = _inject_system_prompt(messages)

    logger = get_conversation_logger()
    
    # Get available providers from .env (those with API keys)
    available_providers = _get_available_providers()
    if not available_providers:
        logger.error("[LLM Error] No LLM providers available (no API keys found)")
        return None

    # Determine fallback order from environment
    fallback_order = _get_fallback_order()

    # Only include providers that have API keys configured
    providers_to_try = [
        p for p in fallback_order if p in available_providers
    ]

    if not providers_to_try:
        logger.error("[LLM Error] No providers available in configured fallback order")
        return None

    # Try each provider in sequence order
    for idx, provider_name in enumerate(providers_to_try):
        # Always use provider-specific default model (ignore model parameter)
        provider_model = get_default_model(provider_name)
        result: Optional[str] = None
        latency_ms: int = 0

        start_time = time.time()
        if provider_name == "openai":
            result = _try_openai_completion(messages, provider_model, temperature)
        elif provider_name == "google":
            result = _try_google_completion(messages, provider_model, temperature)
        elif provider_name == "anthropic":
            result = _try_anthropic_completion(messages, provider_model, temperature)
        elapsed_ms = int((time.time() - start_time) * 1000)

        if result is not None:
            # Log fallback message if not the first provider
            if idx > 0:
                prev_provider = providers_to_try[idx - 1]
                logger.warning(
                    f"[LLM Fallback] Using {provider_name} "
                    f"(previous provider '{prev_provider}' failed)"
                )
            return (result, provider_name, provider_model, elapsed_ms)

    # All providers failed
    logger.error(f"[LLM Error] All available providers failed: {providers_to_try}")
    return None


def audio_transcribe(
    audio_path: str,
    provider: Optional[str] = None,
) -> Optional[tuple[str, str]]:
    """
    Transcribe audio file using OpenAI Whisper API.

    Returns tuple of (transcription_text, backend_name) where backend_name is
    "openai_whisper" for OpenAI API or None if failed.
    
    Model name is read from ASR_MODEL environment variable (defaults to 'whisper-1').
    """
    available_providers = _get_available_providers()
    asr_model = os.getenv("ASR_MODEL", "whisper-1")

    # Try OpenAI Whisper API first
    if "openai" in available_providers:
        client = _get_openai_client()
        if client is not None:
            try:
                with open(audio_path, "rb") as f:
                    response = client.audio.transcriptions.create(
                        model=asr_model,
                        file=f,
                    )
                logger = get_conversation_logger()
                logger.info(f"[ASR] Using backend: {asr_model}")
                return (response.text, "openai_whisper")
            except Exception as e:
                logger = get_conversation_logger()
                logger.error(f"[STT Error] OpenAI Whisper API failed: {e}")
    else:
        logger = get_conversation_logger()
        logger.warning(f"[ASR] OpenAI not available for Whisper (available: {available_providers})")

    # OpenAI Whisper API not available or failed
    return None


# Check if any LLM is available
try:
    _get_openai_client()
    USE_LLM = True
except Exception:
    try:
        _get_anthropic_client()
        USE_LLM = True
    except Exception:
        try:
            _get_google_client()
            USE_LLM = True
        except Exception:
            USE_LLM = False
