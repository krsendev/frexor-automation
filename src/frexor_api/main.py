from collections import Counter
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from datetime import date, datetime, timedelta, timezone
from typing import Annotated, Literal, Self
from uuid import uuid4

from fastapi import (
  Depends,
  FastAPI,
  Header,
  HTTPException,
  Response,
  status,
)
from pydantic import BaseModel, Field, model_validator

from .database import connect, initializeDatabase, transaction
from .security import requireWebhookToken, requireWorkerToken

@asynccontextmanager
async def lifespan(
  app: FastAPI,
) -> AsyncIterator[None]:
  print("Memeriksa database...")
  initializeDatabase()
  print("Database siap!")
  yield
  print("FastAPI berhenti")

app = FastAPI(
  title="Frexor Automation API",
  version="0.1.0",
  lifespan=lifespan,
)

def utcNow() -> str:
  return datetime.now(
    timezone.utc
  ).isoformat()

class discAnswer(BaseModel):
  question_no: int = Field(ge=1, le=24)
  mirip: Literal["A", "B", "C", "D"]
  tidak_mirip: Literal["A", "B", "C", "D"]

  @model_validator(mode="after")
  def answerMustBeDifferent(self) -> Self:
    if self.mirip == self.tidak_mirip:
      raise ValueError(
        "Jawaban harus berbeda pada setiap nomor pertanyaan"
      )
    return self

class vakAnswer(BaseModel):
  question_no: int = Field(ge=1, le=30)
  answer: Literal["A", "B", "C"]

class iqAnswer(BaseModel):
  question_no: int = Field(ge=1, le=60)
  answer: str = Field(min_length=1, max_length=1)

  @model_validator(mode="after")
  def answerMustBeAllowed(self) -> Self:
    if self.question_no in {12, 24, 44, 56}:
      allowedAnswers = set("ABC")
    elif self.question_no in {15, 54}:
      allowedAnswers = set("ABCDEFGH")
    else:
      allowedAnswers = set("ABCDE")

    if self.answer not in allowedAnswers:
      raise ValueError(
        f"Jawaban IQ nomor {self.question_no} harus salah satu dari {sorted(allowedAnswers)}"
      )
    return self

def validateQuestionNumbers(
  module: str,
  answers: list,
  expectedCount: int,
) -> None:
  numbers = [answer.question_no for answer in answers]
  counts = Counter(numbers)
  expected = set(range(1, expectedCount + 1))
  actual = set(numbers)
  missing = sorted(expected - actual)
  unexpected = sorted(actual - expected)
  duplicates = sorted(
    number
    for number, count in counts.items()
    if count > 1
  )

  errors = []
  if missing:
    errors.append(f"nomor yang hilang: {missing}")
  if unexpected:
    errors.append(f"nomor tidak dikenal: {unexpected}")
  if duplicates:
    errors.append(f"nomor duplikat: {duplicates}")
  if errors:
    raise ValueError(
      f"{module} tidak lengkap: {', '.join(errors)}"
    )

class AssessmentAnswers(BaseModel):
  disc: list[discAnswer] = Field(
    min_length=24, max_length=24,
  )
  vak: list[vakAnswer] = Field(
    min_length=30, max_length=30,
  )
  iq: list[iqAnswer] = Field(
    min_length=60, max_length=60,
  )

  @model_validator(mode="after")
  def questionNumberMustBeComplete(self) -> Self:
    validateQuestionNumbers("DISC", self.disc, 24)
    validateQuestionNumbers("VAK", self.vak, 30)
    validateQuestionNumbers("IQ", self.iq, 60)
    return self

class AssessmentRequest(BaseModel):
  external_id: str = Field(min_length=1, max_length=100)
  name: str = Field(min_length=1, max_length=20)
  position: str = Field(min_length=1, max_length=20)
  test_date: date
  answers: AssessmentAnswers

class WorkerClaimRequest(BaseModel):
  worker_id: str = Field(
    min_length=1,
    max_length=100,
  )

