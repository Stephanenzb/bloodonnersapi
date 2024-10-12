from fastapi import APIRouter, HTTPException,Depends,FastAPI, Security
from elasticsearch import AsyncElasticsearch
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
import secrets
from pydantic import BaseModel
from datetime import datetime, timedelta
import math


app = FastAPI()
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

router = APIRouter()

# Connexion à Elasticsearch
elastic = AsyncElasticsearch(
    cloud_id="b01a042efef84182a85f799130f733f5:ZXVyb3BlLXdlc3QzLmdjcC5jbG91ZC5lcy5pbzo0NDMkNTU3NDM0YTQxNDI0NGVlYzk0NDUzZWM2YWIxZjc3N2EkNWY1ZDA0ZjVkMDAwNDc2MGFjOWUwMjYyZTk0ZTBjZjI=",
    http_auth=("elastic", "bvfN5fngmOAhCViV4cuVcHIX"),
)


SECRET_KEY = "votre_cle_secrete"  # Remplacez par votre clé secrète
ALGORITHM = "HS256"  # Algorithme de cryptage


# Modèle pour valider les données du formulaire d'historique de dons
class DonorHistory(BaseModel):
    firstDonationDate: datetime
    lastDonationDate: datetime
    totalDonations: int
    totalVolume: float
    email: str


oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

# Fonction pour décoder le token
async def get_current_user(token: str = Depends(oauth2_scheme)):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email = payload.get("sub")
        if email is None:
            raise HTTPException(status_code=401, detail="Utilisateur non authentifié")
        return email
    except JWTError:
        raise HTTPException(status_code=401, detail="Token invalide")
    




@router.get("/donors/me/{email}")
async def get_user(email: str):
    result = elastic.search(index="database_users", body={
        "query": {
            "term": {"email.keyword": email}
        }
    })
    
    if not result['hits']['hits']:
        raise HTTPException(status_code=404, detail="Utilisateur non trouvé")
    
    return result['hits']['hits'][0]['_source']  # Renvoie toutes les données de l'utilisateur

    





@router.get("/donors/me2")
async def get_donor_info2():
    try:
        email = "test@gmail.com"  # Remplace par l'email souhaité

        result = elastic.search(index="database_users", body={  # Retire `await`
            "query": {
                "match": {
                    "email": email
                }
            }
        })

        if not result['hits']['hits']:
            raise HTTPException(status_code=404, detail="Donneur non trouvé")

        user_data = result['hits']['hits'][0]["_source"]
        donor_history = user_data.get("donor_history", {})
        
        return {
            "username": user_data.get("username"),
            "points": user_data.get("points", 0),
            "nextAppointment": "Aucun rendez-vous prévu.",  # Remplace par la logique pour le prochain rendez-vous
            "firstDonationDate": donor_history.get("firstDonationDate", "Non renseignée"),
            "numberOfDonations": donor_history.get("numberOfDonations", 0),
            "totalVolume": donor_history.get("totalVolumeDonated", 0),
            "lastDonationDate": donor_history.get("lastDonationDate", "Non renseignée"),
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur lors de la récupération des informations du donneur : {e}")

























































































































# Modèle de rendez-vous
class Appointment(BaseModel):
    dateRendezVous: datetime
    timeRendezVous: str  # format HH:MM

# Route POST pour créer un rendez-vous
@router.post("/{email}/appointments")
async def create_appointment(appointment: Appointment, email: str = Depends(get_current_user)):
    try:
        # Créer une entrée dans Elasticsearch avec le statut par défaut "prévu"
        response = elastic.index(
            index='appointments',
            body={
                "donneurEmail": email,
                "dateRendezVous": appointment.dateRendezVous,
                "timeRendezVous": appointment.timeRendezVous,
                "status": "prévu"
            }
        )
        return {"message": "Rendez-vous créé avec succès", "appointmentId": response["_id"]}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur lors de la création du rendez-vous : {e}")





























# Fonction pour calculer l'écart en mois entre deux dates
def calculate_months_between(date1: datetime, date2: datetime) -> int:
    return (date2.year - date1.year) * 12 + date2.month - date1.month

# Route POST pour enregistrer l'historique de don dans Elasticsearch
@router.post("/donor/history")
async def update_donor_history(donor_history: DonorHistory, email: str = Depends(get_current_user)):
    try:
        today = datetime.now()
        months_since_first_donation = calculate_months_between(donor_history.firstDonationDate, today)
        months_since_last_donation = calculate_months_between(donor_history.lastDonationDate, today)

        # Préparation des données à insérer dans Elasticsearch
        donor_history_data = { 
            "firstDonationDate": donor_history.firstDonationDate,
            "lastDonationDate": donor_history.lastDonationDate,
            "totalVolumeDonated": donor_history.totalVolume,
            "numberOfDonations": donor_history.totalDonations,
            "monthsSinceFirstDonation": months_since_first_donation,
            "monthsSinceLastDonation": months_since_last_donation,
        }

        # Insertion ou mise à jour dans l'index Elasticsearch
        response = elastic.index(
            index='database_users',
            body=donor_history_data,
            id=email  
        )

        return {
            "message": "Historique de dons mis à jour avec succès",
            "data": response
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur lors de la mise à jour de l'historique de dons : {e}")
