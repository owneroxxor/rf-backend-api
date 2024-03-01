import asyncio

from fastapi import FastAPI
from starlette.responses import RedirectResponse

from app.api.routers import b3_router, login  # health,
from b3 import B3_client
from db import DB_client
from log import get_logger

log = get_logger("uvicorn.error")

app = FastAPI()
app.include_router(login.router)
app.include_router(b3_router.router)
# app.include_router(health.router)


@app.on_event("startup")
async def startup():
    log.info("Starting up application ...")
    await B3_client.start()
    await DB_client.start()
    log.info("Application successfully started")


@app.on_event("shutdown")
async def shutdown():
    log.info("Shutting down application ...")
    await B3_client.stop()
    await DB_client.stop()
    log.info("Applcation successfully stopped")


@app.get("/")
async def docs_redirect():
    return RedirectResponse(url="/docs")
