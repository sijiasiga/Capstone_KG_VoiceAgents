"""
LLM Provider Manager - Supports OpenAI, Anthropic, and Google
"""
import os
from typing import Optional, Dict, List, Any
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
            _anthropic_client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
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


def get_default_model() -> str:
    """Get default model name for current provider"""
    provider = os.getenv("LLM_PROVIDER", "openai").lower()
    if provider == "anthropic":
        return os.getenv("ANTHROPIC_MODEL", "claude-3-5-sonnet-20241022")
    elif provider == "google":
        return os.getenv("GOOGLE_MODEL", "gemini-pro")
    else:
        return os.getenv("OPENAI_MODEL", "gpt-4o-mini")


def chat_completion(messages: List[Dict[str, str]], 
                   model: Optional[str] = None,
                   temperature: float = 0,
                   provider: Optional[str] = None) -> Optional[str]:
    """
    Unified chat completion interface for all providers
    
    Args:
        messages: List of message dicts with 'role' and 'content'
        model: Model name (optional, uses default for provider)
        temperature: Temperature for generation
        provider: Provider name (optional, uses LLM_PROVIDER env var)
    
    Returns:
        Response text or None if error
    """
    provider = (provider or LLM_PROVIDER).lower()
    model = model or get_default_model()
    
    # OpenAI
    if provider == "openai":
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
    
    # Anthropic
    elif provider == "anthropic":
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
                    role = "user" if msg["role"] in ["user", "system"] else "assistant"
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
    
    # Google Gemini
    elif provider == "google":
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
            
            response = model_instance.generate_content(
                prompt,
                generation_config=genai.types.GenerationConfig(temperature=temperature)
            )
            return response.text
        except Exception as e:
            print(f"[LLM Error] Google: {e}")
            return None
    
    else:
        print(f"[LLM Error] Unknown provider: {provider}")
        return None


def audio_transcribe(audio_path: str, provider: Optional[str] = None) -> Optional[str]:
    """Transcribe audio file (currently only OpenAI Whisper supported)"""
    provider = (provider or LLM_PROVIDER).lower()
    
    # Only OpenAI supports audio transcription via API
    if provider == "openai":
        client = _get_openai_client()
        if client is None:
            return None
        try:
            with open(audio_path, "rb") as f:
                response = client.audio.transcriptions.create(
                    model="whisper-1",
                    file=f
                )
            return response.text
        except Exception as e:
            print(f"[STT Error] OpenAI: {e}")
            return None
    else:
        print(f"[STT] Audio transcription only supported with OpenAI provider")
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

