# 🚀 Quick Start: Sub-workflows Architecture

**Status:** ✅ Ready to import  
**Time needed:** 20 minutes  
**Complexity:** Easy (follow guide)

---

## ⚡ What You Got

**4 new n8n workflow files:**
1. `agent_topic_extractor.json` - Extracts topics
2. `agent_speaker_analyzer.json` - Analyzes speakers
3. `agent_summarizer.json` - Creates summary
4. `group_digest_orchestrator.json` - Main orchestrator

**2 documentation files:**
1. `SUB_WORKFLOWS_GUIDE.md` - Detailed import guide
2. `SUB_WORKFLOWS_IMPLEMENTATION.md` - Technical details

---

## 📋 Quick Import Steps

### 1. Open n8n UI
```
https://n8n.produman.studio
```

### 2. Import in Order

**A) Sub-workflows first (3 files):**
```
Workflows → Import → agent_topic_extractor.json → Activate
Workflows → Import → agent_speaker_analyzer.json → Activate
Workflows → Import → agent_summarizer.json → Activate
```

**B) Then orchestrator:**
```
Workflows → Import → group_digest_orchestrator.json
```

### 3. Configure Orchestrator

Open "Group Digest Orchestrator", configure 3 nodes:

- **"Execute: Topic Extractor"** → Select "Agent: Topic Extractor"
- **"Execute: Speaker Analyzer"** → Select "Agent: Speaker Analyzer"
- **"Execute: Summarizer"** → Select "Agent: Context Summarizer"

Save and **Activate**.

### 4. Deactivate Old v2

```
Workflows → "Group Dialogue Multi-Agent Analyzer v2" → Active OFF
```

### 5. Test

**In Telegram:**
```
/debug_group_digest 6
```

**Should show:**
- ✅ `message_count: 6` (not 0)
- ✅ `period: "6 hours"` (not "24 hours")
- ✅ Topics, speakers, summary

---

## 🎯 Architecture Benefits

| Feature | Old (v2) | New (Sub-workflows) |
|---------|----------|---------------------|
| Workflows | 1 monolithic | 4 modular |
| Testing | Hard | Easy |
| Debugging | 1 log | 4 logs |
| Data loss | Yes (hours, count) | No ✅ |
| Best practices | ❌ | ✅ |
| Speed | ~20s sequential | ~15s parallel |

---

## 📚 Detailed Guides

**Full instructions:**
- `n8n/workflows/SUB_WORKFLOWS_GUIDE.md`

**Technical details:**
- `SUB_WORKFLOWS_IMPLEMENTATION.md`

---

## 🆘 Troubleshooting

**"Workflow not found":**
→ Configure Execute Workflow nodes (step 3)

**Empty results:**
→ Activate all 3 agent workflows

**Still shows v2 results:**
→ Deactivate v2 workflow (step 4)

**Need help?**
→ See `SUB_WORKFLOWS_GUIDE.md` Troubleshooting section

---

## 🔄 Rollback (if needed)

```
1. Deactivate: "Group Digest Orchestrator"
2. Activate: "Group Dialogue Multi-Agent Analyzer v2"
3. Test
```

---

**Start here:** `n8n/workflows/SUB_WORKFLOWS_GUIDE.md`

**Time:** 20 minutes to import and test ⏱️

