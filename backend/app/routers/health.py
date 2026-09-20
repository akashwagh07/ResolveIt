from fastapi import APIRouter
from ..clock import now as clock_now

router = APIRouter(tags=["health"])


@router.get("/api/health")
def get_health():
    return {
        "status": "ok",
        "time": clock_now().isoformat(),
    }
