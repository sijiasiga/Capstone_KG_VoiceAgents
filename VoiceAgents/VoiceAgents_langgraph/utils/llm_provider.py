"""
LLM Provider Manager - Supports OpenAI, Anthropic, and Google with fallback
"""
import os
from typing import Optional, Dict, List
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Initialize clients lazily
_openai_client = None
_anthropic_client = None
_google_client = None

USE_LLM = False
LLM_PROVIDER = os.getenv("LLM_PROVIDER", "openai").lower()


def _get_openai_client():
    """Get or create OpenAI client"""
    global _openai_client
    if _openai_client is None:
        try:
            from openai import OpenAI
            _openai_client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        except Exception:
            pass
    return _openai_client


def _get_anthropic_client():
    """Get or create Anthropic client"""
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
    """Get or create Google client"""
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
    """Get list of available providers based on API keys in environment"""
    available = []
    if os.getenv("OPENAI_API_KEY"):
        available.append("openai")
    if os.getenv("ANTHROPIC_API_KEY"):
        available.append("anthropic")
    if os.getenv("GOOGLE_API_KEY"):
        available.append("google")
    return available


def get_default_model(provider: Optional[str] = None) -> str:
    """Get default model name for specified provider"""
    env_provider = os.getenv("LLM_PROVIDER", "openai")
    provider_val = provider or env_provider
    provider_str = provider_val.lower() if provider_val else "openai"
    if provider_str == "anthropic":
        return os.getenv("ANTHROPIC_MODEL", "claude-3-5-sonnet-20241022")
    elif provider_str == "google":
        return os.getenv("GOOGLE_MODEL", "gemini-pro")
    else:
        return os.getenv("OPENAI_MODEL", "gpt-4o-mini")


def _try_openai_completion(messages: List[Dict[str, str]],
                           model: str,
                           temperature: float) -> Optional[str]:
    """Try OpenAI completion"""
    client = _get_openai_client()
    if client is None:
        return None
    try:
        response = client.chat.completions.create(
            model=model,
            messages=messages,
            temperature=temperature
        )
        return response.choices[0].message.content
    except Exception as e:
        print(f"[LLM Error] OpenAI: {e}")
        return None


def _try_google_completion(messages: List[Dict[str, str]],
                           model: str,
                           temperature: float) -> Optional[str]:
    """Try Google Gemini completion"""
    genai = _get_google_client()
    if genai is None:
        return None
    try:
        # Convert messages for Google format
        model_instance = genai.GenerativeModel(model)

        # Google format: combine system + user messages
        prompt_parts = []
        for msg in messages:
            if msg["role"] == "system":
                prompt_parts.append(f"System: {msg['content']}")
            elif msg["role"] == "user":
                prompt_parts.append(f"User: {msg['content']}")
            elif msg["role"] == "assistant":
                prompt_parts.append(f"Assistant: {msg['content']}")

        prompt = "\n\n".join(prompt_parts)

        gen_config = genai.types.GenerationConfig(
            temperature=temperature)
        response = model_instance.generate_content(
            prompt, generation_config=gen_config)
        return response.text
    except Exception as e:
        print(f"[LLM Error] Google: {e}")
        return None


def _try_anthropic_completion(messages: List[Dict[str, str]],
                              model: str,
                              temperature: float) -> Optional[str]:
    """Try Anthropic Claude completion"""
    client = _get_anthropic_client()
    if client is None:
        return None
    try:
        # Convert messages format for Anthropic
        system_msg = None
        conversation = []
        for msg in messages:
            if msg["role"] == "system":
                system_msg = msg["content"]
            else:
                # Anthropic uses 'user' and 'assistant' roles
                role = ("user" if msg["role"] in ["user", "system"]
                        else "assistant")
                conversation.append({
                    "role": role,
                    "content": msg["content"]
                })

        response = client.messages.create(
            model=model,
            max_tokens=4096,
            temperature=temperature,
            system=system_msg or "",
            messages=conversation
        )
        # Anthropic returns content as a list
        if response.content and len(response.content) > 0:
            return response.content[0].text
        return None
    except Exception as e:
        print(f"[LLM Error] Anthropic: {e}")
        return None


def chat_completion(
        messages: List[Dict[str, str]],
        model: Optional[str] = None,
        temperature: float = 0,
        provider: Optional[str] = None) -> Optional[str]:
    """
    Unified chat completion interface with automatic fallback
    Fallback order: openai -> google -> anthropic

    Args:
        messages: List of message dicts with 'role' and 'content'
        model: Model name (optional, uses default for provider)
        temperature: Temperature for generation
        provider: Provider name (optional, uses LLM_PROVIDER env var,
                 but will fallback to others)

    Returns:
        Response text or None if all providers fail
    """
    # Get available providers from .env
    available_providers = _get_available_providers()

    if not available_providers:
        print("[LLM Error] No LLM providers available (no API keys found)")
        return None

    # Determine primary provider
    primary_provider = (provider or LLM_PROVIDER).lower()

    # Fallback order: openai -> google -> anthropic
    # But prioritize the primary provider if specified
    fallback_order = ["openai", "google", "anthropic"]

    # If primary provider is specified and available, try it first
    if primary_provider in available_providers:
        # Reorder: primary first, then others in fallback order
        providers_to_try = [primary_provider]
        for p in fallback_order:
            if p != primary_provider and p in available_providers:
                providers_to_try.append(p)
    else:
        # Use fallback order for available providers
        providers_to_try = [
            p for p in fallback_order if p in available_providers]

    # Try each provider in order
    for provider_name in providers_to_try:
        provider_model = model or get_default_model(provider_name)
        result = None

        if provider_name == "openai":
            result = _try_openai_completion(
                messages, provider_model, temperature)
        elif provider_name == "google":
            result = _try_google_completion(
                messages, provider_model, temperature)
        elif provider_name == "anthropic":
            result = _try_anthropic_completion(
                messages, provider_model, temperature)

        if result is not None:
            if provider_name != primary_provider:
                msg = (f"[LLM Fallback] Using {provider_name} "
                       f"(primary {primary_provider} failed)")
                print(msg)
            return result

    # All providers failed
    print(f"[LLM Error] All available providers failed: {providers_to_try}")
    return None


def audio_transcribe(audio_path: str,
                     provider: Optional[str] = None) -> Optional[str]:
    """Transcribe audio file (only OpenAI Whisper supported)"""
    # Only OpenAI supports audio transcription via API
    available_providers = _get_available_providers()

    # Try OpenAI first (only provider with audio transcription)
    if "openai" in available_providers:
        client = _get_openai_client()
        if client is not None:
            try:
                with open(audio_path, "rb") as f:
                    response = client.audio.transcriptions.create(
                        model="whisper-1",
                        file=f
                    )
                return response.text
            except Exception as e:
                print(f"[STT Error] OpenAI: {e}")

    # Audio transcription only supported via OpenAI Whisper API
    msg = (f"[STT] Audio transcription requires OpenAI provider "
           f"(available: {available_providers})")
    print(msg)
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
