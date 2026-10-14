from fastapi import APIRouter

router = APIRouter(tags=["Health"])

@router.get("/health")
def health_check():
    return {"status": "ok", "app": "AI Tai Nang 2026 - Excel QA"}
