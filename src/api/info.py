from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel
from src.api import auth

router = APIRouter(
    prefix="/info",
    tags=["info"],
    dependencies=[Depends(auth.get_api_key)],
)

class Timestamp(BaseModel):
    day: str
    hour: int

@router.post("/current_time")
def post_time(timestamp: Timestamp):
    """
    Share current time.
    """
    return {
        "current_time": {
            "day": timestamp.day,
            "hour": timestamp.hour
        },
        "message": f"The current time is {timestamp.hour}:00 on {timestamp.day}."
    }

