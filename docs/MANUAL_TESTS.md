# ResolveIt: Citizen Intake Manual Test Checklist

This checklist verifies the citizen reporting flow (`/citizen/report`), error recovery, multimodal media handling, and outcome visualization.

Prerequisites:
- Backend running at `http://127.0.0.1:8000`
- Frontend running at `http://localhost:5173`

---

## 1. Text-Only Report
- **Steps**:
  1. Navigate to `/citizen/report`.
  2. Verify name and contact are pre-filled from the demo session.
  3. Enter description: `"Broken public street tap overflowing on pavement in Shahupuri near bank."`
  4. Select a location on the map in Shahupuri.
  5. Click **Submit Complaint**.
- **Expected Outcome**:
  - Rotating progress indicators display ("Reading your report", "Assessing severity", etc.).
  - Returns HTTP 201. The form is replaced by `ResultPanel`.
  - Status banner indicates `CLASSIFIED`, category `WATER`, issue `BROKEN_PUBLIC_TAP` or `WATER_OVERFLOW`, with severity score and priority displayed.
  - Clicking "My complaints" lists the newly created complaint under the citizen contact.

---

## 2. Photo Report
- **Steps**:
  1. Open `/citizen/report`.
  2. Click **Take photo or select image** and upload a clear JPEG/PNG of road damage or garbage (< 10 MB).
  3. Verify the image preview thumbnail appears with file size and a remove button.
  4. Leave description blank or enter brief text.
  5. Select map location and click **Submit Complaint**.
- **Expected Outcome**:
  - Submission succeeds without requiring text because media is attached.
  - AI vision inspects the image and assigns appropriate category.
  - On the detail page (`/citizen/complaints/:id`), the photo is rendered as a clickable thumbnail that expands in a lightbox modal.

---

## 3. Recorded Voice Note (Marathi)
- **Steps**:
  1. Open `/citizen/report`.
  2. In the **Voice Note** section, click **Start Recording**.
  3. Speak a short civic complaint in Marathi (e.g., *"आमच्या प्रभागामध्ये गेल्या दोन दिवसांपासून कचरा उचललेला नाही आणि दुर्गंधी येत आहे"*).
  4. Click **Stop Recording**.
  5. Verify the audio is resampled in the browser to a 16 kHz 16-bit PCM WAV (`voice-note.wav`).
  6. Play back the audio using the inline audio controls.
  7. Select location and submit.
- **Expected Outcome**:
  - The WAV file is uploaded with MIME type `audio/wav`.
  - Agent 1 transcribes vernacular Marathi and translates to English.
  - Classified under `WASTE` / `GARBAGE_NOT_COLLECTED`.
  - Detail page includes playable `<audio controls>` element.

---

## 4. Uploaded Audio File
- **Steps**:
  1. Open `/citizen/report`.
  2. Switch the Voice Note tab to **Upload File**.
  3. Select a valid audio file (`.mp3`, `.wav`, `.ogg`, `.m4a`, or `.flac`, < 15 MB).
  4. Verify the filename and size appear with an inline audio player.
  5. Submit the complaint.
- **Expected Outcome**:
  - File is uploaded to the backend `audio` field.
  - Pipeline routes audio to Agent 1 with `expected_kind="AUDIO"`.
  - Audio player functions correctly on the resulting detail page.

---

## 5. Invalid / Oversized File
- **Steps**:
  1. Try uploading an unsupported file format (e.g. `.exe`, `.pdf`, `.zip`) into the photo or video inputs.
  2. Try uploading a photo larger than 10 MB or video larger than 15 MB.
- **Expected Outcome**:
  - The client immediately catches the file extension or size excess.
  - File input rejects the file and displays an inline error message (e.g. *"Photo exceeds the 10 MB limit (12.4 MB)"*).
  - Submit remains disabled or blocked with clear inline error highlighting.

---

## 6. Missing Location Validation
- **Steps**:
  1. Open `/citizen/report`.
  2. Clear the coordinates (or trigger a form reset without map interaction).
  3. Fill description with test text.
  4. Click **Submit Complaint**.
