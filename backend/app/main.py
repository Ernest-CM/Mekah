import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .db.database import init_db
from .api import context as context_router
from .api import adapt as adapt_router
from .api import hitl as hitl_router
from .api import policy as policy_router

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield


app = FastAPI(
    title="Mekah Adaptive Web Interface API",
    description=(
        "Constrained Reinforcement Learning + Human-in-the-Loop adaptive web "
        "interface backend. Implements the LinUCB policy, WCAG 2.1 safety shield, "
        "and HITL governance defined in revised.md and project_document.txt."
    ),
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(context_router.router)
app.include_router(adapt_router.router)
app.include_router(hitl_router.router)
app.include_router(policy_router.router)


@app.get("/api/health")
def health() -> dict:
    return {"status": "ok"}
