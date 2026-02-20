from fastapi import APIRouter, Depends
from app.core.security import get_current_user
from app.analytics.engine import get_user_analytics
from app.db.mongodb import users_col
from app.core.config import get_settings
from app.models.schemas import AnalyticsSummary

router = APIRouter(prefix="/api/analytics", tags=["analytics"])
settings = get_settings()


@router.get("/", response_model=AnalyticsSummary)
async def get_analytics(user_id: str = Depends(get_current_user)):
    user = await users_col().find_one({"_id": user_id})
    data = await get_user_analytics(user_id)

    return AnalyticsSummary(
        total_questions=data["total_questions"],
        questions_today=data["questions_today"],
        daily_limit=data["daily_limit"],
        top_clusters=data["top_clusters"],
        storage_used_mb=user.get("storage_used_mb", 0)
    )
