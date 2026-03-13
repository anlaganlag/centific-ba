from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.auth.dependencies import get_db
from app.api.routes import auth, projects, documents, chat, analysis


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Ensure database is initialized
    get_db()
    yield


app = FastAPI(title=settings.PROJECT_NAME, version=settings.VERSION, lifespan=lifespan)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(auth.router)
app.include_router(projects.router)
app.include_router(documents.router)
app.include_router(chat.router)
app.include_router(analysis.router)


@app.get("/")
async def root():
    return {"name": settings.PROJECT_NAME, "version": settings.VERSION}


@app.get("/health")
async def health():
    return {"status": "ok"}
