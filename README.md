# Healthcare Voice Agent System
## CMU x Zyter Capstone Project

An AI-powered voice triage system for healthcare organizations that provides 24/7 patient support through intelligent conversation agents.

---

## 🎯 Project Overview

This repository contains two complementary healthcare AI systems:

### 🎤 **Voice Agents** (Primary Focus)
**AI-powered voice triage and patient support system**

- 24/7 appointment management and scheduling
- Intelligent symptom triage (RED/ORANGE/GREEN classification)
- Medication education and safety monitoring
- Caregiver support with automated summaries
- Natural language understanding for healthcare conversations

**→ [Explore Voice Agents System](./VoiceAgents/README.md)**

### 🔗 Knowledge Graph
Policy-based medical coverage and prior authorization system

**→ [View Knowledge Graph](./KG/README.md)**

---

## ⚡ Key Performance Metrics (Voice Agents)

| Metric | Result | Impact |
|--------|--------|--------|
| **Response Time** | <2 seconds | Instant patient support vs hours of waiting |
| **Emergency Detection** | 96.8% (30/31) | Identifies life-threatening symptoms requiring ER |
| **Intent Accuracy** | 98.4% (120/122) | Correctly routes patients to appropriate care |
| **Policy Compliance** | 100% | Perfect enforcement of clinical protocols |

---

## 🚀 Quick Start (Voice Agents)

```bash
# Navigate to the main system
cd VoiceAgents/VoiceAgents_langgraph

# Set up environment
cp .env.example .env
# Add your API keys to .env

# Install dependencies
pip install -r requirements.txt

# Run the system
python main.py
```

---

## 📂 Repository Structure

```
Capstone_KG_VoiceAgents/
├── VoiceAgents/              # Voice triage system (main project)
│   ├── VoiceAgents_langgraph/    # Production implementation
│   │   ├── main.py               # Entry point
│   │   ├── nodes/                # Agent implementations
│   │   ├── data/                 # Patient data and knowledge base
│   │   ├── evaluation/           # Test datasets and results
│   │   └── docs/                 # System documentation
│   └── DOCUMENTATION/            # Project reports and analysis
│
└── KG/                       # Knowledge Graph system
    └── README.md
```

---

## 📚 Documentation

### Voice Agents Documentation
- **[📖 START HERE](./VoiceAgents/DOCUMENTATION/START_HERE.md)** - Documentation navigation guide
- **[System Overview](./VoiceAgents/README.md)** - Complete feature documentation
- **[Evaluation Report](./VoiceAgents/DOCUMENTATION/EVALUATION_REPORT.md)** - Performance analysis and validation
- **[System Architecture](./VoiceAgents/DOCUMENTATION/VOICE_AGENT_REPORT.md)** - Technical deep dive
- **[Triage Logic](./VoiceAgents/DOCUMENTATION/Voice_Agent_Triage_Logic_Summary.md)** - Clinical decision system

---

## 🎓 Project Team

**Carnegie Mellon University x Zyter Health**
Capstone Project - Healthcare AI Systems

---

## 📧 Contact

For questions or more information, please refer to the documentation or contact the project team.
