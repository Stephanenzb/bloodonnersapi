from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from elasticsearch import Elasticsearch, AsyncElasticsearch
from jose import JWTError, jwt
import secrets
from pydantic import BaseModel
from datetime import datetime, timedelta
import math


router = APIRouter()




# Modèle pour l'inscription
class User(BaseModel):
    email: str
    username: str
    password: str
    role: str 


# Connexion à Elasticsearch
elastic = AsyncElasticsearch(
    cloud_id="b01a042efef84182a85f799130f733f5:ZXVyb3BlLXdlc3QzLmdjcC5jbG91ZC5lcy5pbzo0NDMkNTU3NDM0YTQxNDI0NGVlYzk0NDUzZWM2YWIxZjc3N2EkNWY1ZDA0ZjVkMDAwNDc2MGFjOWUwMjYyZTk0ZTBjZjI=",
    http_auth=("elastic", "bvfN5fngmOAhCViV4cuVcHIX"),
)

SECRET_KEY = "ton_secret_key"  # A stocker dans les variables d'environnement
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

def create_access_token(data: dict):
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt





# Route d'enregistrement 

@router.post("/register")
async def register_user(user: User):
    try:
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
            "username" : user.username,
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
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))





# Route de connexion 

from datetime import datetime, timedelta


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
    
    # Renvoie le rôle et le jeton
    return {"token": "JWT_TOKEN_HERE", "role": user_data["role"]}

