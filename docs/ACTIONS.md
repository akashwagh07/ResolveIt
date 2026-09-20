# ResolveIt Action Layer Specification

The action layer (`backend/app/actions.py` and `backend/app/routers/actions.py`) maps high-level user actions performed by Citizens, Officers, and Admins to strictly validated backend commands executed through `execute_command()`. The action layer never mutates the database directly.

## Action Matrix

| Action | Label | Allowed Roles | Allowed States | Required Params | Executed Command / Side Effect |
|---|---|---|---|---|---|
| `accept` | Accept for Review | `ADMIN` | `CLASSIFIED` | None | `CHANGE_STATUS` to `UNDER_REVIEW`. |
| `confirm_classification` | Confirm Classification | `ADMIN` | `HUMAN_REVIEW` | None | `CHANGE_STATUS` to `CLASSIFIED`, clears review flag. |
| `reject_out_of_scope` | Reject as Out of Scope | `ADMIN` | `HUMAN_REVIEW` | `reason` (str) | `MARK_OUT_OF_SCOPE` with given reason. |
| `assign` | Assign Officer | `ADMIN` | `CLASSIFIED`, `UNDER_REVIEW` | `officer_id` (int), `note` (optional str) | If `CLASSIFIED`, runs `accept` (`UNDER_REVIEW`) first, then `ASSIGN`. Assigns officer, clears review flags, transitions to `ASSIGNED`. |
| `start_work` | Start Work | Assigned `OFFICER`, `ADMIN` | `ASSIGNED` | None | `CHANGE_STATUS` to `IN_PROGRESS`. |
| `approve_resolution` | Approve Resolution | `ADMIN` | `ADMIN_VERIFICATION` | None | `CHANGE_STATUS` to `CITIZEN_CONFIRMATION`, marks resolution `admin_decision = APPROVED`. |
| `reject_resolution` | Reject Resolution | `ADMIN` | `ADMIN_VERIFICATION` | `reason` (str) | `CHANGE_STATUS` to `IN_PROGRESS`, marks resolution `admin_decision = REJECTED`. |
| `confirm_resolution` | Confirm Resolution | `CITIZEN` (matching contact) | `CITIZEN_CONFIRMATION` | None | `CLOSE` with `closure_reason = CITIZEN_CONFIRMED`. Sets `resolved_at`, marks resolution `citizen_decision = CONFIRMED`, transitions to `RESOLVED`. |
| `dispute_resolution` | Dispute Resolution | `CITIZEN` (matching contact) | `CITIZEN_CONFIRMATION` | `reason` (str) | `REOPEN` with reason. Marks resolution `citizen_decision = DISPUTED`, transitions to `REOPENED`. |
| `resume_work` | Resume Work | Assigned `OFFICER`, `ADMIN` | `REOPENED` | None | `CHANGE_STATUS` to `IN_PROGRESS`. |
| `de_escalate` | De-escalate | `ADMIN` | `ESCALATED` | None | `CHANGE_STATUS` to `complaint.previous_status`. |

---

## Identity & Permissions

- **Identity Headers**:
  - `X-Demo-Role`: `CITIZEN` | `OFFICER` | `ADMIN`
  - `X-Demo-User-Id`: int (for `OFFICER` and `ADMIN`)
  - `X-Demo-Passcode`: str (for `OFFICER` and `ADMIN`, checked against `OFFICER_PASSCODE` using `secrets.compare_digest`)
  - `X-Citizen-Contact`: str (for `CITIZEN`)
- **Authorization Enforcement**:
  - Actions check that `ctx.role` is in `allowed_roles` (403 otherwise).
  - Officer actions (`start_work`, `resume_work`, and resolution upload) require `complaint.assigned_officer_id == ctx.user_id` (403 otherwise).
  - Citizen actions (`confirm_resolution`, `dispute_resolution`) require `complaint.citizen_contact == ctx.contact` (403 otherwise).
  - Actions verify complaint is in an allowed state (409 otherwise).
  - Missing parameters return 422.

---

## Resolution Upload Flow

1. **Endpoint**: `POST /api/complaints/{id}/resolution` (multipart form).
2. **Authorized Actor**: Assigned `OFFICER` only, complaint must be `IN_PROGRESS`.
3. **Payload**:
   - `description`: 10 to 1000 characters.
   - `after_images`: 1 to 4 image files (up to 10 MB each, whitelisted image extensions).
4. **File Storage**:
   - Stored in `UPLOAD_DIR/resolutions/<complaint_id>/` with cryptographically random UUID filenames.
   - Client original filenames are discarded.
   - On any validation or command failure, all saved files are cleaned up immediately.
5. **Command & Verification Hook**:
   - Creates `Evidence` records (`role="RESOLUTION_AFTER"`, `uploaded_by="OFFICER:<id>"`).
   - Executes `SUBMIT_RESOLUTION` command (`RESOLUTION_SUBMITTED`).
   - Automatically executes `CHANGE_STATUS` to `AI_VERIFICATION` via `Actor.SYSTEM`.
   - Runs `Verifier.verify()` (defaults to `StubVerifier` which returns `ADMIN_REVIEW`).
   - Executes `RECORD_VERIFICATION` via `Actor.AGENT3`, resulting in status `ADMIN_VERIFICATION`.
