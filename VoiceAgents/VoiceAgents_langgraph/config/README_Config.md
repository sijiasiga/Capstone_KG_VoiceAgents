# Configuration Guide

This document describes where to find and modify all configurable parameters in the VoiceAgents system.

## Table of Contents

- [Global System Prompt](#global-system-prompt)
- [Agent-Specific Policies](#agent-specific-policies)
- [LLM Provider Configuration](#llm-provider-configuration)
- [STT/TTS Configuration](#stttts-configuration)
- [Safety Rules](#safety-rules)
- [Business Rules](#business-rules)

---

## Global System Prompt

**Location:** `policy/system_behavior.py`

**Purpose:** Defines the overall tone, safety boundaries, and operational guidelines for all agents.

**Key Variable:** `GLOBAL_SYSTEM_PROMPT`

**How to Modify:**
1. Open `policy/system_behavior.py`
2. Edit the `GLOBAL_SYSTEM_PROMPT` string
3. Changes apply automatically to all LLM calls

**Example:**
```python
GLOBAL_SYSTEM_PROMPT = """
You are a healthcare assistant designed for post-discharge patient triage and follow-up.
You are not a licensed clinician.
Always include clear safety language.
Never provide diagnosis, prescriptions, or treatment plans.
Direct RED-flag cases to emergency care immediately.
"""
```

**Note:** This prompt is automatically injected into all LLM completion calls via `utils/llm_provider.py`.

---

## Agent-Specific Policies

**Location:** `policy/agents/`

**Purpose:** Define each agent's permissions, constraints, and escalation logic.

**Files:**
- `appointment_policy.json` - Appointment agent scope and restrictions
- `followup_policy.json` - Follow-up agent scope and triage rules
- `medication_policy.json` - Medication agent scope and risk assessment
- `caregiver_policy.json` - Caregiver agent scope and data aggregation
- `help_policy.json` - Help agent scope and redirect rules

**How to Modify:**
1. Open the relevant policy JSON file
2. Modify the JSON structure (scope, restrictions, escalate_on, etc.)
3. Restart the application for changes to take effect

**Structure:**
```json
{
  "scope": ["action1", "action2"],
  "restrictions": ["restriction1", "restriction2"],
  "escalate_on": ["condition1", "condition2"],
  "triage_required": true
}
```

**Note:** Policies are loaded at module initialization. See `nodes/*.py` for how policies are used.

---

## LLM Provider Configuration

**Location:** `utils/llm_provider.py`

**Purpose:** Configure which LLM provider to use and default models.

### Environment Variables (`.env` file)

**Primary Configuration:**
- `LLM_PROVIDER` - Set to `openai`, `anthropic`, or `google` (default: `openai`)

**OpenAI Configuration:**
- `OPENAI_API_KEY` - Your OpenAI API key
- `OPENAI_MODEL` - Model name (default: `gpt-4o-mini`)

**Anthropic Configuration:**
- `ANTHROPIC_API_KEY` - Your Anthropic API key
- `ANTHROPIC_MODEL` - Model name (default: `claude-3-5-sonnet-20241022`)

**Google Configuration:**
- `GOOGLE_API_KEY` - Your Google API key
- `GOOGLE_MODEL` - Model name (default: `gemini-1.5-pro`)
  - **IMPORTANT**: `gemini-pro` is deprecated. Use `gemini-1.5-pro` or `gemini-1.5-flash`
  - The code will automatically map `gemini-pro` → `gemini-1.5-pro` for backward compatibility

### Code Configuration

**Location:** `utils/llm_provider.py`

**Functions to Modify:**
- `get_default_model(provider)` - Change default model per provider (lines ~70-80)
- `_get_available_providers()` - Modify provider detection logic (lines ~58-67)
- `chat_completion()` - Adjust fallback order or behavior (lines ~224-297)

**Fallback Order:**
The system automatically falls back through providers in this order:
1. Primary provider (from `LLM_PROVIDER` env var)
2. OpenAI
3. Google
4. Anthropic

**How to Modify:**
1. Edit `.env` file for API keys and primary provider
2. Modify `get_default_model()` for model names
3. Adjust fallback order in `chat_completion()` if needed

---

## STT/TTS Configuration

**Location:** `utils/__init__.py`

### Text-to-Speech (TTS)

**Function:** `say(text, voice=False)`

**Configuration Points:**
- Voice selection (lines ~119-132)
- Speech rate (line ~131: `eng.setProperty("rate", 155)`)
- Voice language preference

**How to Modify:**
1. Open `utils/__init__.py`
2. Find the `say()` function
3. Adjust voice selection logic or speech rate
4. Modify voice search criteria if needed

**Dependencies:**
- `pyttsx3` - Python text-to-speech library

### Speech-to-Text (STT)

**Functions:**
- `stt_transcribe(path)` - Transcribe audio file
- `mic_listen_once(timeout, phrase_time_limit)` - Record from microphone

**Configuration Points:**
- Faster Whisper model size (line ~42: `WhisperModel("base")`)
- Speech recognition settings (lines ~149-155)
- Audio format support (line ~125: `[".wav", ".aif", ".aiff", ".flac", ".mp3", ".m4a"]`)

**How to Modify:**
1. Open `utils/__init__.py`
2. Find `stt_transcribe()` or `mic_listen_once()` functions
3. Adjust model size, recognition settings, or supported formats

**Priorities:**
1. Local faster-whisper (if available)
2. OpenAI Whisper API (if `USE_LLM` and OpenAI key available)
3. Google Speech Recognition (fallback)

**Dependencies:**
- `faster_whisper` - Local Whisper model (optional)
- `speech_recognition` - Google Speech Recognition (fallback)
- `pyaudio` - Microphone access

---

---

## Business Rules

**Location:** `data/policy_config.json`

**Purpose:** Business rules for appointment scheduling, telehealth, referrals, etc.

**Current Rules:**
- `red_flags` - Emergency symptoms
- `orange_flags` - Concerning symptoms
- `telehealth_allowed` - Which appointment types allow telehealth
- `referral_required_plans` - Insurance plans requiring referrals

**How to Modify:**
1. Open `data/policy_config.json`
2. Modify JSON structure
3. Update agent code if new rule types are added

**Note:** Also see hardcoded rules in `nodes/appointment.py` (POLICY dictionary) for post-op windows and business logic.

---

## Logging Configuration

**Location:** `utils/logging_utils.py`

**Purpose:** Configure log file locations and formats.

**Log Files:**
- `logs/appointment_agent_log.jsonl`
- `logs/followup_agent_log.jsonl`
- `logs/med_agent_log.jsonl`
- `logs/caregiver_summaries.jsonl`
- `logs/orchestration_log.jsonl`
- `logs/fallback_log.jsonl`

**How to Modify:**
1. Open `utils/logging_utils.py`
2. Change log file paths (lines ~16-21)
3. Modify log schema in `write_log()` function (lines ~30-65)

**Log Schema:**
```python
{
    "timestamp": "ISO format",
    "agent": "agent_name",
    "level": "info|warning|error",
    "message": "log message",
    "risk": "RED|ORANGE|GREEN",
    "context": {...}
}
```

---

## Database Configuration

**Location:** `database.py`

**Purpose:** Configure data source paths.

**Data Files:**
- `data/patients.csv`
- `data/appointments.csv`
- `data/prescriptions.csv`
- `data/caregivers.csv`
- `data/symptom_codes.csv`
- `data/drug_knowledge.csv`
- `logs/symptom_logs.csv` - Symptom tracking logs (runtime data, not static data)

**How to Modify:**
1. Open `database.py`
2. Change `DATA_DIR` path (line ~15)
3. Update file names if needed

**Note:** All data files are in CSV format. Ensure CSV structure matches expected schema.

---

## Quick Reference

| Configuration | Location | File |
|--------------|----------|------|
| Global Prompt | Policy | `policy/system_behavior.py` |
| Agent Policies | Policy | `policy/agents/*.json` |
| LLM Provider | Environment | `.env` |
| LLM Defaults | Code | `utils/llm_provider.py` |
| TTS Settings | Code | `utils/__init__.py` (say function) |
| STT Settings | Code | `utils/__init__.py` (stt functions) |
| Business Rules | Data | `data/policy_config.json` |
| Log Files | Code | `utils/logging_utils.py` |
| Data Sources | Code | `database.py` |

---

## Tips

1. **Always restart the application** after modifying policy files or environment variables
2. **Test changes incrementally** - modify one configuration at a time
3. **Check logs** in `logs/` directory to verify configuration changes
4. **Backup original files** before making significant changes
5. **Use environment variables** for API keys - never commit them to git

---

For questions or issues, see the main [README.md](../README.md) or [Safety_and_Boundaries.md](../docs/Safety_and_Boundaries.md).

