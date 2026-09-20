# ResolveIt Rule Engine Specification

The ResolveIt rule engine is a suite of purely deterministic algorithms executing in Python without any LLM calls or probabilistic inference. It governs **Severity Scoring**, **Priority Assignment**, and **Department Routing**.

---

## 1. Severity Scoring (`backend/app/engines/severity.py`)

### Algorithm
The severity score is an integer between **0 and 10**, computed as the sum of 6 distinct risk components, floored at 0 and capped at 10:

$$\text{Score} = \min\left(10, \max\left(0, \text{base\_risk} + \text{safety} + \text{area} + \text{traffic} + \text{duration} + \text{context}\right)\right)$$

Only nonzero components (plus the base risk) are included in the `factors` list. Each factor is structured as `{ "factor": str, "points": int, "reason": str }` with plain English explanations.

### Severity Levels
| Score Range | Severity Level | Description |
|:---:|:---:|:---|
| 0 – 2 | `LOW` | Minor inconvenience, cosmetic flaw, low hazard |
| 3 – 5 | `MEDIUM` | Moderate civic disruption, standard repair needed |
| 6 – 7 | `HIGH` | Serious civic hazard or significant disruption |
| 8 – 10 | `CRITICAL` | Imminent safety threat, major arterial disruption |

---

### Component Breakdown

#### a) Base Issue Risk (0 – 5)
Every issue code in `ontology.py` maps to a baseline risk point value in `BASE_RISK`. Unmapped issues default to **2**.

| Category | Issue Code | Base Risk |
|:---|:---|:---:|
| **ROADS** | `POTHOLE` | 3 |
| | `ROAD_DAMAGE` | 3 |
| | `ROAD_CRACKS` | 1 |
| | `ROAD_DEBRIS` | 2 |
| | `DAMAGED_SPEED_BREAKER` | 2 |
| | `FOOTPATH_DAMAGE` | 2 |
| | `BLOCKED_FOOTPATH` | 1 |
| | `MISSING_ROAD_SIGN` | 2 |
| **STREET_LIGHTING** | `LIGHT_NOT_WORKING` | 2 |
| | `FLICKERING` | 1 |
| | `DAMAGED_POLE` | 3 |
| | `FALLEN_POLE` | 5 |
| | `EXPOSED_WIRING` | 5 |
| | `INSUFFICIENT_LIGHTING` | 1 |
| **WASTE** | `GARBAGE_NOT_COLLECTED` | 2 |
| | `OVERFLOWING_BIN` | 2 |
| | `ILLEGAL_DUMPING` | 2 |
| | `GARBAGE_ON_ROAD` | 2 |
| | `CONSTRUCTION_WASTE` | 2 |
| | `MISSED_COLLECTION` | 1 |
| | `DEAD_ANIMAL` | 3 |
| **WATER** | `NO_SUPPLY` | 3 |
| | `LOW_PRESSURE` | 1 |
| | `LEAKAGE` | 2 |
| | `PIPELINE_BURST` | 4 |
| | `CONTAMINATED` | 4 |
| | `OVERFLOW` | 2 |
| | `BROKEN_PUBLIC_TAP` | 1 |
| **DRAINAGE** | `BLOCKED_DRAIN` | 2 |
| | `DRAIN_OVERFLOW` | 3 |
| | `SEWAGE_LEAKAGE` | 3 |
| | `SEWAGE_OVERFLOW` | 4 |
| | `BLOCKED_MANHOLE` | 2 |
| | `MISSING_MANHOLE_COVER` | 5 |
| | `WATERLOGGING` | 3 |
| | `STAGNANT_WATER` | 2 |
| **PARKS_ENVIRONMENT** | `FALLEN_TREE` | 4 |
| | `DANGEROUS_BRANCH` | 3 |
| | `TREE_MAINTENANCE` | 1 |
| | `DAMAGED_PLAYGROUND` | 2 |
| | `DAMAGED_PARK` | 1 |
| | `UNCLEAN_PARK` | 1 |
| | `ILLEGAL_TREE_CUTTING` | 2 |
| **ENCROACHMENT** | `ILLEGAL_CONSTRUCTION` | 2 |
| | `UNAUTHORIZED_EXCAVATION` | 3 |
| | `COMMERCIAL_ENCROACHMENT` | 1 |
| | `FOOTPATH_HAWKER` | 1 |
| | `TEMPORARY_STRUCTURE` | 1 |
| | `VEHICLE_ENCROACHMENT` | 1 |
| **ANIMALS** | `STRAY_DOG` | 2 |
| | `STRAY_CATTLE` | 2 |
| | `AGGRESSIVE_ANIMAL` | 4 |
| | `INJURED_ANIMAL` | 3 |
| | `ANIMAL_TRAFFIC_OBSTRUCTION` | 2 |
| **TRAFFIC** | `SIGNAL_FAILURE` | 4 |
| | `DAMAGED_SIGN` | 2 |
| | `MISSING_SIGN` | 2 |
| | `UNSAFE_CROSSING` | 3 |
| | `TRAFFIC_OBSTRUCTION` | 2 |
| | `PARKING_OBSTRUCTION` | 1 |
| **SANITATION** | `PUBLIC_TOILET_ISSUE` | 2 |
| | `FOUL_SMELL` | 1 |
| | `MOSQUITO_BREEDING` | 3 |
| | `PEST_PROBLEM` | 2 |
| | `UNCLEAN_PUBLIC_AREA` | 1 |
| | `UNHYGIENIC_CONDITION` | 2 |
| **OTHER** | `OTHER` | 1 |

