from database import init_db
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from routers import jobs

app = FastAPI(title="Job Automation Bot", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # O especifica http://localhost:5173
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
