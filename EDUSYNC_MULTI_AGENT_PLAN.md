# EduSync Multi-Agent Architecture Plan

## Current Implementation vs. Vision Mapping

### ✅ What's Already Built

| Component | Current State | Status |
|-----------|---------------|--------|
| **Backend API** | FastAPI on Railway | ✅ Working |
| **Database** | SQLite (PostgreSQL SSL issues) | ⚠️ Fallback mode |
| **Telegram Bot** | Webhook endpoint, role-based handlers | ✅ Basic structure |
| **OCR Engine** | Tesseract + EasyOCR + Vision LLMs | ✅ Advanced |
| **AI Processor** | Gemini, OpenAI integration | ✅ Configured |
| **Web UI** | Static landing page | ⚠️ Basic |
| **Reminders** | Database models exist | ⚠️ Not fully wired |

### 🎯 Target Vision

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         EDUSYNC MULTI-AGENT SYSTEM                          │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐                  │
│  │   TEACHER    │    │    PARENT    │    │     WEB      │                  │
│  │   (Telegram) │    │   (Telegram) │    │    (Browser) │                  │
│  └──────┬───────┘    └──────┬───────┘    └──────┬───────┘                  │
│         │                   │                   │                           │
│         └───────────────────┼───────────────────┘                           │
│                             ▼                                               │
│              ┌──────────────────────────────┐                              │
│              │      ORCHESTRATOR AGENT      │                              │
│              │   (Request Routing & State)   │                              │
│              └──────────────┬───────────────┘                              │
│                             │                                               │
│         ┌───────────────────┼───────────────────┐                          │
│         ▼                   ▼                   ▼                          │
│  ┌─────────────┐   ┌─────────────┐   ┌─────────────┐                      │
│  │  OCR AGENT  │   │   AI AGENT  │   │ REMINDER    │                      │
│  │ (Image →    │   │ (Extract &  │   │  AGENT      │                      │
│  │  Text)      │   │  Structure) │   │ (Scheduling)│                      │
│  └─────────────┘   └─────────────┘   └─────────────┘                      │
│         │                   │                   │                          │
│         └───────────────────┼───────────────────┘                          │
│                             ▼                                               │
│              ┌──────────────────────────────┐                              │
│              │      DATABASE (SQLite/PG)    │                              │
│              └──────────────────────────────┘                              │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Multi-Agent Swarm Design

### Agent 1: UI/UX Design Agent
**Role:** Design and validate interactive web interface

