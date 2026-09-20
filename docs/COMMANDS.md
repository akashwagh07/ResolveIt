# ResolveIt Command Specification

All state transitions and mutations to complaints in ResolveIt must pass through `execute_command()`. The command gate enforces strict schema validation, actor permissions, state validity, and deterministic business rules. Any invalid command is rejected atomically, logged into `command_rejections`, and never partially applied.

## Command Reference

| Command | Key Fields | Allowed Actors | Allowed States | Resulting State Transition / Effect |
|---|---|---|---|---|
| `CREATE_COMPLAINT` | `citizen_name`, `citizen_contact`, `raw_text`, `language`, `latitude`, `longitude`, `address_text`, `category`, `issue`, `category_confidence`, `civic_relevance`, `credibility`, `severity_score`, `severity_level`, `priority`, `severity_factors`, `priority_factors`, `department_code`, `structured_summary`, `ai_reasoning`, `missing_info`, `evidence`, `outcome`, `merge_into_id` | `AGENT2`, `SYSTEM` | *(None / New)* | Creates complaint in `SUBMITTED`, steps through `AI_ANALYZING`, to `outcome` (`CLASSIFIED`, `HUMAN_REVIEW`, `OUT_OF_SCOPE`, or `MERGED`). High/review confidence gating and initial SLA calculation applied. |
| `LINK_CLUSTER` | `complaint_id`, `kind` (`DUPLICATE` \| `ROOT_CAUSE`), `cluster_id` or `new_cluster`, `confidence`, `reasoning` | `AGENT2`, `AGENT3`, `SYSTEM` | Any active state | Links complaint to existing cluster or creates a new cluster record; logs audit event. |
| `SET_PRIORITY` | `complaint_id`, `priority`, `priority_factors`, `reasoning` | `AGENT2`, `AGENT3`, `SYSTEM`, `ADMIN` | `CLASSIFIED`, `UNDER_REVIEW`, `ASSIGNED`, `IN_PROGRESS`, `REOPENED`, `ESCALATED` | Updates complaint priority, factor breakdown, and recalculates SLA deadline from `created_at`. |
| `FLAG_HUMAN_REVIEW` | `complaint_id`, `reason`, `confidence` | `AGENT1`, `AGENT2`, `AGENT3`, `SYSTEM` | Any active state | Sets `needs_review = True` and `review_reason`; logs audit event. |
| `MARK_OUT_OF_SCOPE` | `complaint_id`, `reason` | `AGENT2`, `ADMIN` | `AI_ANALYZING`, `HUMAN_REVIEW` | Transitions complaint to `OUT_OF_SCOPE`. |
| `ASSIGN` | `complaint_id`, `officer_id`, `note` | `ADMIN` | `UNDER_REVIEW` | Sets `assigned_officer_id` (must belong to the complaint's department), clears review flags, and transitions from `UNDER_REVIEW` to `ASSIGNED`. |
| `CHANGE_STATUS` | `complaint_id`, `new_status`, `reason` | `ADMIN`, `OFFICER`, `AGENT3`, `SYSTEM` | State-dependent (see section below) | Executes permitted workflow move, validating actor authority and setting transition metadata. |
| `SUBMIT_RESOLUTION` | `complaint_id`, `officer_id`, `description`, `after_evidence_ids` | `OFFICER` | `IN_PROGRESS` | Verifies officer is assigned officer and evidence has role `RESOLUTION_AFTER`; creates `Resolution` record; transitions to `RESOLUTION_SUBMITTED`. |
| `RECORD_VERIFICATION` | `complaint_id`, `evidence_relevant` (optional), `location_consistent` (optional), `visual_change_detected` (optional), `confidence`, `recommendation`, `reasoning` | `AGENT3` | `AI_VERIFICATION` | Saves AI verification verdict on latest resolution. Moves to `ADMIN_VERIFICATION` (if `ADMIN_REVIEW` or low-confidence reject) or `IN_PROGRESS` (if auto-reject or `NEEDS_MORE_EVIDENCE`). |
| `SEND_FOLLOWUP` | `complaint_id`, `message`, `level` (1-3) | `AGENT3`, `SYSTEM` | `CLASSIFIED`, `UNDER_REVIEW`, `ASSIGNED`, `IN_PROGRESS`, `ESCALATED` | Updates `last_followup_at` and appends citizen-visible audit event. |
| `ESCALATE` | `complaint_id`, `reason`, `dossier` | `AGENT3`, `SYSTEM` | Any active state | Increments `escalation_level` (bounded by department chain length), creates `Escalation` record, stores `previous_status`, and transitions to `ESCALATED`. |
| `CLOSE` | `complaint_id`, `closure_reason` (`CITIZEN_CONFIRMED` \| `AUTO_TIMEOUT`) | `CITIZEN`, `SYSTEM` (`AUTO_TIMEOUT` only) | `CITIZEN_CONFIRMATION` | Sets `resolved_at`, marks latest resolution decision, and transitions to `RESOLVED`. |
| `REOPEN` | `complaint_id`, `reason` | `CITIZEN` | `CITIZEN_CONFIRMATION` | Marks latest resolution as disputed and transitions to `REOPENED`. |

---

## Allowed `CHANGE_STATUS` Transitions

| Source Status | Target Status | Authorized Actors | Notes / Side Effects |
|---|---|---|---|
| `SUBMITTED` | `AI_ANALYZING` | `SYSTEM` | Automated intake pipeline trigger |
| `CLASSIFIED` | `UNDER_REVIEW` | `ADMIN` | Officer routing review |
| `HUMAN_REVIEW` | `CLASSIFIED` | `ADMIN` | Clears `needs_review` and `review_reason` |
| `HUMAN_REVIEW` | `OUT_OF_SCOPE` | `ADMIN` | Manual rejection |
| `ASSIGNED` | `IN_PROGRESS` | `OFFICER` (assigned only), `ADMIN` | Work start |
| `RESOLUTION_SUBMITTED` | `AI_VERIFICATION` | `AGENT3`, `SYSTEM` | Triggers AI verification analysis |
| `ADMIN_VERIFICATION` | `CITIZEN_CONFIRMATION` | `ADMIN` | Sets latest resolution `admin_decision = APPROVED` |
| `ADMIN_VERIFICATION` | `IN_PROGRESS` | `ADMIN` | Sets latest resolution `admin_decision = REJECTED` |
| `REOPENED` | `IN_PROGRESS` | `ADMIN`, `OFFICER` | Rework after dispute |
| `ERROR` | `AI_ANALYZING` | `ADMIN`, `SYSTEM` | Retry failed intake |
| `ESCALATED` | `previous_status` | `ADMIN` | Returns only to the state held prior to escalation |
