from fastapi import APIRouter, HTTPException,Depends,FastAPI, Security
from elasticsearch import AsyncElasticsearch
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
import secrets
from pydantic import BaseModel
from datetime import datetime, timedelta
import math
import logging
import random


app = FastAPI()
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

router = APIRouter()

# Connexion à Elasticsearch
elastic = AsyncElasticsearch(
    cloud_id="PA2024:ZXVyb3BlLXdlc3Q5LmdjcC5lbGFzdGljLWNsb3VkLmNvbSQ4Yjk5MjQxNjBmNjc0ODdmYjViMTJlZDhiNmIxYWVlZSQyOThmMDU0ZjE2YjQ0NmMzOThkMzMzNjE1MzZhNDlmMg==",
    http_auth=("elastic", "6EPhppu8hMfSwYZ9reTWfFnv"),
)


SECRET_KEY = "cle_secrete"  
ALGORITHM = "HS256" 




# PAGE D'ACCUEIL DES DONNEURS

# RECUPERER LES INFORMATIONS DE LA TABLE DES UTILISATEURS
@router.get("/users/{email}")
async def get_user_by_email(email: str):
    try:
        result = await elastic.search(index="database_users", body={
            "query": {
                "match": {
                    "email": email
                }
            }
        })

        # Vérifier si l'utilisateur existe
        if result['hits']['total']['value'] == 0:
            raise HTTPException(status_code=404, detail="Utilisateur non trouvé")

        user = result['hits']['hits'][0]["_source"]
        return {"user": user}

    except Exception as e:
        print(f"Erreur dans l'extraction de l'utilisateur: {e}")
        raise HTTPException(status_code=500, detail=str(e)) 
    


# RECUPERER LES INFORMATIONS DE LA TABLE DES RENDEZ VOUS
@router.get("/appointment/{email}")
async def get_appointment_by_email(email: str):
    try:
        result = await elastic.search(index="appointments", body={
            "query": {
                "match": {
                    "donorEmail": email
                }
            }
        })

        # Vérifier si l'utilisateur existe
        if result['hits']['total']['value'] == 0:
            raise HTTPException(status_code=404, detail="Utilisateur non trouvé")

        user = result['hits']['hits'][0]["_source"]
        return {"user": user}

    except Exception as e:
        print(f"Erreur dans l'extraction de l'utilisateur: {e}")
        raise HTTPException(status_code=500, detail=str(e)) 




# PAGE DE PRISE DE RENDEZ VOUS

# Modèle de rendez-vous
class Appointment(BaseModel):
    dateRendezVous: str
    timeRendezVous: str
    status: str


# Route POST pour créer un rendez-vous
@router.post("/{email}/appointments")
async def create_appointment(email: str, appointment: Appointment):
    # Conversion de la date du rendez-vous en objet datetime
    appointment_date = datetime.strptime(appointment.dateRendezVous, "%Y-%m-%d")

    # Vérification que la date n'est pas dans le passé
    if appointment_date < datetime.now():
        raise HTTPException(status_code=400, detail="La date du rendez-vous doit être ultérieure à la date actuelle.")

    try:
        # Vérifier s'il existe déjà un rendez-vous programmé pour cet utilisateur
        search_response = await elastic.search(
            index="appointments",
            body={
                "query": {
                    "bool": {
                        "must": [
                            {"term": {"donorEmail": email}},
                            {"term": {"status": "Programmé"}}
                        ]
                    }
                }
            }
        )

        if search_response['hits']['total']['value'] > 0:
            raise HTTPException(status_code=400, detail="Vous avez déjà un rendez-vous programmé.")

        # Créer une nouvelle entrée dans Elasticsearch si aucun rendez-vous existant
        response = await elastic.index(
            index='appointments',
            body={
                "donorEmail": email,
                "dateRendezVous": appointment.dateRendezVous,
                "timeRendezVous": appointment.timeRendezVous,
                "status": "Programmé"
            }
        )
        return {"message": "Rendez-vous créé avec succès", "appointmentId": response["_id"]}

    except HTTPException as http_err:
        raise HTTPException(status_code=http_err.status_code, detail=http_err.detail)
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur lors de la création du rendez-vous : {e}")



