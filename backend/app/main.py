from fastapi import FastAPI
from app.database import init_db
from app.routers import jobs

app = FastAPI(title="Job Automation Bot", version="1.0.0")

# Registramos el router de empleos
app.include_router(jobs.router)

@app.on_event("startup")
def on_startup():
    init_db()

@app.get("/")
def read_root():
    return {"message": "Job Search & ATS Optimization Bot is running!"}