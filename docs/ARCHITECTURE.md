# ResolveIt architecture

ResolveIt is a closed-loop civic issue resolution platform: citizen complaint,
AI understanding, AI decision, executable workflow, government action,
resolution evidence, verification, citizen confirmation. The department side is
simulated with seeded officer accounts. All severity and SLA values are prototype
rules, not official municipal standards.

## Stack
- Backend: FastAPI, SQLAlchemy, SQLite, Pydantic v2, pytest
- AI: Gemini multimodal via the official Google GenAI Python SDK, all calls
  through backend/app/llm.py with an on-disk response cache keyed by input hash
  so demos work even if the API is slow or offline
- Frontend: React, Vite, Tailwind, Leaflet (OpenStreetMap tiles), Recharts
- Weather: Open-Meteo (no key)

## Core principles
1. Agents propose, the backend executes. Agents emit command blocks (validated
   JSON). The command gate checks schema and allowed state transitions, then
   executes and writes an audit event. Rejected commands are logged too.
2. Deterministic where it must be defensible: severity score, department mapping,
   priority, SLA timing, escalation timing, state transitions.
3. LLM only for understanding (text, image, audio), evidence judgement
   (before/after), and writing text (summaries, dossiers).
4. Every AI decision carries confidence and human-readable reasons.
5. Confidence gating: >= 0.85 automatic; 0.60 to 0.84 proceeds but flagged for
   human review; < 0.60 goes to HUMAN_REVIEW. Applies to classification,
   department mapping and evidence verification.
6. AI never declares a government worker's proof genuine. It reports whether the
   evidence appears relevant and consistent. Admin and citizen confirmation stay
   in the loop.

## Agents
- Agent 1 (classify): input text, image, audio, video frames, GPS. Output:
  category, issue, description, duration (only if stated), location, evidence
  flags, civic_relevance, credibility signals, confidence. Does NOT decide severity.
- Agent 2 (decide): input Agent 1 output plus context. Calls the rule engine
  (severity, department, priority, SLA) and the context engine (duplicates, root
  cause hypothesis, nearby sensitive places, rain forecast). Emits commands.
- Agent 3 (resolve): manages the admin lifecycle. Verifies resolution evidence
  (relevance, location consistency, visual change, confidence, recommendation),
  requests citizen confirmation, and emits follow-up and escalation commands
  when the deterministic scheduler wakes it with a case and a deadline.

## Ontology (canonical)
ROADS: pothole, road damage, road cracks, road debris, damaged speed breaker,
  footpath damage, blocked footpath, missing road sign
STREET_LIGHTING: light not working, flickering light, damaged pole, fallen pole,
  exposed wiring, insufficient lighting
WASTE: garbage not collected, overflowing bin, illegal dumping, garbage on road,
  construction waste, missed collection, dead animal (alias: animal carcass)
WATER: no water supply, low water pressure, water leakage, pipeline burst,
  contaminated water, water overflow, broken public tap
DRAINAGE: blocked drain, drain overflow, sewage leakage, sewage overflow,
  blocked manhole, missing manhole cover, waterlogging, stagnant water
PARKS_ENVIRONMENT: fallen tree, dangerous branch, tree maintenance, damaged
  playground, damaged park, unclean park, illegal tree cutting
ENCROACHMENT: road encroachment, footpath encroachment, illegal construction,
  unauthorized structure, construction obstruction, unauthorized excavation
ANIMALS: stray dog, stray cattle, aggressive animal, injured animal,
  animal traffic obstruction
TRAFFIC: traffic signal failure, damaged traffic sign, missing traffic sign,
  unsafe crossing, traffic obstruction, parking obstruction
SANITATION: public toilet issue, foul smell, mosquito breeding, pest problem,
  unclean public area, unhygienic condition
OTHER: anything else. Non-civic input gets civic_relevance LOW and OUT_OF_SCOPE.
Note: stagnant water is canonical under DRAINAGE only; animal carcass is an alias
of WASTE dead animal.

## Severity (rule engine)
Score = base issue risk + public safety risk + affected area + traffic/population
impact + duration + context, capped at 10. Bands: 0-2 LOW, 3-4 MEDIUM, 5-7 HIGH,
8-10 CRITICAL. Output includes score, band and a list of reasons.
Priority mapping: LOW=NORMAL, MEDIUM=STANDARD, HIGH=HIGH, CRITICAL=EMERGENCY.
Dynamic priority modifiers (adjust priority, never the base severity):
nearby school or hospital, major road, transit area, duplicate count, SLA age,
48-hour rain forecast for drainage and road issues. Always return a breakdown.