class ModuleStatusUpdate(BaseModel):
  status: Literal[
    "PROCESSING",
    "DONE",
    "ERROR",
  ]

  error_code: str = Field(
    default="",
    max_length=100,
  )

  error_message: str = Field(
    default="",
    max_length=500,
  )

  pdf_path: str = Field(
    default="",
    max_length=500,
  )

  @model_validator(mode="after")
  def validateErrorDetail(self) -> Self:
    if self.status == "ERROR":
      if not self.error_code.strip():
        raise ValueError(
          "error_code wajib diisi ketika status ERROR"
        )

      if not self.error_message.strip():
        raise ValueError(
          "error_message wajib diisi ketika status ERROR"
        )
    return self

def saveAssessment(
  payload: AssessmentRequest,
) -> tuple[str, bool]:
    now = utcNow()

    with transaction() as connection:
      existingJob = connection.execute(
        """
        SELECT id
        FROM jobs
        WHERE external_id = ?
        """,
        (
          payload.external_id,
        ),
      ).fetchone()

      if existingJob is not None:
        return existingJob["id"], False

      jobId = str(uuid4())

      connection.execute(
        """
        INSERT INTO jobs (
          id,
          external_id,
          name,
          position,
          test_date,
          status,
          created_at,
          updated_at
        ) VALUES (
          ?, ?, ?, ?, ?, 'QUEUED', ?, ?
        )
        """,
        (
          jobId,
          payload.external_id,
          payload.name,
          payload.position,
          payload.test_date.isoformat(),
          now,
          now,
        ),
      )

      for module in ("DISC","VAK","IQ"):
        connection.execute(
          """
          INSERT INTO module_runs (
            job_id,
            module,
            status,
            updated_at
          ) VALUES (
            ?, ?, 'PENDING', ?
          )
          """,
          (
            jobId,
            module,
            now,
          ),
        )

      for answer in payload.answers.disc:
        connection.execute(
          """
          INSERT INTO answers (
            job_id,
            module,
            question_no,
            mirip,
            tidak_mirip
          ) VALUES (
            ?, 'DISC', ?, ?, ?
          )
          """,
          (
            jobId,
            answer.question_no,
            answer.mirip,
            answer.tidak_mirip,
          ),
        )

      for answer in payload.answers.vak:
        connection.execute(
          """
          INSERT INTO answers (
            job_id,
            module,
            question_no,
            answer
          ) VALUES (
            ?, 'VAK', ?, ?
          )
          """,
          (
            jobId,
            answer.question_no,
            answer.answer,
          ),
        )

      for answer in payload.answers.iq:
        connection.execute(
          """
          INSERT INTO answers (
            job_id,
            module,
            question_no,
            answer
          ) VALUES (
            ?, 'IQ', ?, ?
          )
          """,
          (
            jobId,
            answer.question_no,
            answer.answer,
          ),
        )
      return jobId, True

def getJobStatus(
  jobId: str,
) -> dict:
  connection = connect()

  try:
    job = connection.execute(
      """
      SELECT
        id,
        external_id,
        status,
        attempt_count,
        error_code,
        last_error,
        created_at,
        updated_at
      FROM jobs
      WHERE id = ?
      """,
      (
        jobId,
      ),
    ).fetchone()

    if job is None:
      raise HTTPException(
        status_code=(
          status.HTTP_404_NOT_FOUND
        ),
        detail="Job tidak ditemukan",
      )
    moduleRows = connection.execute(
      """
      SELECT
        module,
        status,
        attempt_count,
        error_code,
        error_message,
        updated_at
      FROM module_runs
      WHERE job_id = ?
      ORDER BY
        CASE module
          WHEN 'DISC' THEN 1
          WHEN 'VAK' THEN 2
          WHEN 'IQ' THEN 3
        END
      """,
      (
        jobId,
      )
    ).fetchall()

    modules = {
      row["module"]: {
        "status": row["status"],
        "attempt_count": (
          row["attempt_count"]
        ),
        "error_code": row["error_code"],
        "error_message": (
          row["error_message"]
        ),
        "updated_at": row["updated_at"],
      }
      for row in moduleRows
    }
    return {
      "job_id": job["id"],
      "external_id": job["external_id"],
      "status": job["status"],
      "attempt_count": (
        job["attempt_count"]
      ),
      "error_code": job["error_code"],
      "error_message": job["last_error"],
      "created_at": job["created_at"],
      "updated_at": job["updated_at"],
      "modules": modules,
    }
  finally:
    connection.close()

