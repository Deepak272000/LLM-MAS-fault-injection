from fastapi import FastAPI
from app.config import settings
from app.router import router

app = FastAPI(title=settings.APP_NAME)
app.include_router(router)