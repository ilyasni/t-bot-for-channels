# Sub-workflows Architecture - Import & Setup Guide

**Version:** 1.0  
**Date:** 13 October 2025  
**Architecture:** Modular Sub-workflows following n8n best practices

---

## Overview

This guide explains how to import and configure the new Sub-workflows architecture for Group Digest generation.

### Architecture

```
Main Workflow: group_digest_orchestrator.json
    ↓
Webhook → Prepare Data → [Call 3 Agents in Parallel] → Aggregate → Response

Sub-workflows (3):
    - agent_topic_extractor.json
    - agent_speaker_analyzer.json
    - agent_summarizer.json
```

**Benefits:**
- Modular and reusable agents
- Easy to test individually
- Clean data flow (no data loss)
- Follows n8n best practices
- Scalable architecture

---

## Step-by-Step Import Instructions

### Step 1: Import Sub-workflows

**Order matters!** Import sub-workflows first, then the orchestrator.

1. **Open n8n UI:** `https://n8n.produman.studio`

2. **Import Agent: Topic Extractor**
   - Workflows → **Import from File**
   - Select: `n8n/workflows/agent_topic_extractor.json`
   - Click **Import**
   - **Activate** the workflow (toggle ON)
   - **Copy Workflow ID** (from URL or workflow settings)

3. **Import Agent: Speaker Analyzer**
   - Workflows → **Import from File**
   - Select: `n8n/workflows/agent_speaker_analyzer.json`
   - Click **Import**
   - **Activate** the workflow (toggle ON)
   - **Copy Workflow ID**

4. **Import Agent: Context Summarizer**
   - Workflows → **Import from File**
   - Select: `n8n/workflows/agent_summarizer.json`
   - Click **Import**
   - **Activate** the workflow (toggle ON)
   - **Copy Workflow ID**

---

### Step 2: Import and Configure Orchestrator

1. **Import Orchestrator**
   - Workflows → **Import from File**
   - Select: `n8n/workflows/group_digest_orchestrator.json`
   - Click **Import**

2. **Configure Execute Workflow Nodes**

   The orchestrator has 3 "Execute Workflow" nodes that need to be configured with the actual workflow IDs:

   **a) Execute: Topic Extractor**
   - Open the node
   - In "Workflow" field, select **"Agent: Topic Extractor"** from dropdown
   - Save

   **b) Execute: Speaker Analyzer**
   - Open the node
   - In "Workflow" field, select **"Agent: Speaker Analyzer"** from dropdown
   - Save

   **c) Execute: Summarizer**
   - Open the node
   - In "Workflow" field, select **"Agent: Context Summarizer"** from dropdown
   - Save

3. **Activate Orchestrator**
   - Toggle **Active → ON** (green)
   - Click **Save**

---

### Step 3: Deactivate Old Workflow

1. **Find old workflow:**
   - Workflows → "Group Dialogue Multi-Agent Analyzer v2"

2. **Deactivate:**
   - Toggle **Active → OFF**
   - This prevents conflicts with the new orchestrator (both use `/webhook/group-digest`)

3. **Don't delete yet** - keep for potential rollback until testing confirms new version works

---

### Step 4: Test the New Architecture

**In Telegram Bot:**

```
/debug_group_digest 6
```

**Expected Result:**

```json
{
  "topics": ["тема1", "тема2", ...],
  "speakers_summary": {
    "username1": "описание",
    "username2": "описание"
  },
  "overall_summary": "Краткое резюме диалога...",
  "message_count": 6,
  "period": "6 hours"
}
```

**Verify:**
- ✅ `message_count` shows real count (e.g., 6)
- ✅ `period` matches requested hours (e.g., "6 hours")
- ✅ Topics extracted (array with 3-5 items)
- ✅ Speakers analyzed (object with usernames)
- ✅ Summary generated (string, 2-3 sentences)

**Also test regular command:**

```
/group_digest 6
```

Should show formatted digest in Telegram.

---

### Step 5: Monitor n8n Execution Logs

1. **Open n8n:** `https://n8n.produman.studio`

2. **Go to Executions** (left menu)

3. **Check recent executions:**
   - Should see 4 executions for each digest request:
     - 1x "Group Digest Orchestrator"
     - 1x "Agent: Topic Extractor"
     - 1x "Agent: Speaker Analyzer"
     - 1x "Agent: Context Summarizer"

4. **Verify each execution:**
   - All should be **green** (success)
   - Check execution time (total ~15-20 seconds)
   - Open "Aggregate Results" node to see merged data

