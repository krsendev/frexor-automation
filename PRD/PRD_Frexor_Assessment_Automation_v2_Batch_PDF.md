# PRD — Frexor Psychology Assessment Automation
## Batch Processing, Automated Submission, and PDF Result Handling

**Document Version:** 2.0  
**Status:** Draft for implementation  
**Audience:** Codex / Software Engineer / Automation Developer  
**Target Platform:** Windows  
**Primary System:** Frexor Psychology Assessment System (`.exe`)  
**Data Source:** Google Sheets  
**Primary Goal:** Automate end-to-end data entry and result generation for multiple assessment participants.

---

## 1. Executive Summary

This project automates the process of transferring assessment answers stored in Google Sheets into the **Frexor Psychology Assessment System** running as a Windows `.exe` application.

The source data originates from physical assessment answer sheets. The physical-sheet scanning/parsing process is **outside the scope of this project**. It is assumed that the final, validated answers are already available in Google Sheets.

The automation must support three assessment types:

1. **Attitude Test — DISC**
   - Each question has two answers:
     - Mirip
     - Tidak Mirip

2. **Working Style Test — VAK**
   - Each question has one answer.
   - Multiple-choice format.

3. **Aptitude Test — IQ**
   - Each question has one answer.
   - Multiple-choice format.

The system must support **batch processing**. For example, if there are 60 participants in Google Sheets, the operator should be able to start the automation once and let the system process the participants sequentially without manually entering every participant.

For each participant, the automation must:

1. Read the participant's data from Google Sheets.
2. Validate the data.
3. Open or prepare Frexor.
4. Enter DISC answers.
5. Enter VAK answers.
6. Enter IQ answers.
7. Validate that the expected data has been entered.
8. Click the Frexor `Kirim` / Submit action automatically.
9. Wait for Frexor to generate the assessment result PDF.
10. Verify that the PDF was successfully created.
11. Associate the PDF with the correct participant.
12. Update the participant's processing status.
13. Continue with the next eligible participant.

A participant is **not considered complete merely because the form was filled or the Submit button was clicked**.

The final success condition is:

> **Assessment data successfully entered + submitted + PDF successfully generated and verified.**

---

# 2. Problem Statement

The current workflow requires an operator to manually transfer assessment answers from Google Sheets into the Frexor desktop application.

This becomes inefficient and error-prone when processing large batches of participants.

For example, processing 60 participants manually requires repeatedly:

- finding a participant,
- opening or navigating the relevant assessment,
- entering DISC answers,
- entering VAK answers,
- entering IQ answers,
- pressing Submit,
- waiting for the result,
- handling the generated PDF,
- and moving to the next participant.

The goal is to remove this repetitive manual work while keeping Google Sheets as the authoritative source of input data.

---

# 3. Product Goals

## 3.1 Primary Goals

The automation must:

- Read participant data from Google Sheets.
- Process multiple participants automatically.
- Support all three assessment types.
- Enter answers into Frexor automatically.
- Submit assessments automatically.
- Detect and verify generated PDF results.
- Track processing status.
- Prevent already-completed participants from being processed again unintentionally.
- Support safe recovery after failures.
- Provide sufficient logging for troubleshooting.

## 3.2 Secondary Goals

The system should:

- Provide visible batch progress.
- Provide meaningful error messages.
- Allow an interrupted batch to resume.
- Keep the automation deterministic and auditable.
- Avoid unnecessary modifications to the existing Frexor application.

---

# 4. Non-Goals / Out of Scope

The following are explicitly outside the scope of this project:

- Scanning physical answer sheets.
- OCR/OMR processing.
- Interpreting handwritten answers.
- Determining or changing participant answers.
- Calculating DISC, VAK, or IQ scores independently.
- Reproducing Frexor's scoring algorithm.
- Modifying Frexor's internal database.
- Reverse engineering or modifying the Frexor executable unless strictly necessary for UI automation.
- Building a replacement assessment platform.
- Generating assessment questions.
- Automatically deciding which answers a participant should have selected.

