# Agent 1: Civic Intake & Classification

Agent 1 is ResolveIt's multimodal civic intake and classification agent. It ingests raw citizen complaints in text, audio, image, and video formats, translates and transcribes vernacular inputs, and classifies complaints against ResolveIt's canonical civic ontology.

In accordance with ResolveIt's architectural rules:
- **Agent 1 never writes to the database directly.**
- **Agent 1 never emits commands or makes state changes.**
- **Agent 1 does NOT decide severity, department assignment, or SLA timing** (those are deterministic downstream engines).
- **Agent 1 outputs a Pydantic-validated result object** with confidence scores, reasons, and location references.

---

## 1. Schemas

### Input: `Agent1Input`
Validated with `model_validator` to ensure at least text or one media file is supplied:
- `text` (*Optional[str]*): Raw citizen text complaint.
- `language_hint` (*Optional[str]*): Suggested language code (e.g. `en`, `hi`, `mr`).
- `latitude` (*Optional[float]*): GPS latitude from client device.
- `longitude` (*Optional[float]*): GPS longitude from client device.
- `address_text` (*Optional[str]*): User-entered address or landmark.
- `media_paths` (*List[str]*): List of file paths to uploaded media (images, audio, or video).

### LLM-Facing Output: `Agent1Output`
Strict schema with no free-form dicts:
- `civic_relevance` (*Literal["LOW", "MEDIUM", "HIGH"]*) & `relevance_reason` (*str*)
- `category` (*str*) & `issue` (*str*): Codes strictly drawn from `backend/app/ontology.py`.
- `description` (*str*): Objective 1–2 sentence neutral summary.
- `duration_text` (*Optional[str]*) & `duration_days` (*Optional[float]*): Only extracted when explicitly stated.
- `size_hint` (*Literal["SMALL", "MEDIUM", "LARGE", "UNKNOWN"]*)
- `context_tags` (*List[str]*): Allowed tags: `SCHOOL_NEARBY`, `HOSPITAL_NEARBY`, `MAJOR_ROAD`, `TRANSIT_AREA`, `HIGH_PEDESTRIAN`, `SAFETY_HAZARD`, `HEALTH_HAZARD`, `TRAFFIC_IMPACT`.
- `language` (*str*), `transcript` (*Optional[str]*), `translation_en` (*Optional[str]*).
- `location_mentions` (*List[str]*): Place names explicitly mentioned in text or audio.
- `image_matches_text` (*Optional[bool]*): Whether visual evidence aligns with text claims.
- `observations` (*List[ObservationItem]*): List of `{fact: str, source: TEXT | IMAGE | AUDIO | VIDEO}`.
- `missing_info` (*List[str]*): Information gaps identified.
- `alternatives` (*List[AlternativeItem]*): Up to 2 `{category: str, issue: str, confidence: float}`.
- `confidence` (*float*): Calibrated score in range `[0.0, 1.0]`.
- `confidence_reason` (*str*): Explanation for the confidence rating.

### Caller Result: `Agent1Result`
- `output` (*Agent1Output*): Deterministically post-processed classification payload.
- `location` (*LocationResult*): `{latitude, longitude, address_text, source: GPS | TEXT | NONE}`.
- `evidence_flags` (*EvidenceFlags*): `{text: bool, image: bool, audio: bool, video: bool}`.
- `model_used` (*str*): Name of the LLM model that generated the classification.
- `cached` (*bool*): True if result was returned directly from disk cache.
- `latency_ms` (*float*): Wall-clock roundtrip duration in milliseconds.
- `warnings` (*List[str]*): List of deterministic fallback notes and validation warnings.

---

## 2. Prompt Rules & Security

1. **Untrusted Data Isolation**:
   Citizen text, audio transcripts, and OCR text in images are treated as untrusted data. The user prompt wraps complaint text inside `<complaint>` and `</complaint>` tags with strict system instructions prohibiting prompt injection or execution of user instructions.
2. **Canonical Ontology Ingestion**:
   The system prompt dynamically builds the category and issue list at import time directly from `backend/app/ontology.py`. If a complaint does not match any category, `OTHER` / `OTHER` must be selected.
3. **Multimodal Discrepancies**:
   If text and visual evidence disagree, visible evidence takes precedence for classification. The agent sets `image_matches_text = false` and notes the discrepancy.
4. **Duration & Location Guardrails**:
   Duration is only extracted if explicitly stated (e.g. "for 3 days"). Coordinates and addresses are never invented; only explicitly mentioned places are extracted into `location_mentions`.
5. **Vernacular Audio**:
   For Hindi and Marathi audio, original audio is transcribed into `transcript` and translated to English in `translation_en`.
6. **Confidence Calibration**:
   - `0.90 - 1.00`: Unambiguous complaint with clear and consistent evidence.
   - `0.60 - 0.84`: Plausible complaint with ambiguous or single weak signal.
   - `< 0.60`: Unclear, conflicting, or non-civic content.

---

## 3. Deterministic Post-Processing

