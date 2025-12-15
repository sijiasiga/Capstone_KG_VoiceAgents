# Getting Started - Voice Agents Documentation

Welcome to the Voice Agents project documentation! This guide will help you navigate the system.

---

## 📖 Documentation Navigation

### For Quick Overview
**Start here if you're new or want a high-level understanding:**

1. **[System Overview](../README.md)** - Main project README with features and quick start
2. **[Evaluation Report](./EVALUATION_REPORT.md)** - Performance metrics and test results
3. **[Triage Logic Summary](./Voice_Agent_Triage_Logic_Summary.md)** - How the clinical triage system works

### For Technical Deep Dive
**Read these for implementation details:**

4. **[Voice Agent Report](./VOICE_AGENT_REPORT.md)** - Complete technical architecture and design decisions
5. **[Changelog](./CHANGELOG.md)** - Implementation updates and improvements

---

## 🚀 Quick Start Path

**For Evaluators/Reviewers:**
```
1. Read: README.md (5 min)
2. Review: EVALUATION_REPORT.md (10 min)
3. Test: Run the system following Quick Start guide
```

**For Developers:**
```
1. Read: README.md + VOICE_AGENT_REPORT.md (20 min)
2. Explore: VoiceAgents_langgraph/nodes/ (agent implementations)
3. Test: Run evaluation/evaluate_langgraph.py
4. Review: CHANGELOG.md for recent changes
```

**For Clinical Reviewers:**
```
1. Read: Voice_Agent_Triage_Logic_Summary.md (15 min)
2. Review: EVALUATION_REPORT.md (validation results)
3. Test: Try the system with test cases from validation_datasets/
```

---

## 🎯 Key Files by Purpose

### Understanding the System
- `../README.md` - What it does, how to run it
- `EVALUATION_REPORT.md` - How well it works
- `Voice_Agent_Triage_Logic_Summary.md` - Clinical decision logic

### Technical Implementation
- `VOICE_AGENT_REPORT.md` - Architecture and design
- `../VoiceAgents_langgraph/nodes/` - Agent code
- `../VoiceAgents_langgraph/workflow.py` - System orchestration

### Testing and Validation
- `../VoiceAgents_langgraph/evaluation/` - Test scripts
- `../VoiceAgents_langgraph/validation_datasets/` - Test cases
- `EVALUATION_REPORT.md` - Results summary

---

## 💡 Common Questions

**Q: Where do I start if I want to run the system?**
A: Follow the Quick Start guide in `../README.md` - it takes 5 minutes.

**Q: How accurate is the triage system?**
A: 96.8% for emergency detection, 98.4% for intent classification. See `EVALUATION_REPORT.md` for details.

**Q: Can I test specific scenarios?**
A: Yes! Use the validation datasets in `../VoiceAgents_langgraph/validation_datasets/`

**Q: What models does it support?**
A: OpenAI, Anthropic, and Google models with automatic fallback. Configured in `.env` file.

**Q: Is it production-ready?**
A: The system is fully functional and validated. See `VOICE_AGENT_REPORT.md` for deployment considerations.

---

## 📧 Need Help?

- Check the documentation files listed above
- Review code comments in `VoiceAgents_langgraph/nodes/`
- Run tests with `pytest tests/test_agents.py -v`