The automation is an **input and workflow automation layer** only.

---

# 5. High-Level Architecture

```text
Physical Answer Sheet
        |
        | (external scanning process)
        v
Google Sheets
        |
        v
+-------------------------+
| Automation Application  |
|                         |
| - Sheet Reader          |
| - Data Validator        |
| - Batch Orchestrator    |
| - Frexor Automation     |
| - PDF Verifier          |
| - Status Manager        |
| - Logging               |
+------------+------------+
             |
             v
      Frexor Psychology
      Assessment System
             |
             v
      Generated PDF Result
             |
             v
       Output / Archive
```

Google Sheets is the authoritative input source.

Frexor is the target application.

The automation layer coordinates the workflow between them.

---

# 6. Assessment Types

## 6.1 DISC — Attitude Test

### Input Model

Each question has exactly two answer fields:

- Mirip
- Tidak Mirip

Example:

```text
Question 1
Mirip       = A
Tidak Mirip = C
```

Conceptual data:

```json
{
  "type": "DISC",
  "question": 1,
  "mirip": "A",
  "tidak_mirip": "C"
}
```

The automation must enter both answers.

---

## 6.2 VAK — Working Style Test

### Input Model

Each question has exactly one answer.

Example:

```text
Question 1
Answer = B
```

Conceptual data:

```json
{
  "type": "VAK",
  "question": 1,
  "answer": "B"
}
```

The automation must select the specified choice.

---

## 6.3 IQ — Aptitude Test

### Input Model

Each question has exactly one answer.

Example:

```text
Question 1
Answer = C
```

Conceptual data:

```json
{
  "type": "IQ",
  "question": 1,
  "answer": "C"
}
```

The automation must select the specified choice.

---

# 7. Google Sheets Data Model

The exact sheet layout may be adapted to the existing implementation, but the logical data model must support:

- participant identity,
- assessment answers,
- per-assessment status,
- overall status,
- error information,
- PDF information.

A recommended logical structure is:

## 7.1 Participants

| Field | Description |
|---|---|
| participant_id | Unique participant identifier |
| name | Participant name |
| status | Overall processing state |
| disc_status | DISC processing state |
| vak_status | VAK processing state |
| iq_status | IQ processing state |
| pdf_status | Result PDF state |
| pdf_path | Output PDF path if available |
| error_code | Machine-readable error |
| error_message | Human-readable error |
| updated_at | Last update timestamp |

## 7.2 DISC Answers

| Field | Description |
|---|---|
| participant_id | Participant identifier |
| question_no | Question number |
| mirip | Mirip answer |
| tidak_mirip | Tidak Mirip answer |

## 7.3 VAK Answers

| Field | Description |
|---|---|
| participant_id | Participant identifier |
| question_no | Question number |
| answer | Selected answer |

## 7.4 IQ Answers

| Field | Description |
|---|---|
| participant_id | Participant identifier |
| question_no | Question number |
| answer | Selected answer |

The implementation may use a different physical spreadsheet layout if the same logical information can be reconstructed reliably.

---

# 8. Processing States

The automation must maintain explicit states.

## 8.1 Participant-Level States

Minimum required states:

```text
READY
PROCESSING
DONE
ERROR
```

Optional internal states may be used.

## 8.2 Assessment-Level States

For DISC, VAK, and IQ independently:

```text
READY
PROCESSING
DONE
ERROR
```

This is important because one assessment may succeed while another fails.

Example:

```text
Participant 001

DISC = DONE
VAK  = ERROR
IQ   = READY
Overall = ERROR
```

On retry, DISC must not be reprocessed unnecessarily.

---

# 9. State Machine

A successful participant lifecycle should be conceptually:

```text
READY
  |
  v
PROCESSING
  |
  v
DATA_VALIDATED
  |
  v
DISC_COMPLETED
  |
  v
VAK_COMPLETED
  |
  v
IQ_COMPLETED
  |
  v
SUBMITTED
  |
  v
WAITING_FOR_PDF
  |
  v
PDF_VERIFIED
  |
  v
DONE
```