#### b) Public Safety (0 – 2)
- `SAFETY_HAZARD` context tag: **+2 points** ("Direct safety hazard flagged")
- Otherwise, `HEALTH_HAZARD` context tag: **+1 point** ("Public health hazard flagged")

#### c) Affected Area (0 – 2)
- `size_hint == "LARGE"`: **+2 points** ("Large affected area or physical scope")
- `size_hint == "MEDIUM"`: **+1 point** ("Medium affected area or physical scope")
- `size_hint == "SMALL"` or unset: **0 points**

#### d) Traffic & Population (0 – 2)
- Any of `MAJOR_ROAD`, `TRANSIT_AREA`, or `TRAFFIC_IMPACT` present: **+1 point** ("Located on a major road, transit corridor, or causing traffic disruption")
- `HIGH_PEDESTRIAN` present: **+1 point** ("High pedestrian footfall zone")

#### e) Duration (0 – 2)
- `duration_days >= 14`: **+2 points** ("Persistent unresolved condition lasting 14+ days")
- `duration_days >= 7`: **+1 point** ("Ongoing condition lasting 7+ days")

#### f) Context Sensitivity (0 – 1)
- Either `SCHOOL_NEARBY` or `HOSPITAL_NEARBY` present: **+1 point** ("Sensitive location: school or hospital in immediate vicinity")

---

## 2. Priority Assignment (`backend/app/engines/priority.py`)

### Baseline Priority from Severity Level
| Severity Level | Baseline Priority |
|:---|:---|
| `LOW` | `NORMAL` |
| `MEDIUM` | `STANDARD` |
| `HIGH` | `HIGH` |
| `CRITICAL` | `EMERGENCY` |

### Sensitive Location Bump Rule
If `SCHOOL_NEARBY` or `HOSPITAL_NEARBY` is present in `context_tags`:
- `MEDIUM` severity (`STANDARD` priority) is bumped up to **`HIGH`** (+1 tier).
- `HIGH` severity (`HIGH` priority) is bumped up to **`EMERGENCY`** (+1 tier).
- **`LOW`** and **`CRITICAL`** levels **never bump**.

Priority values strictly mirror `PriorityEnum` (`NORMAL`, `STANDARD`, `HIGH`, `EMERGENCY`). The priority engine returns `PriorityResult(priority, factors)` recording each contributing rule.

---

## 3. Department Routing (`backend/app/engines/department.py`)

ResolveIt uses deterministic rule-based department assignment:
1. The database `departments` table is queried for the department whose `categories` JSON list contains the complaint's `category`.
2. If no department matches, or if the category is `OTHER`, complaints are routed to `TRIAGE_DEPARTMENT_CODE` (`"SANITATION"`, Health & Sanitation Department).
3. `OUT_OF_SCOPE` complaints are also routed to `TRIAGE_DEPARTMENT_CODE` to fulfill the command schema invariant requiring a valid `department_code`.
4. The rule engine is authoritative; LLM department suggestions are never accepted for routing.