---

### Step 6: Delete Old Workflow (After Success)

**Only after confirming new architecture works!**

1. Workflows → "Group Dialogue Multi-Agent Analyzer v2"
2. Click **Delete**
3. Confirm deletion

---

## Troubleshooting

### Issue: "Workflow not found" error

**Cause:** Execute Workflow nodes not configured with workflow IDs

**Solution:**
1. Open orchestrator workflow
2. Open each "Execute: ..." node
3. Select the agent workflow from dropdown
4. Save

---

### Issue: Empty results from agents

**Cause:** Agent workflows not activated

**Solution:**
1. Go to Workflows
2. Check that all 3 agent workflows show **Active (green)**
3. Activate any that are OFF

---

### Issue: message_count still 0

**Cause:** Old v2 workflow still active (conflict)

**Solution:**
1. Deactivate v2 workflow
2. Make sure orchestrator is active
3. Test again

---

### Issue: Webhook timeout

**Cause:** One of the agents is slow or failing

**Solution:**
1. Check Executions log
2. Find which agent failed
3. Open that agent's execution
4. Check GigaChat response for errors
5. Verify gpt2giga-proxy is running: `docker ps | grep gpt2giga`

---

## Architecture Details

### Data Flow

```
1. Python bot calls: POST /webhook/group-digest
   Body: {messages: [...], user_id, group_id, hours}

2. Orchestrator: Prepare Data
   → Formats messages, saves message_count, hours

3. Orchestrator: Execute 3 agents in PARALLEL
   Agent 1: Extract topics → {topics: [...]}
   Agent 2: Analyze speakers → {speakers: {...}}
   Agent 3: Summarize → {summary: "..."}

4. Orchestrator: Aggregate Results
   → Merges all agent results
   → Preserves message_count, hours from Prepare Data
   → Returns: {topics, speakers_summary, overall_summary, message_count, period}

5. Python bot: Formats for Telegram
   → Displays in user chat
```

### Key Improvements vs v2

| Aspect | v2 (Monolithic) | New (Sub-workflows) |
|--------|-----------------|---------------------|
| **Structure** | 1 workflow | 4 workflows |
| **Agents** | HTTP nodes | Execute Workflow nodes |
| **Reusability** | None | High |
| **Testing** | Hard | Easy (test each agent) |
| **Data loss** | Possible | Fixed (clean passing) |
| **Debugging** | Complex | Simple (4 execution logs) |
| **Scalability** | Low | High |
| **Best practices** | ❌ | ✅ |

---

## Testing Individual Agents

You can test each agent independently:

### Test Topic Extractor

1. Open "Agent: Topic Extractor" workflow
2. Click **Execute Workflow** (top right)
3. In the test panel, provide input:
   ```json
   {
     "messages_text": "[1] alice: Hello\n[2] bob: How are you?",
     "hours": 6
   }
   ```
4. Click **Execute**
5. Check "Parse Topics" node output: should have `{topics: [...]}`

### Test Speaker Analyzer

Similar process, provide:
```json
{
  "messages_text": "[1] alice: Hello\n[2] bob: How are you?"
}
```

### Test Summarizer

Similar process, provide:
```json
{
  "messages_text": "[1] alice: Hello\n[2] bob: How are you?",
  "hours": 6
}
```

---

## Rollback to v2 (If Needed)

If new architecture has issues:

1. **Deactivate Orchestrator:**
   - "Group Digest Orchestrator" → Active OFF

2. **Reactivate v2:**
   - "Group Dialogue Multi-Agent Analyzer v2" → Active ON

3. **Test:**
   - `/group_digest 6` should work again

4. **Report issue** and investigate

---

## Next Steps

After successful migration:

1. ✅ Test with different groups
2. ✅ Test with different time periods (1h, 6h, 24h)
3. ✅ Monitor execution times
4. ✅ Delete v2 workflow
5. ✅ Consider adding more agents (sentiment analysis, key quotes, etc.)

---

## Files Reference

- `agent_topic_extractor.json` - Sub-workflow for topic extraction
- `agent_speaker_analyzer.json` - Sub-workflow for speaker analysis
- `agent_summarizer.json` - Sub-workflow for context summarization
- `group_digest_orchestrator.json` - Main orchestrator workflow
- `SUB_WORKFLOWS_GUIDE.md` - This file

---

**Import order:** Sub-workflows first → Orchestrator → Configure → Activate → Test

**Questions?** Check Executions log in n8n for detailed debugging.

