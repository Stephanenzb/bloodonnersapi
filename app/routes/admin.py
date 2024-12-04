from fastapi import FastAPI,APIRouter, HTTPException
from elasticsearch import Elasticsearch
from datetime import datetime, timedelta
import joblib 
import numpy as np
import os
import uvicorn
import pandas as pd
from google.cloud import storage
from pydantic import BaseModel
from tensorflow.keras.models import load_model
from sklearn.preprocessing import StandardScaler


app = FastAPI()


router = APIRouter()

# Connexion à Elasticsearch
elastic = Elasticsearch(
    cloud_id="PA2024:ZXVyb3BlLXdlc3Q5LmdjcC5lbGFzdGljLWNsb3VkLmNvbSQ4Yjk5MjQxNjBmNjc0ODdmYjViMTJlZDhiNmIxYWVlZSQyOThmMDU0ZjE2YjQ0NmMzOThkMzMzNjE1MzZhNDlmMg==",
    http_auth=("elastic", "6EPhppu8hMfSwYZ9reTWfFnv"),
)

# PAGE ADMIN HOME

#TOP 3 DONNEURS
@router.get("/admin/top3-donors")
async def get_top3_donors():
    try:
        response = elastic.search(index="database_users", body={
            "query": {
                "match": {
                    "role": "donor"
                }
            },
            "size": 1000
        })

        donors = response['hits']['hits']
        donor_data = [{
            "username": donor["_source"].get("username"),
            "email": donor["_source"].get("email"),
            "points": int(donor["_source"].get("points", 0)) 
        } for donor in donors]

        top_donors = sorted(donor_data, key=lambda x: x['points'], reverse=True)[:3]

        return top_donors
    except Exception as e:
        return {"error": str(e)}





# PAGE LISTE DES DONNEURS 

# AFFICHAGE DE LA LISTE DES DONNEURS 
@router.get("/admin/donors")
async def get_donors():
    try:
        result = elastic.search(index="database_users", body={
            "query": {
                "match": {
                    "role": "donor"
                }
            }
        })

        print("Les donneurs trouvés :", result['hits']['total']['value'])  

        donors = []
        for hit in result['hits']['hits']:
            source = hit["_source"]
            donors.append(source)  

        return {"donors": donors}

    except Exception as e:
        print(f"Erreur dans l'extraction des donateurs: {e}")
        return {"Erreur": "Erreur du serveur interne"}, 500
    



# SUPPRIMER UN DONNEUR
@router.delete("/donors/{email}")
async def delete_donor(email: str):
    result = elastic.delete_by_query(index="database_users", body={
        "query": {
            "match": {
                "email": email
            }
        }
    })

    if result['deleted'] == 0:
        raise HTTPException(status_code=404, detail="Donneur non trouvé")

    return {"message": f"Donneur avec l'email {email} supprimé"}




# MISE A JOUR DES DONNÉES D'UN DONNEUR
@router.put("/donors/{email}")
async def update_donor(email: str, donor_data: dict):
    # VERIFIE SI L'EMAIL EXISTE
    result = elastic.search(index="database_users", body={
        "query": {
            "match": {
                "email": email
            }
        }
    })

    if result['hits']['total']['value'] == 0:
        raise HTTPException(status_code=404, detail="Donneur non trouvé")

    # Calcule les mois depuis le premier et le dernier don
    months_since_first = calculate_months_since(donor_data.get("firstDonationDate"))
    months_since_last = calculate_months_since(donor_data.get("lastDonationDate"))

    # Met à jour les informations de l'utilisateur
    try:
        elastic.update_by_query(index="database_users", body={
            "script": {
                "source": """
                    if (params.points != null) { ctx._source.points = params.points; }
                    if (params.numberOfDonations != null) { ctx._source.donor_history.numberOfDonations = params.numberOfDonations; }
                    if (params.totalVolumeDonated != null) { ctx._source.donor_history.totalVolumeDonated = params.totalVolumeDonated; }
                    if (params.firstDonationDate != null) { ctx._source.donor_history.firstDonationDate = params.firstDonationDate; }
                    if (params.lastDonationDate != null) { ctx._source.donor_history.lastDonationDate = params.lastDonationDate; }
                    ctx._source.donor_history.monthsSinceFirstDonation = params.monthsSinceFirstDonation;
                    ctx._source.donor_history.monthsSinceLastDonation = params.monthsSinceLastDonation;
                """,
                "params": {
                    "points": donor_data.get("points"),
                    "numberOfDonations": donor_data.get("numberOfDonations"),
                    "totalVolumeDonated": donor_data.get("totalVolumeDonated"),
                    "firstDonationDate": donor_data.get("firstDonationDate"),
                    "lastDonationDate": donor_data.get("lastDonationDate"),
                    "monthsSinceFirstDonation": months_since_first,
                    "monthsSinceLastDonation": months_since_last
                }
            },
            "query": {
                "match": {
                    "email": email
                }
            }
        })
        return {"message": f"Informations de {email} mises à jour"}
    except Exception as e:
        raise HTTPException(status_code=500, detail="Erreur lors de la mise à jour : " + str(e))

def calculate_months_since(date_str):
    if date_str:
        # Logique pour calculer les mois depuis la date fournie
        first_date = datetime.strptime(date_str, '%Y-%m-%d')
        now = datetime.now()
        return (now.year - first_date.year) * 12 + now.month - first_date.month
    return 0  












# PAGE LISTE DES RENDEZ-VOUS

