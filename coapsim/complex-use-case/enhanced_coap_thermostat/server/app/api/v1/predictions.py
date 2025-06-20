# app/api/v1/predictions.py
from typing import Annotated
from fastapi import APIRouter, Depends, Query

from ...core.dependencies import get_current_user, get_ml_service
from ...models.schemas.responses import PredictionResponse
from ...models.database.user import User
from ...services.ml_service import MLService
from ...core.exceptions import ThermostatException, create_http_exception

router = APIRouter(prefix="/predictions")

@router.get("/{device_id}/temperature", response_model=PredictionResponse)
async def get_temperature_predictions(
    device_id: str,
    hours: int = Query(default=24, ge=1, le=168),
    current_user: Annotated[User, Depends(get_current_user)],
    ml_service: Annotated[MLService, Depends(get_ml_service)]
):
    """Get temperature predictions for a device."""
    try:
        predictions = await ml_service.get_predictions(device_id, hours)
        return PredictionResponse(
            device_id=device_id,
            predictions=predictions.get("predictions", []),
            confidence=predictions.get("confidence", 0.0),
            model_version="1.0.0",
            generated_at=datetime.now()
        )
    except ThermostatException as e:
        raise create_http_exception(e)