**Responsibilities:**
- Teacher dashboard (upload homework, view classes, track completion)
- Parent dashboard (view children's homework, mark complete, get reminders)
- Mobile-responsive design
- Real-time updates via WebSocket/SSE

**Context Isolation:**
- Input: User personas (teacher/parent), feature requirements
- Output: HTML/CSS/JS code, responsive layouts

**Implementation:**
```python
# Spawn UI agent for each dashboard
ui_tasks = [
    Task(description="Design Teacher Dashboard", subagent_name="frontend"),
    Task(description="Design Parent Dashboard", subagent_name="frontend"),
    Task(description="Design Mobile Responsive", subagent_name="frontend")
]
dashboards = await asyncio.gather(*ui_tasks)
```

---

### Agent 2: API Testing Agent
**Role:** Ensure all API endpoints work correctly

**Responsibilities:**
- Test homework CRUD operations
- Test Telegram webhook integration
- Test reminder scheduling
- Test OCR → AI → Database pipeline

**Test Coverage:**
| Endpoint | Method | Test Case |
|----------|--------|-----------|
| `/api/v1/homework` | POST | Teacher uploads homework |
| `/api/v1/homework` | GET | Parent views homework |
| `/api/v1/homework/{id}/complete` | PATCH | Parent marks complete |
| `/webhook/telegram` | POST | Bot receives message |
| `/api/reminders` | GET | List pending reminders |

---

### Agent 3: Natural Language Bot Agent
**Role:** Process natural language from parents/teachers

**Example Flows:**

**Teacher Upload:**
```
Teacher: "Post math homework for Class 5A, due Friday. Page 45 exercises 1-10"
↓
NL Agent extracts:
- Subject: Mathematics
- Class: 5A
- Due: Friday
- Content: Page 45, exercises 1-10
↓
Create homework record
Notify all parents in Class 5A
```

**Parent Query:**
```
Parent: "What homework does Ahmad have this week?"
↓
NL Agent extracts:
- Child: Ahmad
- Timeframe: This week
↓
Query database for Ahmad's homework
Format response with due dates
```

**Implementation:**
- Use Gemini for intent classification
- Extract entities (subject, date, child_name)
- Map to API calls

---

### Agent 4: OCR + AI Processing Agent
**Role:** Extract homework from photos

**Pipeline:**
```
Photo Upload
    ↓
┌─────────────────────────────────────────┐
│  ENSEMBLE OCR (Parallel Execution)      │
│  ┌─────────────┐ ┌─────────────┐       │
│  │  Tesseract  │ │  EasyOCR    │       │
│  └──────┬──────┘ └──────┬──────┘       │
│         └───────────────┘               │
│                   ↓                     │
│         ┌─────────────┐                 │
│         │ Vision LLM  │ (Gemini)        │
│         │  (Fallback) │                 │
│         └──────┬──────┘                 │
└────────────────┼────────────────────────┘
                 ↓
        ┌─────────────────┐
        │   AI PROCESSOR  │
        │  (Gemini/GPT)   │
        └────────┬────────┘
                 ↓
    Extracted Homework:
    - Subject: Science
    - Title: "Plant Biology Worksheet"
    - Due: 2024-02-20
    - Description: "Label flower parts"
```

---

### Agent 5: Reminder Scheduler Agent
**Role:** Send timely reminders to parents

**Scheduling Rules:**
| Trigger | Action | Timing |
|---------|--------|--------|
| New homework posted | Notify parents | Immediate |
| Due date approaching | Send reminder | 1 day before |
| Due date same day | Urgent reminder | Morning of |
| Homework overdue | Escalation | Daily until done |

**Multi-Agent Reminder Flow:**
```python
# Check reminders every hour
async def check_reminders():
    pending = await get_pending_reminders()
    
    # Spawn agent for each reminder type
    tasks = [
        Task(description=f"Send reminder: {r.type} for {r.parent}", 
             subagent_name="messenger")
        for r in pending
    ]
    await asyncio.gather(*tasks)
```

---

## Implementation Roadmap

### Phase 1: Fix Core Infrastructure (Week 1)
- [ ] Fix PostgreSQL SSL or migrate to SQLite
- [ ] Ensure Telegram bot webhook processing works
- [ ] Verify OCR → AI pipeline
- [ ] Test Gemini API integration

### Phase 2: Interactive Web UI (Week 2)
- [ ] Teacher Dashboard
  - Upload homework with file/photo
  - View class list
  - Track completion rates
- [ ] Parent Dashboard
  - View children's homework
  - Mark as complete
  - Set reminder preferences

### Phase 3: Natural Language Bot (Week 3)
- [ ] Intent classification (Gemini)
- [ ] Entity extraction (dates, names, subjects)
- [ ] Context-aware conversations
- [ ] Multi-language support (EN, BM, 中文)

### Phase 4: Reminder System (Week 4)
- [ ] Background scheduler (APScheduler/Celery)
- [ ] Reminder templates
- [ ] WhatsApp integration (fallback)

---

## Multi-Agent Coordination

### Orchestrator Pattern

```python
class EduSyncOrchestrator:
    """Main orchestrator for all agents."""
    
    async def handle_teacher_upload(self, photo, teacher_id):
        """Teacher uploads homework photo."""
        
        # Parallel OCR processing
        ocr_results = await asyncio.gather(
            Task(description="Extract with Tesseract", subagent_name="ocr"),
            Task(description="Extract with EasyOCR", subagent_name="ocr"),
            Task(description="Extract with Gemini Vision", subagent_name="ocr"),
        )
        
        # AI Processing Agent
        extracted = await Task(
            description=f"Structure homework from: {ocr_results}",
            subagent_name="ai_processor"
        )
        
        # Database Agent
        homework_id = await Task(
            description=f"Save homework: {extracted}",
            subagent_name="database"
        )
        
        # Reminder Agent
        await Task(
            description=f"Schedule reminders for homework {homework_id}",
            subagent_name="reminder"
        )
        
        # Notification Agent
        await Task(
            description=f"Notify parents in class {extracted['class_id']}",
            subagent_name="notifier"
        )
        
        return {"status": "success", "homework_id": homework_id}
```

---

## Testing Strategy

### Parallel Test Execution
```python
async def run_all_tests():
    """Run all test agents in parallel."""
    
    test_tasks = [
        Task(description="Test Teacher Flow", subagent_name="tester"),
        Task(description="Test Parent Flow", subagent_name="tester"),
        Task(description="Test OCR Accuracy", subagent_name="tester"),
        Task(description="Test Reminder System", subagent_name="tester"),
        Task(description="Test Natural Language", subagent_name="tester"),
        Task(description="Test UI Responsiveness", subagent_name="tester"),
    ]
    
    results = await asyncio.gather(*test_tasks)
    return aggregate_test_results(results)
```

---

## Current Gaps & Action Items

| Gap | Priority | Action |
|-----|----------|--------|
| PostgreSQL SSL | 🔴 High | Fix or use SQLite |
| Bot not processing | 🔴 High | Debug webhook handler |
| Web UI static only | 🟡 Medium | Build interactive dashboards |
| NL bot basic | 🟡 Medium | Add intent classification |
| Reminders not wired | 🟡 Medium | Connect scheduler |
| No parent tracking | 🟢 Low | Add parent dashboard |

---

## Next Steps

1. **Fix Database Connection** - Get PostgreSQL working or fully commit to SQLite
2. **Fix Bot Webhook** - Ensure Telegram updates are processed
3. **Build Teacher Dashboard** - Interactive homework upload
4. **Build Parent Dashboard** - Track and complete homework
5. **Add NL Processing** - Natural language commands

**Which would you like to tackle first?**
