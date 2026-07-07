import requests
import csv
import time
import os
import argparse

# Configuration
API_URL = "https://recherche-entreprises.api.gouv.fr/search"
NAF_CODE = "68.31Z"
OUTPUT_FILE = "agences_independantes_france.csv"

# Liste des franchises à exclure (à compléter si besoin)
FRANCHISES = [
    "ORPI", "CENTURY 21", "GUY HOQUET", "ERA", "LAFORET", "STEPHANE PLAZA", 
    "NESTENN", "SQUARE HABITAT", "HUMAN IMMOBILIER", "CLAIRIMMO", "ARTHURIMMO", 
    "L'ADRESSE", "FONCIA", "CITYA", "IMMO DE FRANCE", "ADRIANA", "OPTIMHOME", 
    "IAD", "SAFTI", "CAPIFRANCE", "PROPRIETES-PRIVEES", "REMAX", "KELLER WILLIAMS"
]

def is_independent(name):
    if not name:
        return True
    name_upper = name.upper()
    for franchise in FRANCHISES:
        if franchise in name_upper:
            return False
    return True

def get_departments():
    # Liste des départements français (01-95 + DOM)
    deps = [str(i).zfill(2) for i in range(1, 96)]
    deps.extend(["971", "972", "973", "974", "976"])
    return deps

def extract_agencies(departments=None, output_file=None):
    all_agencies = []
    if departments is None:
        departments = get_departments()
    if output_file is None:
        output_file = OUTPUT_FILE
    
    print(f"Début de l'extraction pour le code NAF {NAF_CODE}...")
    print(f"Départements traités : {', '.join(departments)}")
    
    for dep in departments:
        print(f"Extraction du département {dep}...")
        page = 1
        while True:
            params = {
                "activite_principale": NAF_CODE,
                "etat_administratif": "A",
                "departement": dep,
                "per_page": 25,
                "page": page
            }
            
            try:
                response = requests.get(API_URL, params=params, timeout=10)
                if response.status_code == 404: # Plus de pages
                    break
                response.raise_for_status()
                data = response.json()
                
                results = data.get("results", [])
                if not results:
                    break
                
                for res in results:
                    name = res.get("nom_complet")
                    if is_independent(name):
                        siege = res.get("siege", {})
                        agency = {
                            "Nom": name,
                            "Ville": siege.get("libelle_commune"),
                            "Code Postal": siege.get("code_postal"),
                            "Adresse": siege.get("adresse"),
                            "SIRET": siege.get("siret"),
                            "Date Creation": res.get("date_creation")
                        }
                        all_agencies.append(agency)
                
                page += 1
                # Respecter les limites de l'API (7 requêtes/sec pour l'API publique)
                time.sleep(0.2)
                
            except Exception as e:
                print(f"Erreur sur le département {dep}, page {page}: {e}")
                break
                
    # Sauvegarde en CSV
    if all_agencies:
        keys = all_agencies[0].keys()
        with open(output_file, 'w', newline='', encoding='utf-8') as f:
            dict_writer = csv.DictWriter(f, fieldnames=keys)
            dict_writer.writeheader()
            dict_writer.writerows(all_agencies)
        print(f"Extraction terminée ! {len(all_agencies)} agences indépendantes trouvées.")
    else:
        # On écrit quand même un CSV vide avec les en-têtes attendus,
        # pour que l'étape de fusion ne plante pas si un shard n'a rien trouvé.
        with open(output_file, 'w', newline='', encoding='utf-8') as f:
            dict_writer = csv.DictWriter(f, fieldnames=["Nom", "Ville", "Code Postal", "Adresse", "SIRET", "Date Creation"])
            dict_writer.writeheader()
        print("Aucune agence trouvée.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Extraction des agences immobilières indépendantes")
    parser.add_argument(
        "--departments",
        type=str,
        default=None,
        help="Liste de départements séparés par des virgules (ex: 01,02,03). Par défaut : tous les départements."
    )
    parser.add_argument(
        "--output",
        type=str,
        default=None,
        help="Nom du fichier CSV de sortie. Par défaut : agences_independantes_france.csv"
    )
    args = parser.parse_args()

    dep_list = args.departments.split(",") if args.departments else None
    extract_agencies(departments=dep_list, output_file=args.output)
