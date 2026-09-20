from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .config import get_settings
from .database import Base, SessionLocal, engine
from .routers import actions, auth, complaints, departments, health
from .seed import seed_database


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Initialize database tables and seed baseline data
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        seed_database(db)
    finally:
        db.close()
    yield


settings = get_settings()

app = FastAPI(
    title="ResolveIt API",
    description="AI-powered closed-loop civic issue resolution platform",
    lifespan=lifespan,
)

origins = [settings.FRONTEND_ORIGIN]
if "http://localhost:5173" not in origins:
    origins.append("http://localhost:5173")
if "http://127.0.0.1:5173" not in origins:
    origins.append("http://127.0.0.1:5173")

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router)
app.include_router(auth.router)
app.include_router(departments.router)
app.include_router(complaints.router)
app.include_router(actions.router)
