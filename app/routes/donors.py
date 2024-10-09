from fastapi import APIRouter, HTTPException,Depends
from elasticsearch import Elasticsearch
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
import secrets
from pydantic import BaseModel
from datetime import datetime
import math


router = APIRouter()

# Connexion à Elasticsearch
elastic = Elasticsearch(
    cloud_id="b01a042efef84182a85f799130f733f5:ZXVyb3BlLXdlc3QzLmdjcC5jbG91ZC5lcy5pbzo0NDMkNTU3NDM0YTQxNDI0NGVlYzk0NDUzZWM2YWIxZjc3N2EkNWY1ZDA0ZjVkMDAwNDc2MGFjOWUwMjYyZTk0ZTBjZjI=",
    http_auth=("elastic", "bvfN5fngmOAhCViV4cuVcHIX"),
)

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")


SECRET_KEY = secrets.token_hex(32) 
ALGORITHM = "HS256"


async def get_current_user(token: str = Depends(oauth2_scheme)):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email = payload.get("sub")  
        if email is None:
            raise HTTPException(status_code=401, detail="Utilisateur non authentifié")
        return email
    except JWTError:
        raise HTTPException(status_code=401, detail="Token invalide")
    

# Modèle pour valider les données du formulaire d'historique de dons
class DonorHistory(BaseModel):
    firstDonationDate: datetime
    lastDonationDate: datetime
    totalDonations: int
    totalVolume: float
    email: str


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


@router.get("/donors/me")
async def get_donor_info(token: str = Depends(oauth2_scheme)):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
        email = payload.get("sub")
        
        if email is None:
            raise HTTPException(status_code=401, detail="Non authentifié")

        result = await elastic.search(index="database_users", body={
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
            "username": user_data.get("username", "Non renseigné"),
            "points": user_data.get("points", 0),
            "nextAppointment": user_data.get("nextAppointment", "Aucun rendez-vous prévu."),
            "firstDonationDate": donor_history.get("firstDonationDate", "Non renseignée"),
            "numberOfDonations": donor_history.get("numberOfDonations", 0),
            "totalVolume": donor_history.get("totalVolumeDonated", 0),
            "lastDonationDate": donor_history.get("lastDonationDate", "Non renseignée"),
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur lors de la récupération des informations du donneur : {e}")