The raw LLM output is never trusted blindly:
1. **Alias Normalization**: Known aliases (e.g. `ANIMAL_CARCASS` -> `WASTE` / `DEAD_ANIMAL`) are mapped to canonical ontology codes.
2. **Ontology Validation**: If category and issue are not recognized in `CATEGORIES`, category and issue are set to `OTHER` / `OTHER`, confidence is capped at `0.5`, and a warning is logged.
3. **Confidence Clamping**: Confidence is clamped between `0.0` and `1.0`.
4. **Multimodal Disagreement Cap**: If `image_matches_text` is `False`, confidence is capped at `0.7` and a warning is added.
5. **Alternatives Limit**: At most 2 valid alternative classifications are retained.
6. **Location Resolution**:
   - Client device GPS coordinates always win (`source="GPS"`).
   - If no GPS is present, `address_text` or the first `location_mention` is used (`source="TEXT"`).
   - Coordinates generated by the LLM are **never** used.
7. **Real Evidence Flags**: `evidence_flags` (`text`, `image`, `audio`, `video`) are computed exclusively from actual uploaded files and non-empty text, never from LLM output.

---

## 4. LLM Configuration, Retries & Caching

### Models & Fallback Chain
- `GEMINI_MODEL`: Primary classification model (default: `gemini-3.6-flash`).
- `GEMINI_FALLBACK_MODELS`: Comma-separated list of fallback models tried in sequential order if primary fails (default: `gemini-3.5-flash,gemini-3.7-flash`).
- `GEMINI_FALLBACK_MODEL`: Supported as a backward-compatible alias.
- The wrapper tries `GEMINI_MODEL` first, then each fallback model in order, skipping blanks and duplicate models.

### Retry & Quota Rules
- **Quota Errors** (`429` with `RESOURCE_EXHAUSTED` status/message):
  - Retried at most once on that model, and only if the server specifies a retry delay of 5 seconds or less (`retry-after` header or message delay).
  - If retry delay > 5s or no short delay specified, immediately moves to the next fallback model without retrying.
- **Transient Overload Errors** (`500`, `502`, `503`, `504`, generic timeouts): Up to 4 attempts per model with exponential backoff plus random jitter (intervals of ~1s, ~2s, ~4s), using an injectable sleep function.
- **Non-Retryable Errors** (`404`, `400`, bad request, model not found): Skip remaining retries on that model and proceed directly to the next fallback model.
- **Validation / Invalid JSON**: A single repair retry attempt with repair prompt appended before moving to the next model.
- **Total Time Budget (`LLM_TOTAL_TIMEOUT_SECONDS`)**: Default 25 seconds across all models and retries (including sleep delays). If exceeded, halts and raises `LLMError` detailing all models and attempts tried.
- **Circuit Breaker Cooldown (`LLM_QUOTA_COOLDOWN_SECONDS`)**:
  - When all models fail due to QUOTA errors in a single call, the LLM enters cooldown for 120 seconds (measured with an injectable monotonic clock, independent of the virtual app clock).
  - During cooldown, `generate_json` immediately raises `LLMUnavailableError` without making any network calls; cache hits continue to be served.
  - Cooldown expires automatically after the timeout or resets upon any successful call.
  - Health check (`GET /api/health`) reports `llm: {"status": "ok" | "cooldown", "cooldown_seconds_left": int}`.
- **Error Visibility**: When all models fail, `LLMError` lists each model tried, the number of attempts made on it, and the last error class and message (truncated to 300 characters). The API key is sanitized and never printed.

### Caching & Storage
- **Cache Directory**: Defined by `LLM_CACHE_DIR` (default: `./.llm_cache`).
- **Cache Key**: SHA-256 hash computed over:
  - JSON representation of the Pydantic schema
  - System instruction
  - User prompt
  - SHA-256 digests of all attached media payloads
  - Thinking level (`"low"`, `"medium"`, or `"high"`)
  - Primary model name (`GEMINI_MODEL`)
  *(Note: Fallback model configuration is excluded from the cache key, so changing fallbacks never invalidates cached entries).*
- **Cache Hit**: Returns the parsed Pydantic object instantly with `cached=True`, `latency_ms=0.0`, and zero backend API calls.
- **Cache Invalidation**: Delete files in `./.llm_cache/` or call `clear_cache()` in `backend/app/llm.py`.

---

## 5. Developer CLI (`try_agent1.py`)

A standalone CLI tool is provided to test Agent 1 locally without starting the full server:

```powershell
python -m backend.scripts.try_agent1 --help
```

### Examples

**Classify text complaint with location:**
```powershell
python -m backend.scripts.try_agent1 `
  --text "There is a massive water leak from the pipeline outside City Hospital for the last 2 days." `
  --address "City Hospital Main Gate" `
  --lat 19.076 `
  --lng 72.877
```

**Classify with image attachment:**
```powershell
python -m backend.scripts.try_agent1 `
  --text "Pothole on 5th Avenue" `
  --image "uploads/pothole.jpg"
```

**Bypass Cache:**
```powershell
python -m backend.scripts.try_agent1 `
  --text "Overflowing garbage bin near bus stand" `
  --no-cache
```