# AFFICHAGE DES RENDEZ-VOUS
@router.get("/admin/appointments")
async def get_appointments():
    appointments = elastic.search(index="appointments", body={"query": {"match_all": {}}})
    
    current_datetime = datetime.now()
    
    for appointment in appointments['hits']['hits']:
        # Convertir la date et l'heure du rendez-vous
        appointment_datetime_str = f"{appointment['_source']['dateRendezVous']} {appointment['_source']['timeRendezVous']}"
        appointment_datetime = datetime.strptime(appointment_datetime_str, '%Y-%m-%d %H:%M')

        # Mettre à jour le statut automatiquement en fonction de la date et de l'heure
        if appointment['_source']['status'] != "Effectué":
            if appointment_datetime < current_datetime:
                appointment['_source']['status'] = "Passé"
            else:
                appointment['_source']['status'] = "Programmé"

    return appointments


# SUPPRESSION D'UN RENDEZ-VOUS
@router.delete("/appointments/{donorEmail}")
async def delete_appointment(donorEmail: str):
    result = elastic.delete_by_query(index="appointments", body={
        "query": {
            "match": {
                "donorEmail": donorEmail
            }
        }
    })

    if result['deleted'] == 0:
        raise HTTPException(status_code=404, detail=f"Aucun rendez-vous trouvé pour {donorEmail}")

    return {"message": f"Rendez-vous pour le donneur {donorEmail} supprimé avec succès"}




@router.put("/appointments/{donorEmail}")
async def update_appointment(donorEmail: str, updatedData: dict):
    # Obtenir le rendez-vous à modifier
    appointment = elastic.search(index="appointments", body={
        "query": {
            "match": {
                "donorEmail": donorEmail
            }
        }
    })

    if not appointment['hits']['hits']:
        raise HTTPException(status_code=404, detail="Rendez-vous non trouvé")
    
    # Mettre à jour les champs avec les données fournies
    elastic.update(
        index="appointments",
        id=appointment['hits']['hits'][0]['_id'],
        body={"doc": updatedData}
    )

    # Mettre à jour les données du donneur si le statut est "Effectué"
    if updatedData.get('status') == "Effectué":
        volume_taken = updatedData.get('volumeTaken', 0)  # Volume de sang prélevé
        donor_email = donorEmail  # Email du donneur

        # Récupérer les informations actuelles du donneur
        donor = elastic.search(index="database_users", body={
            "query": {
                "match": {
                    "email": donor_email
                }
            }
        })

        if donor['hits']['hits']:
            donor_data = donor['hits']['hits'][0]['_source']

            # Calculer les nouvelles valeurs
            new_volume = donor_data['donor_history']['totalVolumeDonated'] + float(volume_taken)
            new_donations = donor_data['donor_history']['numberOfDonations'] + 1
            new_points = donor_data['points'] + 100  # Points à attribuer
            new_last_donation_date = updatedData['dateRendezVous']  # Date du dernier don

            # Mettre à jour les informations du donneur
            elastic.update(
                index="database_users",
                id=donor['hits']['hits'][0]['_id'],
                body={
                    "doc": {
                        "donor_history": {
                            "totalVolumeDonated": new_volume,
                            "numberOfDonations": new_donations,
                            "lastDonationDate": new_last_donation_date
                        },
                        "points": new_points
                    }
                }
            )

    return {"message": "Rendez-vous et données du donneur mis à jour"}


@router.get("/centers")
def get_centers():
    try:
        # Requête pour récupérer tous les documents
        response = elastic.search(
            index="health_centers",
            scroll="2m",  # Durée pendant laquelle le scroll reste actif
            body={"query": {"match_all": {}}},
            size=1000  # Nombre de documents par batch
        )

        scroll_id = response["_scroll_id"]
        hits = response["hits"]["hits"]

        # Récupérer tous les documents
        all_centers = [
            {
                "id": hit["_id"],
                "name": hit["_source"].get("index", {}).get("name", ""),
                "amenity": hit["_source"].get("index", {}).get("amenity", ""),
                "location": hit["_source"].get("index", {}).get("location", {}),
                "geometry": hit["_source"].get("index", {}).get("geometry", {}),
                "region": hit["_source"].get("index", {}).get("region", ""),
                "address": hit["_source"].get("index", {}).get("address", ""),
                "updated_at": hit["_source"].get("index", {}).get("updated_at", "")
            }
            for hit in hits
        ]

        while len(hits) > 0:
            response = elastic.scroll(scroll_id=scroll_id, scroll="2m")
            hits = response["hits"]["hits"]
            all_centers.extend([
                {
                    "id": hit["_id"],
                    "name": hit["_source"].get("index", {}).get("name", ""),
                    "amenity": hit["_source"].get("index", {}).get("amenity", ""),
                    "location": hit["_source"].get("index", {}).get("location", {}),
                    "geometry": hit["_source"].get("index", {}).get("geometry", {}),
                    "region": hit["_source"].get("index", {}).get("region", ""),
                    "address": hit["_source"].get("index", {}).get("address", ""),
                    "updated_at": hit["_source"].get("index", {}).get("updated_at", "")
                }
                for hit in hits
            ])

        return {"success": True, "data": all_centers}
    except Exception as e:
        return {"success": False, "error": str(e)}







# Lancer une notification
@router.post("/admin/notify")
async def notify_donor(email: str, message: str):
    return {"message": "Notification envoyée au donneur", "email": email}