At any failure point:

```text
PROCESSING
    |
    v
  ERROR
```

The implementation may use different internal states, but externally observable status must remain clear.

---

# 10. Batch Processing

Batch processing is a core requirement.

If Google Sheets contains 60 eligible participants:

```text
001 READY
002 READY
003 READY
...
060 READY
```

The operator should only need to start the automation once.

The system must process:

```text
001 -> process -> submit -> PDF -> DONE
002 -> process -> submit -> PDF -> DONE
003 -> process -> submit -> PDF -> DONE
...
060 -> process -> submit -> PDF -> DONE
```

The operator must not have to manually press `Start`, `Kirim`, or navigate between participants for each participant.

---

# 11. Eligibility Rules

A participant is eligible for normal batch processing when:

- required participant identity exists;
- required assessment answers are present;
- participant is not already `DONE`;
- participant does not have a locked/finalized state;
- the data passes validation.

Normally:

```text
READY -> eligible
DONE  -> skip
ERROR -> retry only when explicitly allowed
```

The implementation should not silently process an already completed participant.

---

# 12. Single-Participant Processing Workflow

For each participant, the automation must execute the following sequence.

## Step 1 — Load Participant

Read the participant and all required answers from Google Sheets.

## Step 2 — Validate

Check:

- participant identity;
- required answers;
- answer format;
- question count;
- missing values;
- unexpected values.

Do not start Frexor data entry if required input is invalid.

## Step 3 — Prepare Frexor

Ensure Frexor is:

- running,
- accessible,
- in the correct workflow,
- not blocked by a previous participant,
- ready for new input.

## Step 4 — Process DISC

Enter all required `Mirip` and `Tidak Mirip` answers.

## Step 5 — Process VAK

Enter all required single-choice answers.

## Step 6 — Process IQ

Enter all required single-choice answers.

## Step 7 — Input Verification

Before submission, verify that the intended values were entered where possible.

## Step 8 — Submit

Automatically activate the Frexor `Kirim` / Submit action.

## Step 9 — Wait

Wait for Frexor to finish processing.

## Step 10 — Detect PDF

Detect the PDF generated by Frexor.

## Step 11 — Verify PDF

Confirm:

- file exists;
- file size is greater than zero;
- file is readable/accesssible;
- the file appeared or changed as a result of the current submission;
- where technically possible, the file corresponds to the current participant.

## Step 12 — Finalize

Only after PDF verification succeeds:

```text
participant.status = DONE
```

## Step 13 — Continue

Move to the next eligible participant.

---

# 13. Submit Behavior

The automation MUST automatically trigger the Frexor submit action.

The implementation must not require the operator to manually press the `Kirim` button for every participant.

However:

> Clicking `Kirim` is an intermediate action, not the completion condition.

The system must wait for and verify the resulting PDF before declaring success.

---

# 14. PDF Generation and Verification

PDF generation is a required output of the system.

After clicking `Kirim`:

```text
Submit
  |
  v
Wait
  |
  v
PDF detected?
  |            |
 NO           YES
  |            |
ERROR      Validate PDF
               |
               v
           PDF valid?
            |      |
           NO     YES
            |      |
          ERROR   DONE
```

## 14.1 PDF Validation

At minimum:

- file exists;
- extension is `.pdf`;
- file size > 0;
- file can be opened/read;
- file is newly generated or otherwise verifiably associated with the current submission.

If technically feasible, also verify that the PDF content or metadata corresponds to the current participant.

---

# 15. PDF Association

Every successful participant must have a known PDF result.

The automation must maintain:

```text
participant_id -> PDF path
```

Example:

```text
001 -> C:\Frexor\Results\001_Andi.pdf
002 -> C:\Frexor\Results\002_Budi.pdf
```

If Frexor generates generic filenames such as:

