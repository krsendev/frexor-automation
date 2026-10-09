import secrets
from typing import Annotated, Callable

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from .config import WEBHOOK_TOKEN, WORKER_TOKEN

bearer = HTTPBearer()

# Membuat fungsi pemeriksaan token
def tokenDependency(expectedToken: str) -> Callable:
  async def verify(
    credentials: Annotated[
      HTTPAuthorizationCredentials,
      Depends(bearer),
    ],
  ) -> None:
      tokenValid = secrets.compare_digest(
        credentials.credentials,
        expectedToken,
      )
      if not tokenValid:
        raise HTTPException(
          status_code=status.HTTP_401_UNAUTHORIZED,
          detail="Token tidak valid",
          headers={
            "WWW-Authenticate": "Bearer"
          },
        )
  return verify

requireWebhookToken = tokenDependency(WEBHOOK_TOKEN)
requireWorkerToken = tokenDependency(WORKER_TOKEN)
