from uuid import uuid4
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from ..db import models
from ..schemas.api import ContextRequest, ContextResponse
from .deps import get_db

router = APIRouter(prefix="/api/context", tags=["context"])


@router.post("", response_model=ContextResponse)
def post_context(payload: ContextRequest, db: Session = Depends(get_db)) -> ContextResponse:
    cid = str(uuid4())
    row = models.ContextEvent(
        id=cid,
        user_id=payload.user_id,
        session_id=payload.session_id,
        features=payload.context_features,
        ui_state=payload.ui_state,
    )
    db.add(row)
    db.commit()
    return ContextResponse(context_id=cid)