def recoverExpiredJobs() -> dict:
  now = utcNow()

  with transaction() as connection:
    claimedResult = connection.execute(
      """
      UPDATE jobs
      SET
        status = 'QUEUED',
        worker_id = NULL,
        lease_until = NULL,
        error_code = '',
        last_error = '',
        updated_at = ?
      WHERE
        status = 'CLAIMED'
        AND lease_until IS NOT NULL
        AND lease_until <= ?
      """,
      (now, now)
    )

    processingResult = connection.execute(
      """
      UPDATE jobs
      SET
        status = 'REVIEW_REQUIRED',
        worker_id = NULL,
        lease_until = NULL,
        error_code = 'LEASE_EXPIRED',
        last_error = ?,
        updated_at = ?
      WHERE
        status = 'PROCESSING'
        AND lease_until IS NOT NULL
        AND lease_until <= ?
      """,
      (
        (
          "Lease berakhir ketika automation sedang memproses assessment"
        ),
        now, now
      )
    )

    return{
      "requeued": claimedResult.rowcount,
      "review_required": processingResult.rowcount
    }

def claimJob(
  workerId: str,
) -> dict | None:
    now = datetime.now(timezone.utc)

    leaseUntil = (
      now + timedelta(minutes=30)
    )
    with transaction() as connection:
      job = connection.execute(
        """
        SELECT
          id,
          external_id,
          name,
          position,
          test_date,
          status,
          attempt_count
        FROM jobs
        WHERE status = 'QUEUED'
        ORDER BY created_at
        LIMIT 1
        """
      ).fetchone()

      if job is None:
        return None

      result = connection.execute(
        """
        UPDATE jobs
        SET
          status = 'CLAIMED',
          worker_id = ?,
          lease_until = ?,
          attempt_count = (
            attempt_count + 1
          ),
          updated_at = ?
        WHERE
          id = ?
          AND status = 'QUEUED'
        """,
        (
          workerId,
          leaseUntil.isoformat(),
          now.isoformat(),
          job["id"],
        ),
      )

      if result.rowcount != 1:
        return None

      moduleRows = connection.execute(
        """
        SELECT module, status, pdf_path
        FROM module_runs
        WHERE job_id = ?
        ORDER BY CASE module
          WHEN 'DISC' THEN 1
          WHEN 'VAK' THEN 2
          WHEN 'IQ' THEN 3
        END
        """,
        (job["id"],),
      ).fetchall()

      return {
        "job_id": job["id"],
        "external_id": job["external_id"],
        "name": job["name"],
        "position": job["position"],
        "test_date": job["test_date"],
        "status": "CLAIMED",
        "worker_id": workerId,
        "lease_until": (
          leaseUntil.isoformat()
        ),
        "attempt_count": (
          job["attempt_count"] + 1
        ),
        "modules": {
          row["module"]: {
            "status": row["status"],
            "pdf_path": row["pdf_path"],
          }
          for row in moduleRows
        },
      }