```text
result_12345.pdf
result_12346.pdf
```

the automation must create a reliable mapping to the participant.

Never infer ownership solely from directory ordering.

---

# 16. PDF Output Management

Recommended output structure:

```text
output/
├── 001_Andi/
│   └── assessment.pdf
├── 002_Budi/
│   └── assessment.pdf
└── 003_Citra/
    └── assessment.pdf
```

The exact directory structure can be adapted to the current implementation.

Requirements:

- do not overwrite another participant's result;
- avoid filename collisions;
- preserve existing results;
- use deterministic naming where possible.

---

# 17. Google Sheets Status Updates

The automation must update Google Sheets at meaningful checkpoints.

Example:

```text
READY
  ↓
PROCESSING
  ↓
SUBMITTED
  ↓
WAITING_FOR_PDF
  ↓
DONE
```

A minimal implementation may expose only:

```text
READY
PROCESSING
DONE
ERROR
```

while recording more detailed state in logs.

## 17.1 Required Output Fields

At minimum, the system should expose:

- overall status;
- DISC status;
- VAK status;
- IQ status;
- PDF status/path;
- error code;
- error message;
- last updated timestamp.

---

# 18. Error Handling

The automation must fail safely.

Potential errors include:

```text
FREXOR_NOT_FOUND
FREXOR_NOT_READY
FREXOR_NOT_RESPONDING
INPUT_FIELD_NOT_FOUND
INVALID_INPUT_DATA
MISSING_ANSWER
DISC_INPUT_FAILED
VAK_INPUT_FAILED
IQ_INPUT_FAILED
SUBMIT_FAILED
PDF_TIMEOUT
PDF_NOT_FOUND
PDF_INVALID
PDF_ASSOCIATION_FAILED
GOOGLE_SHEETS_READ_FAILED
GOOGLE_SHEETS_UPDATE_FAILED
```

The implementation may define additional error codes.

Errors must be logged with enough context to diagnose the failure.

---

# 19. Stop-on-Error Policy

Default behavior should be conservative:

```text
Participant 001 -> DONE
Participant 002 -> DONE
Participant 003 -> ERROR
                         |
                         v
                        STOP
```

Do not immediately continue if the Frexor UI may be in an unknown state.

The implementation may support a configurable option such as:

```text
STOP_ON_ERROR = true
```

Any automatic continue-after-error behavior must be explicitly configurable and safe.

---

# 20. Resume Behavior

The system must support resuming a partially completed batch.

Example:

```text
001 -> DONE
002 -> DONE
003 -> ERROR
004 -> READY
...
060 -> READY
```

After fixing the issue:

```text
001 -> SKIP
002 -> SKIP
003 -> PROCESS
004 -> PROCESS
...
060 -> PROCESS
```

Already completed participants must not be processed again by default.

---

# 21. Per-Assessment Resume

If supported by the Frexor workflow, an individual assessment should be resumable independently.

Example:

```text
Participant 003

DISC = DONE
VAK  = ERROR
IQ   = READY
```

Retry should not repeat DISC unless the application requires the entire participant workflow to be restarted.

If Frexor technically forces the entire assessment workflow to restart, the implementation must handle that safely and document the behavior.

---

# 22. Idempotency and Duplicate Prevention

The system must prevent accidental duplicate processing.

A participant with:

```text
status = DONE
pdf_status = VERIFIED
```

must be skipped during normal batch execution.

Reprocessing should require an explicit operator action.

This is particularly important because reprocessing may generate a second PDF result.

---

# 23. Progress UI

The automation should provide visible progress.

Minimum information:

```text
Total participants : 60
Processed          : 23
Success            : 22
Error              : 1

Current:
ID   : 024
Name : Budi

DISC : DONE
VAK  : DONE
IQ   : PROCESSING
PDF  : WAITING
```

The UI does not need to be complex.

A simple status window is sufficient for MVP.

---

# 24. Batch Completion Summary

At the end of a batch, display a summary such as:

```text
Batch Complete

Total     : 60
Success   : 58
Error     : 2
Skipped   : 0
```

The application should also identify failed participants.

Example:

```text
Failed Participants:

003 - Citra - PDF_NOT_FOUND
027 - Dimas - SUBMIT_FAILED
```

---

# 25. Logging

The automation must maintain an execution log.

Example:

```text
10:21:04 | START | Participant 001 | Andi
10:21:05 | VALID | Input valid
10:21:07 | DISC | Completed
10:21:09 | VAK  | Completed
10:21:11 | IQ   | Completed
10:21:12 | SUBMIT | Clicked
10:21:13 | PDF | Waiting
10:21:16 | PDF | Found result_12345.pdf
10:21:17 | PDF | Verified
10:21:18 | DONE | Participant 001
```

Error example:

```text
10:35:22 | PARTICIPANT | 021 | Budi
10:35:24 | SUBMIT | Clicked
10:35:40 | PDF | Timeout
10:35:40 | ERROR | PDF_TIMEOUT
```

Logs should be persisted outside the UI where practical.

---

# 26. Frexor UI Automation

The exact automation mechanism must be determined through technical discovery.

Possible approaches include:

1. Windows UI Automation / Accessibility APIs
2. `pywinauto`
3. AutoHotkey
4. Other appropriate Windows automation mechanisms

Do not assume the implementation technology before inspecting the actual Frexor executable.

The developer must inspect:

- application window hierarchy;
- controls;
- text fields;
- buttons;
- radio buttons or selection controls;
- navigation behavior;
- result/PDF generation behavior;
- possible dialogs;
- download/save dialogs;
- application state transitions.

Do not rely on hard-coded screen coordinates unless no robust alternative is available.

---

# 27. Frexor Discovery Requirement

Before modifying production automation, perform a technical discovery pass against the actual Frexor application.

The developer must determine:

- how Frexor starts;
- how a participant is selected or created;
- how each assessment is opened;
- how answer fields are exposed;
- how `Kirim` works;
- whether submit opens a dialog;
- where PDFs are generated;
- whether PDF generation is asynchronous;
- how to detect completion;
- how to return to the state required for the next participant.

The discovery results should be documented in the codebase or technical notes.

Do not invent UI selectors, control names, window titles, or PDF paths.

---

# 28. Security Requirements

The implementation must:

- keep Google credentials out of source code;
- avoid hardcoding secrets;
- use secure credential storage where practical;
- limit Google Sheets access to required scopes;
- avoid putting sensitive participant information into unnecessary logs;
- protect generated assessment PDFs;
- avoid exposing assessment results to unauthorized users.

---

# 29. Operational Assumptions

The first version assumes:

- Windows is available to run Frexor.
- Frexor can be launched and interacted with by the automation process.
- The machine has access to Google Sheets.
- Required Google credentials are configured.
- Participant answers are already present in Google Sheets.
- The scan/answer extraction process has already been completed.
- Frexor's PDF generation is available when `Kirim` succeeds.

---

# 30. MVP Requirements

The MVP is complete when it can perform this workflow:

```text
Google Sheets
     |
     v
Load participant
     |
     v
Validate data
     |
     v
Open / prepare Frexor
     |
     v
Fill DISC
     |
     v
Fill VAK
     |
     v
Fill IQ
     |
     v
Click Kirim
     |
     v
Wait for PDF
     |
     v
Verify PDF
     |
     v
Update Sheet = DONE
     |
     v
Next participant
```

The operator should only need to initiate the batch and intervene when a genuine error occurs.

---

# 31. Acceptance Criteria

## AC-01 — Batch Processing

Given 60 valid `READY` participants,

when the operator starts the automation,

then the system attempts to process all eligible participants automatically.

## AC-02 — No Manual Submit

The operator must not need to press the Frexor `Kirim` button manually for each participant.

## AC-03 — PDF Required for Success

A participant must not be marked `DONE` unless a valid result PDF has been detected and verified.