# PAGE DE MISE A JOUR DE L'HISTORIQUE DES DONS


def calculate_months_since(date_str):
    if not date_str:
        return 0  
    date = datetime.strptime(date_str, '%Y-%m-%d')
    current_date = datetime.now()
    years_diff = current_date.year - date.year
    months_diff = current_date.month - date.month
    total_months = years_diff * 12 + months_diff
    return total_months





@router.put("/donors_history/{email}")
async def update_donor(email: str, donor_data: dict):
    try:
        # Recherche l'utilisateur par email
        result = await elastic.search(index="database_users", body={
            "query": {
                "match": {
                    "email": email
                }
            }
        })

        if result['hits']['total']['value'] == 0:
            raise HTTPException(status_code=404, detail="Donneur non trouvé")
        
        print(f"First Donation Date: {donor_data.get('firstDonationDate')}")
        print(f"Last Donation Date: {donor_data.get('lastDonationDate')}")
        print(f"Donor Data: {donor_data}")


        # Calcule les mois depuis le premier et le dernier don
        months_since_first = donor_data.get("donor_history").get("monthsSinceFirstDonation")
        months_since_last = donor_data.get("donor_history").get("monthsSinceLastDonation")


        doc_id = result['hits']['hits'][0]['_id']


        update_response = await elastic.update(index="database_users", id=doc_id, body={
            "doc": {
                "donor_history": {
                    "numberOfDonations": donor_data.get("donor_history").get("numberOfDonations"),
                    "totalVolumeDonated": donor_data.get("donor_history").get("totalVolumeDonated"),
                    "firstDonationDate": donor_data.get("donor_history").get("firstDonationDate"),
                    "lastDonationDate": donor_data.get("donor_history").get("lastDonationDate"),
                    "monthsSinceFirstDonation": months_since_first,
                    "monthsSinceLastDonation": months_since_last
                }
            }
        })  


        return {"message": f"Informations de {email} mises à jour"}

    except Exception as e:
        raise HTTPException(status_code=500, detail="Erreur lors de la mise à jour: " + str(e))







# ANALYSE SANGUINE

@router.put("/update_blood_stats/{email}")
async def update_blood_stats(email: str, blood_data: dict):
    try:
        # Recherche l'utilisateur par email
        result = await elastic.search(index="database_users", body={
            "query": {
                "match": {
                    "email": email
                }
            }
        })

        # Vérification si le donneur existe
        if result['hits']['total']['value'] == 0:
            raise HTTPException(status_code=404, detail="Donneur non trouvé")

        # Extraction des données du formulaire
        gender = blood_data.get("Gender")
        age = blood_data.get("Age")
        current_smoker = blood_data.get("currentSmoker")
        cigs_per_day = blood_data.get("cigsPerDay")

        if current_smoker is not None:
            current_smoker = bool(int(current_smoker))  


        doc_id = result['hits']['hits'][0]['_id']

        # Mise à jour des données de l'utilisateur dans Elasticsearch
        update_response = await elastic.update(index="database_users", id=doc_id, body={
            "doc": {
                "blood_stats": {
                    "Gender": gender,              
                    "Age": age,                   
                    "currentSmoker": current_smoker,  
                    "cigsPerDay": cigs_per_day       
                }
            }
        })

        return {"message": f"Les informations de {email} ont été mises à jour avec succès."}

    except Exception as e:
        raise HTTPException(status_code=500, detail="Erreur lors de la mise à jour: " + str(e))



# Fonction pour générer des valeurs aléatoires pour un intervalle donné
def get_random_float(min_val, max_val, decimals=1):
    factor = 10 ** decimals
    return round(random.uniform(min_val, max_val), decimals)

def get_random_int(min_val, max_val):
    return random.randint(min_val, max_val)