- **Expected Outcome**:
  - Submission is blocked on the client side.
  - The page smoothly scrolls to the location picker section.
  - An inline red error message appears: *"Please select a location on the map."*

---

## 7. Denied Geolocation Permission
- **Steps**:
  1. In browser site settings for `localhost`, set Location permission to **Block / Denied**.
  2. Reload `/citizen/report`.
  3. Click **Use my current location**.
- **Expected Outcome**:
  - The app gracefully catches `err.PERMISSION_DENIED`.
  - An alert banner informs the user: *"Location permission denied. Please tap or click on the map to set your location."*
  - The rest of the form and manual pin-dropping on the Leaflet map remain fully functional.

---

## 8. Double-Click Submit Protection
- **Steps**:
  1. Complete all valid form fields.
  2. Rapidly double-click or multi-click the **Submit Complaint** button.
- **Expected Outcome**:
  - The button is immediately disabled (`disabled={isSubmitting}`) upon the first click.
  - The full-width `SubmissionProgress` panel replaces the form controls.
  - Only a single HTTP POST request is dispatched to `/api/complaints`.

---

## 9. Cancel While Submitting
- **Steps**:
  1. Submit a complaint with text and attachments.
  2. While the rotating progress banner is active ("Reading your report..."), click **Cancel Submission**.
- **Expected Outcome**:
  - The `AbortController` signal fires immediately.
  - In-flight fetch request is aborted.
  - The UI cleanly exits the submitting state and returns to the form with previously entered fields intact.
  - An alert indicates *"Complaint submission was cancelled."*

---

## 10. Non-Civic Message (Out of Scope)
- **Steps**:
  1. Enter non-civic input: *"Where can I buy tickets for the cricket match tomorrow evening?"*
  2. Pick any location and click **Submit Complaint**.
- **Expected Outcome**:
  - Agent 1 flags low civic relevance.
  - Agent 2 assigns outcome `OUT_OF_SCOPE`.
  - `ResultPanel` displays the polite status banner: *"This doesn't look like a civic issue"*.
  - Trace explains that the inquiry does not pertain to municipal civic infrastructure.

---

## 11. Backend Offline / Server Failure
- **Steps**:
  1. Temporarily stop the backend server (`Ctrl+C` in the backend terminal).
  2. In the frontend, fill a report and click **Submit Complaint**.
- **Expected Outcome**:
  - The client catches the network failure before any server processing.
  - Clear message is displayed: *"The server could not be reached. Your report was not sent. Please verify the server is running and try again."*
  - Form inputs are preserved so the citizen does not lose their typed description or selected files.

---

## 12. Full Closed-Loop Lifecycle (Admin Assign -> Officer Resolve -> Admin Approve -> Citizen Confirm)
- **Steps**:
  1. **Citizen Submission**: Log in as Citizen (`Rahul Deshmukh`, `+91 9822012345`). Submit a high-confidence pothole report with text and photo. Note the generated complaint ID (e.g. `c...`).
  2. **Admin Assignment**:
     - Click **Switch role** in header, select **Admin**, choose an admin account (e.g. `Sanjay Deshmukh`), enter passcode (default `officer123`, or configured `OFFICER_PASSCODE`), and enter.
     - In **Work Queue** (`/admin`), find the new complaint (status `CLASSIFIED`). Click **Review**.
     - In **Available Actions**, click **Assign Officer**.
     - Select a field officer belonging to the complaint's department (e.g. `Vikram Jadhav`), add an optional note, and click **Confirm & Execute**.
     - Verify status transitions to `ASSIGNED` and assigned officer name appears.
  3. **Officer Start Work & Resolution Upload**:
     - Click **Switch role**, select **Officer**, choose `Vikram Jadhav`, enter passcode (default `officer123`, or configured `OFFICER_PASSCODE`), and enter.
     - On **My Work** (`/officer`), find the complaint in `ASSIGNED` status. Click **Start Work**.
     - Status transitions to `IN_PROGRESS`.
     - Click **View Dossier**. The **Resolution Proof** form appears with the original complaint photo side-by-side as a reference.
     - Enter work description: `"Pothole filled with asphalt mastic and compacted with mechanical roller."`
     - Attach 1–2 after photos (< 10 MB each) and click **Submit for Verification**.
     - Status updates to `ADMIN_VERIFICATION`.
  4. **Admin Approval**:
     - Switch role to **Admin**.
     - Open the complaint detail. The **Administrative Verification** section is promoted to the top with `VerificationCard` and `BeforeAfter` comparison.
     - Click **Approve Resolution** in `ActionPanel`.
     - Status updates to `CITIZEN_CONFIRMATION`.
  5. **Citizen Confirmation & Closure**:
     - Switch role to **Citizen** (`+91 9822012345`).
     - Go to **My Complaints** and open the complaint.
     - A highlighted card displays the Before/After photos and officer note with **Confirm Resolution** and **Dispute Resolution** actions.
     - Click **Confirm Resolution**.
     - Complaint transitions to `RESOLVED`. The green **Complaint Successfully Resolved & Closed** banner displays the resolution timestamp and completes the closed loop.

