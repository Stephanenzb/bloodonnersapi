from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.routes import auth, donors, admin


app = FastAPI()

# Configuration de CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Inclusion des routes
app.include_router(auth.router, prefix="/api", tags=["auth"])
app.include_router(donors.router, prefix="/api", tags=["donors"])
app.include_router(admin.router, prefix="/api", tags=["admin"])
@app.get("/")
async def root():
    return {"message": "Welcome to the Blood Donation API"}
