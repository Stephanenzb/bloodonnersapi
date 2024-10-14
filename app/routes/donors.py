from fastapi import APIRouter, HTTPException,Depends,FastAPI, Security
from elasticsearch import AsyncElasticsearch
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
import secrets
from pydantic import BaseModel
from datetime import datetime, timedelta
import math
import logging


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
        raise HTTPException(status_code=500, detail=str(e))  # Inclure le message d'erreur
    


# RECUPERER LES INFORMATIONS DE LA TABLE DES RENDEZ VOUS
@router.get("/appointment/{email}")
async def get_appointment_by_email(email: str):
    try:
        result = await elastic.search(index="appointments", body={
            "query": {
                "match": {
                    "donorEmail": email,
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
        raise HTTPException(status_code=500, detail=str(e))  # Inclure le message d'erreur




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

        # Si un rendez-vous programmé existe déjà, retourner un message d'erreur sans le code HTTP dans le détail
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
        # Capturer l'exception HTTP sans afficher le code d'erreur
        raise HTTPException(status_code=http_err.status_code, detail=http_err.detail)
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur lors de la création du rendez-vous : {e}")



# PAGE DE MISE A JOUR DE L'HISTORIQUE DES DONS


def calculate_months_since(date_str):
    if not date_str:
        return 0  # Ou une autre valeur par défaut
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



