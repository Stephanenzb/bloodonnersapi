from fastapi import APIRouter, HTTPException
from elasticsearch import Elasticsearch

router = APIRouter()

# Connexion à Elasticsearch
elastic = Elasticsearch(
    cloud_id="b01a042efef84182a85f799130f733f5:ZXVyb3BlLXdlc3QzLmdjcC5jbG91ZC5lcy5pbzo0NDMkNTU3NDM0YTQxNDI0NGVlYzk0NDUzZWM2YWIxZjc3N2EkNWY1ZDA0ZjVkMDAwNDc2MGFjOWUwMjYyZTk0ZTBjZjI=",
    http_auth=("elastic", "bvfN5fngmOAhCViV4cuVcHIX"),
)



# Tableau listes des donneurs 
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












# Lancer une notification
@router.post("/admin/notify")
async def notify_donor(email: str, message: str):
    # Logique pour envoyer une notification
    return {"message": "Notification envoyée au donneur", "email": email}



# Lancer la probabilité
@router.get("/admin/probabilities")
async def analyze_probabilities():
    # Logique pour analyser et récupérer les probabilités de dons
    return {"message": "Probabilités analysées"}


# Supprimer un donneur
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