---

## 13. Dispute Path (Citizen Dispute -> Reopened -> Resume Work)
- **Steps**:
  1. Follow steps 1–4 of test 12 until complaint reaches `CITIZEN_CONFIRMATION`.
  2. Log in as the reporting Citizen. Open the complaint detail page.
  3. In the highlighted resolution card, click **Dispute Resolution**.
  4. In the modal dialog, enter dispute reason: `"Road surface is still uneven and bitumen began cracking on day 2."`
  5. Click **Confirm & Execute**.
- **Expected Outcome**:
  - Complaint transitions to status `REOPENED`.
  - The latest resolution record marks `citizen_decision: DISPUTED`.
  - An audit event is logged with the citizen dispute reasoning.
  - Logging in as the assigned Officer shows the complaint in the `/officer` work queue under `REOPENED` status with an action to **Resume Work**.

---

## 14. Wrong Passcode on Demo Login
- **Steps**:
  1. From `/`, select **Officer** or **Admin**.
  2. Select an officer or admin account.
  3. Enter an incorrect passcode (e.g. `wrongpass123`).
  4. Click **Enter as Officer/Admin**.
- **Expected Outcome**:
  - The request to `GET /api/auth/whoami` with the invalid `X-Demo-Passcode` fails with HTTP 401.
  - An inline red error message appears: *"Wrong passcode. Ask the team for the demo passcode."*
  - Session is NOT created in `localStorage` or `sessionStorage`.
  - The user remains on the Landing Page.

---

## 15. Wrong-Role Route Access & Route Guarding
- **Steps**:
  1. Log in as **Citizen** (`Rahul Deshmukh`).
  2. In the browser address bar, manually type `/admin` and press Enter.
  3. In the address bar, manually type `/officer` and press Enter.
  4. Switch role to **Officer**. Try navigating to `/admin` or `/citizen/report`.
- **Expected Outcome**:
  - `RoleGuard` catches the role mismatch.
  - The user is redirected to the Landing Page `/`.
  - A prominent amber alert banner displays:
    *"Access denied: page requires ADMIN role, but you are currently in session as CITIZEN."*

---

## 16. Two Browsers as Different Roles (Simultaneous Walkthrough)
- **Steps**:
  1. Open Chrome window 1 (Citizen or Admin): log in as Admin.
  2. Open an Incognito window or Firefox/Edge window 2 (Officer): log in as Officer `Vikram Jadhav`.
  3. In window 1, assign a complaint to `Vikram Jadhav`.
  4. In window 2, refresh `/officer`.
- **Expected Outcome**:
  - Window 2 immediately reflects the new task assigned from Window 1 without session collision because credentials are independently isolated in separate browser instances.
  - Officer can upload resolution proof in window 2, and Admin in window 1 immediately sees the before/after evidence upon refresh.
