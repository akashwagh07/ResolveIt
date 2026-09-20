# Agent 2: Deterministic Decision & Command Generation

`Agent 2` (`backend/app/agents/agent2.py`) is a deterministic policy agent responsible for synthesizing Agent 1's civic classification with citizen inputs and deterministic rule engines.

**Design Invariant:** Agent 2 makes **zero LLM calls**. Every decision follows a strict, deterministic sequence of criteria. Agent 2 never writes directly to the database; it generates a validated `CreateComplaintCommand` executed through the backend command gate.

---

## 1. Input Contract (`Agent2Input`)

```python
class Agent2Input(BaseModel):
    agent1: Optional[Agent1Result] = None
    citizen_name: str
    citizen_contact: str
    raw_text: str
    language: Optional[str] = None
    latitude: float
    longitude: float
    address_text: Optional[str] = None
    evidence: list[dict[str, Any]] = Field(default_factory=list)
    ai_unavailable: bool = False
```

---

## 2. Decision Hierarchy (Outcome Logic)

Agent 2 evaluates outcomes in a strict sequence:

```
[Agent2Input]
     │
     ├── 1. ai_unavailable is True?
     │      └─► OUTCOME: HUMAN_REVIEW
     │          (category=OTHER, issue=OTHER, confidence=0.0, reason="AI unavailable")
     │
     ├── 2. civic_relevance == "LOW"?
     │      └─► OUTCOME: OUT_OF_SCOPE
     │          (score=0, level=LOW, priority=NORMAL, relevance_reason in trace)
     │
     ├── 3. category == "OTHER" (with civic_relevance MEDIUM or HIGH)?
     │      └─► OUTCOME: HUMAN_REVIEW
     │          (reason="Category 'OTHER' requires manual review")
     │
     ├── 4. confidence < 0.60?
     │      └─► OUTCOME: HUMAN_REVIEW
     │          (reason="Low model confidence (< 0.60)")
     │
     └── 5. Otherwise:
            └─► OUTCOME: CLASSIFIED
                (If confidence is between 0.60 and 0.84, needs_review=True is set by command executor)
```

---

## 3. Output Contract (`Agent2Decision`)

```python
class Agent2Decision(BaseModel):
    command: CreateComplaintCommand
    outcome: str               # "CLASSIFIED" | "HUMAN_REVIEW" | "OUT_OF_SCOPE"
    severity: SeverityResult
    priority: PriorityResult
    department_code: str
    needs_review: bool
    review_reasons: list[str]
    trace: list[str]
```

---

## 4. Synthesized Fields & Enriched Reasoning

### Location & Address Fallback
- `address_text`: Uses the citizen's submitted `address_text` if provided; falls back to Agent 1's extracted `location.address_text` or `None`.
- `latitude` / `longitude`: Coordinates submitted by the citizen are authoritative.

### Summary Fallback
- `structured_summary`: Uses Agent 1's generated `description`. If unavailable or empty, falls back to the first 200 characters of the citizen's `raw_text`.

### `ai_reasoning` Dictionary Structure
To provide complete transparency and auditability, `CreateComplaintCommand.ai_reasoning` embeds:
- `category`: Category string
- `issue`: Issue string
- `confidence`: Confidence float (0.0 to 1.0)
- `confidence_reason`: Plain text explanation from Agent 1
- `alternatives`: Secondary classifications suggested by Agent 1
- `observations`: Sensory observations extracted by Agent 1
- `warnings`: Cautionary flags from Agent 1
- `model_used`: LLM model name that generated classification
- `cached`: Boolean whether Agent 1 result came from disk cache
- `transcript`: Audio transcript if an audio note was processed
- `translation_en`: English translation if raw input was non-English
- `trace`: The sequential list of readable sentences explaining each step of Agent 2's decision
- `thresholds`: Applied confidence thresholds (`{"human_review": 0.60, "auto_route": 0.85}`)
