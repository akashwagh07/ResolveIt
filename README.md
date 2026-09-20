# Resolveit

### AI-Powered Civic Issue Resolution Platform

> **Report. Resolve. Verify.**

Resolveit is an AI-powered civic issue resolution platform designed to transform citizen complaints into structured, prioritized, traceable workflows for government departments.

Citizens can report issues using **text, images, audio, video, and location data**. Resolveit uses a multi-agent AI architecture to classify the issue, assess its severity, route it to the appropriate department, monitor its resolution, and verify resolution evidence before closing the complaint.

The platform is designed around a **closed-loop workflow** that keeps citizens informed from initial reporting to final resolution.

---

## Problem

Civic issues such as potholes, garbage accumulation, broken streetlights, water leakage, drainage overflow, and illegal construction are often reported through fragmented channels.

This creates several problems:

- Complaints may lack sufficient evidence or structured information.
- Reports can be routed to the wrong department.
- Severity and urgency may not be assessed consistently.
- Citizens often have limited visibility into complaint progress.
- Unresolved complaints may not receive timely follow-ups.
- Resolution claims may lack verifiable evidence.
- There is limited traceability across the complete complaint lifecycle.

Resolveit addresses these challenges by creating an **AI-assisted, evidence-driven civic complaint workflow**.

---

# Key Features

### Multimodal Complaint Submission

Citizens can submit complaints using:

- Text
- Images
- Audio
- Video
- Location

The system extracts relevant information from the submitted evidence and converts it into structured complaint data.

---

### AI-Powered Issue Classification

The first AI agent identifies:

- Civic issue category
- Specific issue type
- Relevant description
- Available location information
- Evidence type
- Extracted contextual information
- Classification confidence

Supported categories include:

- Roads
- Streetlights
- Garbage
- Water
- Drainage & Sewage
- Parks & Environment
- Sanitation & Public Health
- Encroachment & Illegal Construction
- Stray Animals
- Traffic & Public Infrastructure
- Other

---

### Intelligent Severity Assessment

The second AI agent evaluates the classified complaint using predefined decision rules.

Severity considers factors such as:

- Base issue risk
- Public safety impact
- Number of people or area affected
- Duration of the issue
- Available evidence
- Contextual risk

Complaints are categorized into:

`LOW` → `MEDIUM` → `HIGH` → `CRITICAL`

The system also determines the appropriate priority and workflow requirements.

> Severity values and SLA thresholds in the prototype are configurable hackathon rules and are not intended to represent official municipal standards.

---

### Automatic Department Routing

Resolveit maps complaints to the appropriate department.

Examples:

| Issue | Department |
|---|---|
| Pothole | Roads / Public Works |
| Streetlight failure | Electrical / Street Lighting |
| Garbage accumulation | Waste Management |
| Water leakage | Water Supply |
| Sewage overflow | Drainage / Sewerage |
| Fallen tree | Parks / Garden |
| Illegal construction | Building / Town Planning |
| Stray animals | Animal Control |
| Traffic signal failure | Traffic / Infrastructure |

The AI suggests the routing while deterministic backend rules validate the final decision.
