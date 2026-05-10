from sqlalchemy.orm import Session
from fastapi import Depends, HTTPException
from ..db.database import SessionLocal
from ..db import models


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def require_context(context_id: str, db: Session) -> models.ContextEvent:
    row = db.get(models.ContextEvent, context_id)
    if row is None:
        raise HTTPException(status_code=404, detail=f"context_id {context_id} not found")
    return row


def require_decision(decision_id: str, db: Session) -> models.Decision:
    row = db.get(models.Decision, decision_id)
    if row is None:
        raise HTTPException(status_code=404, detail=f"decision_id {decision_id} not found")
    return row