## AC-04 — PDF Association

Every `DONE` participant must have an associated PDF path/reference.

## AC-05 — Duplicate Prevention

A participant already marked `DONE` must be skipped during normal batch execution.

## AC-06 — Resume

After a failure, completed participants must not be reprocessed unnecessarily.

## AC-07 — Error Visibility

A failed participant must have a meaningful error status and message.

## AC-08 — Safe Failure

If Frexor enters an unknown or unsafe UI state, the system should stop rather than blindly continue.

## AC-09 — Progress

The operator can see which participant is currently being processed and overall batch progress.

## AC-10 — Final Summary

At batch completion or stop, the application displays counts for:

- total;
- success;
- failed;
- skipped.

---

# 32. Example End-to-End Scenario

Assume 60 participants exist:

```text
001 - Andi
002 - Budi
003 - Citra
...
060 - Zaki
```

Operator starts automation.

System performs:

```text
001
├── DISC
├── VAK
├── IQ
├── Submit
├── PDF generated
├── PDF verified
└── DONE

002
├── DISC
├── VAK
├── IQ
├── Submit
├── PDF generated
├── PDF verified
└── DONE

...

037
├── DISC
├── VAK
├── IQ
├── Submit
└── PDF timeout
    └── ERROR + STOP
```

After fixing the issue and resuming:

```text
001-036 -> SKIP
037      -> PROCESS
038-060  -> PROCESS
```

The system continues until all participants are either:

- `DONE`, or
- explicitly left in `ERROR`.

---

# 33. Important Implementation Principles

## Principle 1 — Do Not Overwrite the Existing Working Implementation

The current implementation has already been developed from the previous PRD.

Implement this document as an incremental enhancement unless a redesign is technically necessary.

## Principle 2 — PDF Is a First-Class Output

The PDF is not merely a side effect of submission.

It is part of the success criteria.

## Principle 3 — Google Sheets Remains the Source of Truth

The automation should not create unnecessary duplicate data stores.

## Principle 4 — Frexor Remains the Assessment Engine

The automation must not calculate or modify assessment results.

## Principle 5 — Never Guess UI Behavior

Use actual inspection of Frexor rather than assumptions.

## Principle 6 — Fail Safely

When the automation cannot determine whether a participant was correctly submitted and whether the corresponding PDF was generated, do not silently continue.

---

# 34. Deliverables Expected from Codex

Codex should produce:

1. Updated automation implementation.
2. Google Sheets integration updates.
3. Batch processing/orchestration.
4. Frexor automated submission.
5. PDF detection and verification.
6. Participant-to-PDF mapping.
7. Status management.
8. Resume/retry behavior.
9. Error handling.
10. Logging.
11. Basic progress UI.
12. Automated/manual test coverage where practical.
13. Documentation for running the automation.

---

# 35. Definition of Done

The feature is considered complete when:

- an operator can start a batch;
- multiple participants can be processed automatically;
- DISC answers are entered correctly;
- VAK answers are entered correctly;
- IQ answers are entered correctly;
- `Kirim` is triggered automatically;
- the generated PDF is detected;
- the PDF is verified;
- participant status is updated;
- completed participants are not accidentally duplicated;
- the batch can resume after failure;
- errors are visible and diagnosable;
- the operator can determine the final status of every participant.

---

# 36. Final Product Behavior

The intended operator experience is:

```text
1. Ensure Google Sheets contains validated participant data.
2. Open the automation application.
3. Start batch processing.
4. Automation processes participants automatically.
5. Automation enters all answers.
6. Automation presses Kirim.
7. Frexor generates PDF.
8. Automation verifies PDF.
9. Automation marks participant DONE.
10. Automation continues to the next participant.
11. Operator intervenes only when an error requires attention.
```

The desired end state is:

> **For a batch of 60 participants, the operator performs one batch-start action, while the system handles data entry, submission, PDF generation verification, status tracking, and progression through all participants automatically.**
