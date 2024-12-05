from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from routes import auth, donors, admin
from google.cloud import storage
import os
import uvicorn
import pandas as pd
from tensorflow.keras.models import load_model
from sklearn.preprocessing import StandardScaler  
from pydantic import BaseModel
import joblib
import numpy as np



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













if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080)) 
    uvicorn.run(app, host="0.0.0.0", port=port)

