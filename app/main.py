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


# Configuration du bucket et du fichier modèle
BUCKET_NAME = 'bucket_pa2024'
MODEL_FILE_NAME = 'pa2024.h5'
SCALER_FILE_NAME = 'pa2024_blood_donation.pkl'
LOCAL_MODEL_PATH = os.path.join(os.getcwd(), MODEL_FILE_NAME)
LOCAL_SCALER_PATH = os.path.join(os.getcwd(), SCALER_FILE_NAME)

model = None
scaler = None

# Fonction pour télécharger le modèle et le scaler depuis le bucket
def download_file(bucket_name, file_name, local_path):
    client = storage.Client()
    bucket = client.bucket(bucket_name)
    blob = bucket.blob(file_name)
    blob.download_to_filename(local_path)
    print(f"Fichier téléchargé depuis {bucket_name} : {file_name}")

# Événement de démarrage de l'application pour télécharger et charger le modèle et le scaler
@app.on_event("startup")
async def startup_event():
    download_file(BUCKET_NAME, MODEL_FILE_NAME, LOCAL_MODEL_PATH)
    global model
    model = load_model(LOCAL_MODEL_PATH)
    if model is None:
        print("Erreur lors du chargement du modèle.")
    else:
        print(f"Modèle téléchargé et chargé : {LOCAL_MODEL_PATH}")

    download_file(BUCKET_NAME, SCALER_FILE_NAME, LOCAL_SCALER_PATH)
    global scaler
    scaler = joblib.load(LOCAL_SCALER_PATH)
    if scaler is None:
        print("Erreur lors du chargement du scaler.")
    else:
        print(f"Scaler téléchargé et chargé : {LOCAL_SCALER_PATH}")


# Endpoint pour la prédiction
@app.post("/api/predict")
async def predict(data: dict):
    try:
        # Extraire les données pour la prédiction
        months_since_last_donation = data.get('Months since Last Donation', 0)
        number_of_donations = data.get('Number of Donations', 0)
        total_volume_donated = data.get('Total Volume Donated (c.c.)', 0)
        months_since_first_donation = data.get('Months since First Donation', 0)

        print("Données d'entrée:", months_since_last_donation, number_of_donations, total_volume_donated, months_since_first_donation)

        # Préparer les données d'entrée avec l'ordre correct
        input_data = pd.DataFrame([[months_since_last_donation, number_of_donations, total_volume_donated, months_since_first_donation]],
                                  columns=['Months since Last Donation', 'Number of Donations', 'Total Volume Donated (c.c.)', 'Months since First Donation'])

        print("Données d'entrée préparées:", input_data)

        # Standardiser les données
        input_data_scaled = scaler.transform(input_data)

        # Faire la prédiction
        prediction_prob = model.predict(input_data_scaled)

        # Traitement de la prédiction
        prediction_class = (prediction_prob > 0.5).astype(int)
        prediction_percentage = prediction_prob[0][0] * 100

        return {
            "prediction": int(prediction_class[0][0]),
            "probability": round(float(prediction_percentage), 2)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))





