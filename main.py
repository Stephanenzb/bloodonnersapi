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


# Configuration du bucket et du fichier modèle
BUCKET_NAME = 'pa2024_bucket'
MODEL_FILE_NAME = 'pa2024.h5'
SCALER_FILE_NAME = 'pa2024_blood_donation.pkl'
LOCAL_MODEL_PATH = os.path.join(os.getcwd(), MODEL_FILE_NAME)
LOCAL_SCALER_PATH = os.path.join(os.getcwd(), SCALER_FILE_NAME)

model = None
scaler = None

MODEL_FILE_NAME2 = 'multi_label_model.pkl'
LOCAL_MODEL_PATH2 = os.path.join(os.getcwd(), MODEL_FILE_NAME2)
model2 = None


# Fonction pour télécharger le modèle et le scaler depuis le bucket
def download_file(BUCKET_NAME, file_name, local_path):
    client = storage.Client()
    bucket = client.bucket(BUCKET_NAME)
    blob = bucket.blob(file_name)
    blob.download_to_filename(local_path)
    print(f"Fichier téléchargé depuis {BUCKET_NAME} : {file_name}")


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

    download_file(BUCKET_NAME, MODEL_FILE_NAME2, LOCAL_MODEL_PATH2)
    global model2
    # Utilisation de joblib pour charger le modèle RandomForest
    model2 = joblib.load(LOCAL_MODEL_PATH2)
    if model2 is None:
        print("Erreur lors du chargement du modèle RandomForest.")
    else:
        print(f"Modèle RandomForest téléchargé et chargé : {LOCAL_MODEL_PATH2}")
        


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
    



@app.post("/api/diseasePrediction")
async def disease_prediction(data: dict):
    try:
        # Validation des champs requis
        required_fields = ['Gender', 'Age', 'Hemoglobin', 'MCH', 'MCHC', 'MCV', 'Pregnancies', 'Glucose', 'BloodPressure']
        for field in required_fields:
            if data.get(field) is None:
                raise HTTPException(status_code=400, detail=f"Missing required field: {field}")
        
        # Extraire les données de la requête
        gender = data.get('Gender', 'Femme')  # Par défaut, "Femme"
        age = data.get('Age', 0)
        hemoglobin = data.get('Hemoglobin', 0)
        mch = data.get('MCH', 0)
        mchc = data.get('MCHC', 0)
        mcv = data.get('MCV', 0)
        pregnancies = data.get('Pregnancies', 0)
        glucose = data.get('Glucose', 0)
        blood_pressure = data.get('BloodPressure', 0)
        skin_thickness = data.get('SkinThickness', 0)
        insulin = data.get('Insulin', 0)
        bmi = data.get('BMI', 0)
        diabetes_pedigree_function = data.get('DiabetesPedigreeFunction', 0)
        current_smoker = data.get('currentSmoker', 0)
        cigs_per_day = data.get('cigsPerDay', 0)
        bpmeds = data.get('BPMeds', 0)
        cholesterol = data.get('Cholesterol', 0)
        heart_rate = data.get('heartRate', 0)
        cp = data.get('cp', 0)
        trestbps = data.get('trestbps', 0)
        fbs = data.get('fbs', 0)
        restecg = data.get('restecg', 0)
        thalach = data.get('thalach', 0)
        exang = data.get('exang', 0)
        oldpeak = data.get('oldpeak', 0)
        slope = data.get('slope', 0)
        ca = data.get('ca', 0)
        thal = data.get('thal', 0)
        sysbp = data.get('sysBP', 0)
        diabp = data.get('diaBP', 0)

        # Convertir "Homme" en 1 et "Femme" en 0
        gender = 1 if gender == "Homme" else 0

        # Préparer les données pour le modèle sous forme de DataFrame
        input_data = pd.DataFrame([[ 
            gender, hemoglobin, mch, mchc, mcv, pregnancies, glucose, blood_pressure,
            skin_thickness, insulin, bmi, diabetes_pedigree_function, age, current_smoker,
            cigs_per_day, bpmeds, cholesterol, sysbp, diabp, heart_rate, cp, trestbps, 
            fbs, restecg, thalach, exang, oldpeak, slope, ca, thal]], 
            columns=['Gender', 'Hemoglobin', 'MCH', 'MCHC', 'MCV', 'Pregnancies', 'Glucose',
                     'BloodPressure', 'SkinThickness', 'Insulin', 'BMI', 'DiabetesPedigreeFunction',
                     'Age', 'currentSmoker', 'cigsPerDay', 'BPMeds', 'Cholesterol', 'sysBP', 'diaBP',
                     'heartRate', 'cp', 'trestbps', 'fbs', 'restecg', 'thalach', 'exang', 'oldpeak',
                     'slope', 'ca', 'thal'])
        
         # Faire la prédiction avec le modèle
        prediction = model2.predict(input_data)

        # Format de la prédiction
        # La sortie est un tableau de taille (1, 4) où chaque colonne correspond à une pathologie
        # Renvoi d'un dictionnaire pour chaque pathologie (Anemia, Diabetes, Hypertension, Cardiovascular)
        return {
            "prediction": {
                "Anemia": bool(prediction[0][0]),
                "Diabetes": bool(prediction[0][1]),
                "Hypertension": bool(prediction[0][2]),
                "Cardiovascular": bool(prediction[0][3])
            }
        }
    
    except Exception as e:
        # Gestion des erreurs
        raise HTTPException(status_code=400, detail=str(e))
    

@app.get("/test")
async def test():
    return {"message": "Test endpoint"}


















if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080)) 
    uvicorn.run(app, host="0.0.0.0", port=port)

