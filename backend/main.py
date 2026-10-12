import traceback

from database import init_db
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from routers import jobs

app = FastAPI(title="Job Automation Bot", version="1.0.0", debug=True)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Registramos el router de empleos
app.include_router(jobs.router)


@app.on_event("startup")
def on_startup():
    init_db()


@app.get("/")
def read_root():
    return {"message": "Job Search & ATS Optimization Bot is running!"}


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    # Esto imprime el traceback completo directamente en la consola de Docker
    error_trace = traceback.format_exc()
    print("🔥 ERROR CRÍTICO CAPTURADO:")
    print(error_trace)

    # Y te devuelve el error detallado en la respuesta HTTP para que lo leas de inmediato
    return JSONResponse(
        status_code=500,
        content={"detail": str(exc), "traceback": error_trace},
    )
