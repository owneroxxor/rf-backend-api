import asyncio
from fastapi import Depends, FastAPI
from starlette.responses import RedirectResponse

from app.api.routers import health, login, b3
from app.security import JWTBearer, fetch_public_sig_keys
from app.log import get_logger
from app.b3 import B3

log = get_logger("uvicorn.error")

app = FastAPI()
app.include_router(login.router)
app.include_router(b3.router, dependencies=[Depends(JWTBearer())])
app.include_router(health.router)


@app.on_event("startup")
async def startup():
    log.info("Starting up application ...")
    if not fetch_public_sig_keys():
        log.fatal("Failed to fetch public signature parameters from identity server")
        return
    asyncio.create_task(fc.start())
    log.info("Application successfully started")


@app.on_event("shutdown")
async def shutdown():
    log.info("Shutting down application ...")
    await fc.stop()
    log.info("Applcation successfully stopped")


@app.get("/")
async def docs_redirect():
    return RedirectResponse(url="/docs")