# Modèle pour les données de prélèvement sanguin
class BloodTest(BaseModel):
    Hemoglobin: float
    MCH: float
    MCHC: float
    MCV: float
    Pregnancies: int
    Glucose: float
    SkinThickness: float
    Insulin: float
    BMI: float
    DiabetesPedigreeFunction: float
    BPMeds: bool
    Cholesterol: float
    heartRate: int
    cp: int
    trestbps: int
    fbs: bool
    restecg: int
    thalach: int
    exang: bool
    oldpeak: float
    slope: int
    ca: int
    thal: int
    sysBP: int
    diaBP: int
    BloodPressure: int

# Fonction pour générer les données
def generate_blood_test_data():
    return BloodTest(
        Hemoglobin=get_random_float(5, 18),
        MCH=get_random_float(15, 30),
        MCHC=get_random_float(25, 35),
        MCV=get_random_float(60, 101),
        Pregnancies=get_random_int(0, 15),
        Glucose=get_random_float(0, 200),
        SkinThickness=get_random_float(0, 50),
        Insulin=get_random_float(0, 900),
        BMI=get_random_float(0, 50),
        DiabetesPedigreeFunction=get_random_float(0, 1, 3),
        BPMeds=random.choice([True, False]),
        Cholesterol=get_random_float(100, 500),
        heartRate=get_random_int(50, 110),
        cp=get_random_int(0, 4),
        trestbps=get_random_int(100, 160),
        fbs=random.choice([True, False]),
        restecg=get_random_int(0, 2),
        thalach=get_random_int(70, 190),
        exang=random.choice([True, False]),
        oldpeak=get_random_float(0.0, 5.0),
        slope=get_random_int(0, 2),
        ca=get_random_int(0, 4),
        thal=get_random_int(0, 3),
        sysBP=get_random_int(100, 190),
        diaBP=get_random_int(60, 110),
        BloodPressure=get_random_int(0, 120)
    )

def generate_random_value(min_value, max_value, decimals=1):
    return round(random.uniform(min_value, max_value), decimals)




# Mise à jour des données du test sanguin

@router.put("/BloodPrelevement/{email}")
async def blood_prelevement(email: str, blood_test_data: dict):
    try:
        # Recherche l'utilisateur par email
        result = await elastic.search(index="database_users", body={
            "query": {
                "match": {
                    "email": email
                }
            }
        })

        # Vérification si le donneur existe
        if result['hits']['total']['value'] == 0:
            raise HTTPException(status_code=404, detail="Donneur non trouvé")
        
        
        doc_id = result['hits']['hits'][0]['_id']

        # Générer les données aléatoires pour les colonnes spécifiées
        blood_test_data = {
            "Hemoglobin": generate_random_value(5, 18),
            "MCH": generate_random_value(15, 30),
            "MCHC": generate_random_value(25, 35),
            "MCV": generate_random_value(60, 101),
            "Pregnancies": random.randint(0, 15),
            "Glucose": generate_random_value(0, 200),
            "SkinThickness": generate_random_value(0, 50),
            "Insulin": generate_random_value(0, 900),
            "BMI": generate_random_value(0, 50),
            "DiabetesPedigreeFunction": generate_random_value(0, 1, 3),  
            "BPMeds": bool(random.randint(0, 1)),
            "Cholesterol": generate_random_value(100, 500),
            "heartRate": random.randint(50, 110),
            "cp": random.randint(0, 4),
            "trestbps": random.randint(100, 160),
            "fbs": bool(random.randint(0, 1)),
            "restecg": random.randint(0, 2),
            "thalach": random.randint(70, 190),
            "exang": bool(random.randint(0, 1)),
            "oldpeak": generate_random_value(0.0, 5.0, 1),
            "slope": random.randint(0, 2),
            "ca": random.randint(0, 4),
            "thal": random.randint(0, 3),
            "sysBP": random.randint(100, 190),
            "diaBP": random.randint(60, 110),
            "BloodPressure": random.randint(0, 120)
        }

        
        update_body = {
            "doc": {
                "blood_stats": blood_test_data
            }
        }

        
        update_response = await elastic.update(index="database_users", id=doc_id, body=update_body)

        return {"message": "Prélèvement sanguin mis à jour avec succès", "data": blood_test_data}

    except Exception as e:
        raise HTTPException(status_code=500, detail="Erreur lors de la mise à jour: " + str(e))