def getWorkerAnswers(
  jobId: str,
  module: str,
  workerId: str,
) -> dict:
    normalizedModule = module.upper()
    allowedModules = {
      "DISC",
      "VAK",
      "IQ",
    }

    if normalizedModule not in allowedModules:
      raise HTTPException(
        status_code=(
          status.HTTP_400_BAD_REQUEST
        ),
        detail="Module harus DISC, VAK, atau IQ",
      )

    connection = connect()
    try:
      job = connection.execute(
        """
        SELECT
          id,
          worker_id,
          status
        FROM jobs
        WHERE id = ?
        """,
        (
          jobId,
        ),
      ).fetchone()

      if job is None:
        raise HTTPException(
          status_code=(
            status.HTTP_404_NOT_FOUND
          ),
          detail="Job tidak ditemukan",
        )

      if job["worker_id"] != workerId:
        raise HTTPException(
          status_code=(
            status.HTTP_409_CONFLICT
          ),
          detail=(
            "Job telah diklaim oleh worker lain"
          ),
        )

      if job["status"] not in {
        "CLAIMED",
        "PROCESSING",
      }:
        raise HTTPException(
          status_code=(
            status.HTTP_409_CONFLICT
          ),
          detail=(
            "Status job tidak mengizinkan pengambilan jawaban"
          ),
        )

      rows = connection.execute(
        """
        SELECT
          question_no,
          answer,
          mirip,
          tidak_mirip
        FROM answers
        WHERE
          job_id = ?
          AND module = ?
        ORDER BY question_no
        """,
        (
          jobId,
          normalizedModule,
        ),
      ).fetchall()

      if normalizedModule == "DISC":
        answers = [
          {
            "question_no": row["question_no"],
            "mirip": row["mirip"],
            "tidak_mirip": row["tidak_mirip"],
          }
          for row in rows
        ]
      else:
        answers = [
          {
            "question_no": row["question_no"],
            "answer": row["answer"],
          }
          for row in rows
        ]

      return {
        "job_id": jobId,
        "module": normalizedModule,
        "count": len(answers),
        "answers": answers,
      }
    finally:
      connection.close()

