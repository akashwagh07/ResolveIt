from fastapi import APIRouter
from ..clock import now as clock_now
from ..llm import get_llm_status

router = APIRouter(tags=["health"])


@router.get("/api/health")
def get_health():
    llm_status, seconds_left = get_llm_status()
    return {
        "status": "ok",
        "time": clock_now().isoformat(),
        "llm": {
            "status": llm_status,
            "cooldown_seconds_left": seconds_left,
        },
    }