## Department mapping
pothole/road issues -> Roads; streetlight issues -> Electrical/Street Lighting;
garbage/waste -> Waste Management; water issues -> Water Supply; drainage and
sewage -> Drainage/Sewerage; trees and parks -> Parks/Garden; encroachment and
illegal construction -> Building/Town Planning; animals -> Animal Control;
traffic -> Traffic/Infrastructure; sanitation -> Sanitation/Health. The AI may
suggest a department; the rule map validates it.

## SLA (hours: initial response / follow-up / escalation)
NORMAL 48/72/96; STANDARD 24/48/72; HIGH 12/24/48; EMERGENCY 2/6/12.
All SLA math uses a virtual clock (clock.now()) so the demo can fast-forward time.

## States
Main: SUBMITTED, AI_ANALYZING, CLASSIFIED, UNDER_REVIEW, ASSIGNED, IN_PROGRESS,
RESOLUTION_SUBMITTED, AI_VERIFICATION, ADMIN_VERIFICATION,
CITIZEN_CONFIRMATION, RESOLVED.
Other: HUMAN_REVIEW, OUT_OF_SCOPE, MERGED, ESCALATED, REOPENED, ERROR.
Transitions:
- SUBMITTED -> AI_ANALYZING -> CLASSIFIED | HUMAN_REVIEW | OUT_OF_SCOPE | MERGED | ERROR
- HUMAN_REVIEW -> CLASSIFIED | OUT_OF_SCOPE
- CLASSIFIED -> UNDER_REVIEW -> ASSIGNED -> IN_PROGRESS -> RESOLUTION_SUBMITTED
  -> AI_VERIFICATION -> ADMIN_VERIFICATION -> CITIZEN_CONFIRMATION -> RESOLVED
- AI_VERIFICATION -> IN_PROGRESS (evidence rejected)
- ADMIN_VERIFICATION -> IN_PROGRESS (admin rejects)
- CITIZEN_CONFIRMATION -> RESOLVED (confirm) | REOPENED (dispute)
- REOPENED -> IN_PROGRESS
- Any active state -> ESCALATED on SLA breach; store previous_status and return
  to it when a higher authority acts
- ERROR -> AI_ANALYZING (retry)

## Command whitelist
CREATE_COMPLAINT, LINK_CLUSTER, SET_PRIORITY, FLAG_HUMAN_REVIEW, MARK_OUT_OF_SCOPE,
ASSIGN, CHANGE_STATUS, SUBMIT_RESOLUTION, RECORD_VERIFICATION, SEND_FOLLOWUP,
ESCALATE, CLOSE, REOPEN. Each has a pydantic schema and is valid only in
specific states.

## Roles
CITIZEN, OFFICER (belongs to a department), ADMIN (supervisor). Use simple seeded
demo accounts with token login. Do not build real authentication infrastructure.

## Data model
users, departments (with escalates_to), clusters (kind DUPLICATE or ROOT_CAUSE,
lat, lng, hypothesis, confidence), complaints (citizen_id, department_id,
cluster_id, category, issue, status, previous_status, severity_score, severity,
priority, ai_confidence, credibility, lat, lng, description, sla fields,
created_at, updated_at), evidence (complaint_id, type, file_url, phash,
uploaded_by_role), audit_events (complaint_id, actor, action, payload json,
confidence, at), resolutions (complaint_id, officer_id, description,
ai_verdict json, ai_confidence, admin_decision, citizen_decision),
escalations (complaint_id, level, dossier, at).

## Differentiators (build in this order after the core loop works)
1. Proof-of-fix: before/after verification plus citizen (and neighbouring
   reporter) confirmation or dispute.
2. Dynamic priority with rain forecast and a visible score breakdown.
3. Duplicate clustering and cross-type root-cause hypothesis (always presented as
   a hypothesis with confidence, never as fact).
4. Escalation dossier and recurrence flag.
Stretch: report credibility check (EXIF GPS, perceptual hash), field work orders,
Hindi/Marathi voice input.

## Demo support
A demo control panel: fast-forward the virtual clock, toggle a rain forecast,
seed sample complaints, and simulate the department officer.