def updateModuleStatus(
  jobId: str,
  module: str,
  workerId: str,
  payload: ModuleStatusUpdate,
) -> dict:
  normalizeModule = module.upper()
  allowedModules = {
    "DISC", "VAK", "IQ"
  }

  if normalizeModule not in allowedModules:
    raise HTTPException(
      status_code=(
        status.HTTP_400_BAD_REQUEST
      ),
      detail="Module harus DISC, VAK, atau IQ",
    )

  allowedTransitions = {
    "PENDING": {
      "PROCESSING", "ERROR"
    },
    "PROCESSING": {
      "DONE", "ERROR"
    },
    "ERROR": {
      "PROCESSING"
    },
    "DONE": set(),
  }

  now = utcNow()

  with transaction() as connection:
    job = connection.execute(
      """
      SELECT
        id,
        worker_id,
        status
      FROM jobs
      WHERE id = ?
      """,
      (
        jobId,
      ),
    ).fetchone()

    if job is None:
      raise HTTPException(
        status_code=(
          status.HTTP_404_NOT_FOUND
        ),
        detail="Job tidak ditemukan"
      )

    if job["worker_id"] != workerId:
      raise HTTPException(
        status_code=(
          status.HTTP_409_CONFLICT
        ),
        detail=(
          "Job diklaim oleh worker lain"
        ),
      )

    if job["status"] not in {
      "CLAIMED",
      "PROCESSING",
      "FAILED",
    }:
      raise HTTPException(
        status_code=(
          status.HTTP_409_CONFLICT
        ),
        detail=(
          "Status job tidak mengizinkan perubahan modul"
        ),
      )

    moduleRow = connection.execute(
      """
      SELECT
        status,
        attempt_count
      FROM module_runs
      WHERE
        job_id = ?
        AND module = ?
      """,
      (
        jobId,
        normalizeModule,
      )
    ).fetchone()

    if moduleRow is None:
      raise HTTPException(
        status_code=(
          status.HTTP_404_NOT_FOUND
        ),
        detail="Status modul tidak ditemukan",
      )

    currentStatus = moduleRow["status"]
    requestedStatus = payload.status

    if currentStatus == requestedStatus:
      return {
        "job_id": jobId,
        "module": normalizeModule,
        "status": currentStatus,
        "job_status": job["status"],
        "idempotent": True,
      }

    allowed = allowedTransitions.get(
      currentStatus,
      set(),
    )

    if requestedStatus not in allowed:
      raise HTTPException(
        status_code=(
          status.HTTP_409_CONFLICT
        ),
        detail=(
          f"Transisi {currentStatus} ke {requestedStatus} tidak diperbolehkan"
        ),
      )

    attemptIncrement = (
      1
      if requestedStatus == "PROCESSING"
      else 0
    )

    errorCode = (
      payload.error_code.strip()
      if requestedStatus == "ERROR"
      else ""
    )

    errorMessage = (
      payload.error_message.strip()
      if requestedStatus == "ERROR"
      else ""
    )

    pdfPath = (
      payload.pdf_path.strip()
      if requestedStatus == "DONE"
      else ""
    )

    connection.execute(
      """
      UPDATE module_runs
      SET
        status = ?,
        attempt_count = attempt_count + ?,
        error_code = ?,
        error_message = ?,
        pdf_path = CASE
          WHEN ? <> ''
          THEN ?
          ELSE pdf_path
        END,
        updated_at = ?
      WHERE
        job_id = ?
        AND module = ?
      """,
      (
        requestedStatus,
        attemptIncrement,
        errorCode,
        errorMessage,
        pdfPath,
        pdfPath,
        now,
        jobId,
        normalizeModule,
      ),
    )

    moduleStatuses = connection.execute(
      """
      SELECT status
      FROM module_runs
      WHERE job_id = ?
      """,
      (
        jobId,
      ),
    ).fetchall()

    statusValues = {
      row["status"]
      for row in moduleStatuses
    }

    if "ERROR" in statusValues:
      jobStatus = "FAILED"
    elif statusValues == {"DONE"}:
      jobStatus = "DONE"
    elif (
      "PROCESSING" in statusValues
      or "DONE" in statusValues
    ):
      jobStatus = "PROCESSING"
    else:
      jobStatus = "CLAIMED"

    connection.execute(
      """
      UPDATE jobs
      SET
        status = ?,
        error_code = ?,
        last_error = ?,
        pdf_path = CASE
          WHEN ? <> ''
          THEN ?
          ELSE pdf_path
        END,
        lease_until = CASE
          WHEN ? IN ('DONE', 'FAILED')
          THEN NULL
          ELSE lease_until
        END,
        updated_at = ?
      WHERE id = ?
      """,
      (
        jobStatus,
        errorCode,
        errorMessage,
        pdfPath,
        pdfPath,
        jobStatus,
        now,
        jobId,
      ),
    )

    return {
      "job_id": jobId,
      "module": normalizeModule,
      "status": requestedStatus,
      "job_status": jobStatus,
      "idempotent": False,
    }

def heartbeatJob(
  jobId: str,
  workerId: str,
) -> dict:
  now = datetime.now(timezone.utc)

  newLeaseUntil = (
    now + timedelta(minutes=30)
  )

  with transaction() as connection:
    job = connection.execute(
      """
      SELECT
        id,
        worker_id,
        status,
        lease_until
      FROM jobs
      WHERE id = ?
      """,
      (
        jobId,
      ),
    ).fetchone()

    if job is None:
      raise HTTPException(
        status_code=(
          status.HTTP_404_NOT_FOUND
        ),
        detail="Job tidak ditemukan",
      )

    if job["worker_id"] != workerId:
      raise HTTPException(
        status_code=(
          status.HTTP_409_CONFLICT
        ),
        detail="Job dimiliki worker lain"
      )

    if job["status"] not in {
      "CLAIMED",
      "PROCESSING",
    }:
      raise HTTPException(
        status_code=status.HTTP_409_CONFLICT,
        detail="Job sedang tidak aktif",
      )

    if not job["lease_until"]:
      raise HTTPException(
        status_code=status.HTTP_409_CONFLICT,
        detail="Job tidak memiliki lease",
      )

    currentLeaseUntil = datetime.fromisoformat(
      job["lease_until"]
    )

    if currentLeaseUntil <= now:
      raise HTTPException(
        status_code=status.HTTP_409_CONFLICT,
        detail="Lease job sudah kadaluwarsa",
      )

    connection.execute(
      """
      UPDATE jobs
      SET
        lease_until = ?,
        updated_at = ?
      WHERE id = ?
      """,
      (
        newLeaseUntil.isoformat(),
        now.isoformat(),
        jobId,
      ),
    )

    return {
      "job_id": jobId,
      "worker_id": workerId,
      "status": job["status"],
      "lease_until": newLeaseUntil.isoformat(),
    }

