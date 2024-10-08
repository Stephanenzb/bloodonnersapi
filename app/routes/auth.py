from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from elasticsearch import Elasticsearch

router = APIRouter()

# Modèle pour l'inscription
class User(BaseModel):
    email: str
    username: str
    password: str
    role: str 


# Connexion à Elasticsearch
elastic = Elasticsearch(
    cloud_id="b01a042efef84182a85f799130f733f5:ZXVyb3BlLXdlc3QzLmdjcC5jbG91ZC5lcy5pbzo0NDMkNTU3NDM0YTQxNDI0NGVlYzk0NDUzZWM2YWIxZjc3N2EkNWY1ZDA0ZjVkMDAwNDc2MGFjOWUwMjYyZTk0ZTBjZjI=",
    http_auth=("elastic", "bvfN5fngmOAhCViV4cuVcHIX"),
)



# Route d'enregistrement 

@router.post("/register")
async def register_user(user: User):
    # Vérifiez si l'utilisateur existe déjà dans Elasticsearch
    existing_user = await elastic.search(
        index="database_users",
        body={
            "query": {
                "match": {
                    "email": user.email
                }
            }
        }
    )

    if existing_user['hits']['total']['value'] > 0:
        raise HTTPException(status_code=400, detail="Cet E-mail est déjà utilisé")

    # Enregistrement dans Elasticsearch
    user_data = {
        "email": user.email,
        "password": user.password,  
        "role": user.role,
        "points": 0,
        "donor_history": {
            "numberOfDonations": None,
            "totalVolumeDonated": None,
            "firstDonationDate": None,
            "monthsSinceFirstDonation": None,
            "lastDonationDate": None,
            "monthsSinceLastDonation": None
        },
    }

    result = await elastic.index(index="database_users", body=user_data)
    return {"result": "Nouveau compte utilisateur créé", "id": result['_id']}




# Route de connexion 

@router.post("/login")
async def login_user(email: str, password: str):
    result = await elastic.search(index="database_users", body={
        "query": {
            "match": {
                "email": email
            }
        }
    })

    if not result['hits']['hits']:
        raise HTTPException(status_code=404, detail="Utilisateur introuvable")

    user_data = result['hits']['hits'][0]["_source"]
    if user_data["password"] != password:
        raise HTTPException(status_code=400, detail="Mot de passe incorrect")

    return {"message": "Connexion Réussie", "user": user_data}