# 🧠 Orchestration Agent (Router + STT/TTS + Logging)

This module is the **central router** in the CMU x Zyter Capstone Voice Agent System.  
It listens to user input (text, speech, or audio), detects intent, and routes the message to the appropriate sub-agent.

---

## 🎯 Purpose

| Function | Description |
|----------|-------------|
| **Intent Detection** | Determines whether the input relates to appointments, symptoms, medications, or caregiver updates. |
| **Routing** | Sends the request to the correct specialized agent. |
| **Fallback Handling** | Uses LLM (OpenAI GPT-4o-mini) for intent classification; if uncertain, falls back to rule-based parsing. |
| **STT / TTS Support** | Speech-to-text (optional) and text-to-speech response playback. |
| **Unified Logging** | Logs every interaction (intent, patient_id, agent response) in JSONL format. |

---

## ⚙️ Core Workflow

### Step 1: Listen
- Accepts **typed text**, **audio file**, or **microphone input**.  
- Audio is converted using **SpeechRecognition (STT)**.  

### Step 2: Parse Intent
- Primary: Uses OpenAI's **GPT-4o-mini** model.  
- Fallback: Uses keyword rules (ensures routing works offline).  
- Recognized intents:
  - `appointment`
  - `followup`
  - `medication`
  - `caregiver`
  - `help`

### Step 3: Route to Sub-Agent

Each recognized intent triggers a different specialized agent:

| Intent | Routed Agent | Example Input | Example Response |
|--------|--------------|---------------|------------------|
| `appointment` | Appointment Agent | "I am patient 10004235, can you check my appointment?" | "Your Follow-up - Cardiology with Dr. Johnson on October 08 at 02:20 PM is confirmed." |
| `followup` | Follow-Up Agent | "I feel dizzy 7 out of 10 and shortness of breath." | "I've logged your symptom (shortness of breath). Since it occurred more than twice this week, I'll notify your provider." |
| `medication` | Medication Agent | "I forgot to take my Lasix this morning." | "Furosemide: Take as soon as you remember unless the next dose is near." |
| `caregiver` | Caregiver Agent | "Give me this week's caregiver update for 10004235." | "Caregiver Update for Alice Lee (Mother: Wong Parent)… Overall status: MODERATE." |
| `help` | System Help | "What can you do?" | "I can help with appointments, symptoms, medications, and caregiver summaries." |

---

## 🔁 Fallback Logic (LLM → Rules)

If the LLM response is `"help"` (uncertain classification), the system automatically re-parses the message using **rule-based detection**, ensuring:
- Offline mode still works
- Medical phrases like "shortness of breath" or "dizzy" correctly trigger **follow-up**
- Robust routing even if OpenAI returns ambiguous intent

**Example console output:**
```
[DEBUG] LLM intent → help, patient_id → None
[DEBUG] LLM fallback → using rule intent followup
```

---

## 🧩 Repo Layout
```
orchestration_agent/
├── README.md
├── demos/
│   ├── orchestration_agent_workflow.py
│   └── logs/
│       └── orchestration_log.jsonl
└── relies on other sub-agents:
    ├── ../appointment_agent/
    ├── ../followup_agent/
    ├── ../medication_agent/
    └── ../caregiver_agent/
```

## 🧠 Example Interaction
```bash
$ python -m orchestration_agent.demos.orchestration_agent_workflow
```
```
Orchestration Agent (Router + STT/TTS)
Commands:
  :voice on | :voice off            -> toggle TTS
  pid <8digit>                      -> set default patient_id context
  :stt <path_to_audio.wav/mp3>      -> transcribe then route
  :mic on                           -> speak one sentence to route
  quit                              -> exit
```

### Example Session
```
You: I am patient 10004235, can you check my appointment?
[DEBUG] LLM intent → appointment, patient_id → 10004235
Agent: Your Follow-up - Cardiology with Dr. Johnson on October 08 at 02:20 PM is confirmed.

You: I feel dizzy 7 out of 10 and shortness of breath.
[DEBUG] LLM intent → help, patient_id → None
[DEBUG] LLM fallback → using rule intent followup
Agent: I've logged your symptom (shortness of breath). Since it occurred more than twice this week, I'll notify your provider.

You: I forgot to take my Lasix this morning.
[DEBUG] LLM intent → medication, patient_id → 10004235
Agent: Furosemide: Take as soon as you remember unless the next dose is near.

You: Give me this week's caregiver update for 10004235.
[DEBUG] LLM intent → caregiver, patient_id → 10004235
Agent: Caregiver Update for Alice Lee (Mother: Wong Parent)
- Alice Lee reported dizziness 2× (avg severity 6.5), breathlessness 1× (avg severity 7.0), shortness of breath 1× (avg severity 7.0).
- Risk level this week: MODERATE.
```

## 📄 Logging Output

Every routed event is saved to:
```
orchestration_agent/demos/logs/orchestration_log.jsonl
```

Example log record:
```json
{
  "ts": "2025-10-16T21:40:12Z",
  "agent": "OrchestrationAgent",
  "input": "I feel dizzy 7 out of 10 and shortness of breath.",
  "intent": "followup",
  "patient_id": "10004235",
  "routed_reply": "I've logged your symptom (shortness of breath). Since it occurred more than twice this week, I'll notify your provider."
}
```

## 🔧 Commands

| Command | Description |
|---------|-------------|
| `:voice on / off` | Toggle text-to-speech |
| `pid <8digit>` | Set a default patient ID context |
| `:stt <file>` | Convert an audio file to text and route it |
| `:mic on` | Speak a single sentence (if microphone is available) |
| `quit` | Exit the program |

## 🧠 Summary
```
👉 Listen → Detect Intent → Route to Agent → Log Response → Speak (optional)
```

This Orchestration Agent is the central intelligence layer that coordinates all voice modules. It ensures modular scalability — meaning each agent (appointment, follow-up, medication, caregiver) can evolve independently while still connecting to this unified orchestration layer.

## 🔑 Notes

- Requires `OPENAI_API_KEY` for LLM-based routing
- Fallback rules ensure the system remains functional offline
- All logs are timestamped in ISO-8601 UTC format
- Dependencies: `openai`, `speechrecognition`, `pyttsx3` (optional)
```bash
export OPENAI_API_KEY=sk-xxxx     # Mac/Linux
setx OPENAI_API_KEY "sk-xxxx"     # Windows
```

✅ **System Ready:** Once this Orchestration Agent runs successfully, you have a fully integrated multi-agent voice triage system connecting all Zyter components.