@app.get("/health")
async def health() -> dict[str, str]:
  return {"status": "ok"}

@app.post(
  "/api/v1/webhooks/assessments",
  status_code=status.HTTP_201_CREATED,
)
async def createAssessment(
  payload: AssessmentRequest,
  response: Response,
  _: Annotated[
    None,
    Depends(requireWebhookToken)
    ],
  ) -> dict:
      jobId, created = saveAssessment(
        payload
      )

      if created:
        response.status_code = (
          status.HTTP_201_CREATED
        )
        message = "Assessment diterima"
      else:
        response.status_code = (
          status.HTTP_200_OK
        )
        message = (
          "Assessment sebelumnya sudah diterima"
        )
      currentStatus = (
        "QUEUED"
        if created
        else getJobStatus(jobId)["status"]
      )
      return {
        "message": message,
        "job_id": jobId,
        "external_id": payload.external_id,
        "status": currentStatus,
        "created": created,
      }

@app.get(
  "/api/v1/jobs/{jobId}",
)
async def readJobStatus(
  jobId: str,
  _: Annotated[
    None,
    Depends(requireWebhookToken),
  ],
) -> dict:
    return getJobStatus(jobId)

@app.post(
  "/api/v1/worker/jobs/claim",
  response_model=None,
  responses={
    204: {
      "description": (
        "Tidak ada job dalam antrean"
      )
    }
  },
)
async def claimNextJob(
  payload: WorkerClaimRequest,
  _: Annotated[
    None,
    Depends(requireWorkerToken),
  ],
) -> dict | Response:
  recoverExpiredJobs()
  job = claimJob(payload.worker_id)

  if job is None:
    return Response(
      status_code=(
        status.HTTP_204_NO_CONTENT
      )
    )
  return job

@app.get(
  "/api/v1/worker/jobs/{jobId}/answers/{module}",
)
async def readWorkerAnswers(
  jobId: str,
  module: str,
  workerId: Annotated[
    str,
    Header(
      alias="X-Worker-ID",
      min_length=1,
      max_length=100,
    ),
  ],
  _: Annotated[
    None,
    Depends(requireWorkerToken),
  ],
) -> dict:
    return getWorkerAnswers(
      jobId=jobId,
      module=module,
      workerId=workerId,
    )

@app.patch(
  "/api/v1/worker/jobs/{jobId}/modules/{module}"
)
async def patchModuleStatus(
  jobId: str,
  module: str,
  payload: ModuleStatusUpdate,
  workerId: Annotated[
    str,
    Header(
      alias="X-Worker-ID",
      min_length=1,
      max_length=100,
    ),
  ],
  _: Annotated[
    None,
    Depends(requireWorkerToken),
  ],
) -> dict:
  return updateModuleStatus(
    jobId=jobId,
    module=module,
    workerId=workerId,
    payload=payload,
  )

@app.post(
  "/api/v1/worker/jobs/{jobId}/heartbeat"
)
async def heartbeatWorkerJob(
  jobId: str,
  workerId: Annotated[
    str, Header(
      alias="X-Worker-ID",
      min_length=1,
      max_length=100,
    ),
  ],
  _: Annotated[
    None, Depends(requireWorkerToken),
  ],
) -> dict:
  return heartbeatJob(jobId=jobId, workerId=workerId)
