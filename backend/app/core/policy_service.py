"""Singleton LinUCB policy with versioned persistence.

Loads the latest snapshot from the DB on startup; falls back to a fresh model.
On each /policy/update, the new state is bumped to the next version and saved.
"""
from __future__ import annotations
from threading import RLock
import numpy as np
from sqlalchemy import select, desc
from sqlalchemy.orm import Session

from .linucb import LinUCB
from .actions import NUM_ACTIONS
from .features import FEATURE_DIM
from ..config import LINUCB_ALPHA
from ..db.database import SessionLocal
from ..db.models import PolicySnapshot


class PolicyService:
    def __init__(self) -> None:
        self._lock = RLock()
        self._policy: LinUCB | None = None
        self._version: int = 0

    def _load(self) -> None:
        with SessionLocal() as db:
            row = db.execute(
                select(PolicySnapshot).order_by(desc(PolicySnapshot.version)).limit(1)
            ).scalar_one_or_none()
            if row is None:
                self._policy = LinUCB(
                    n_arms=NUM_ACTIONS,
                    n_features=FEATURE_DIM,
                    alpha=LINUCB_ALPHA,
                )
                self._version = 0
            else:
                self._policy = LinUCB.from_snapshot(row.snapshot)
                self._version = row.version

    @property
    def policy(self) -> LinUCB:
        if self._policy is None:
            self._load()
        assert self._policy is not None
        return self._policy

    @property
    def version(self) -> int:
        if self._policy is None:
            self._load()
        return self._version

    def select(self, x: np.ndarray, allowed_idx: list[int]) -> tuple[int, float, list[float]]:
        with self._lock:
            idx, conf, scores = self.policy.select(x, allowed_idx)
            return idx, conf, scores.tolist()

    def update(
        self,
        db: Session,
        arm_idx: int,
        x: np.ndarray,
        reward: float,
        notes: str | None = None,
    ) -> int:
        with self._lock:
            self.policy.update(arm_idx, x, reward)
            self._version += 1
            db.add(
                PolicySnapshot(
                    version=self._version,
                    snapshot=self.policy.snapshot(),
                    n_features=self.policy.n_features,
                    n_arms=self.policy.n_arms,
                    notes=notes,
                )
            )
            db.commit()
            return self._version


policy_service = PolicyService()
