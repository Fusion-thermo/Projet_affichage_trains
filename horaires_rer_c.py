import requests
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
import os
import sys
import json
import hashlib

repertoire_script = os.path.dirname(os.path.abspath(__file__))
sys.path.append(repertoire_script)
from gestion_erreurs import dump_debug
from update_display_code import update_display
from clef_api import API_KEY

"""
TO DO
afficher le dernier train prévu d'une station donnée
afficher une autre station en touchant l'écran
"""




"""
Notez que depuis le 13/03/2025, les données Prochains Passages SNCF sont disponibles uniquement par zone d'arrêt « ZdAid », que vous pouvez retrouver dans ce référentiel, L'identifiant d'une zone d'arrêt doit être passé sous la forme :

STIF:StopArea:SP:XXXXX: avec XXXXX l’identifiant du référentiel des Zones d'arrêts

https://prim.iledefrance-mobilites.fr/fr/jeux-de-donnees/zones-d-arrets
https://prim.iledefrance-mobilites.fr/fr/jeux-de-donnees/referentiel-des-lignes

"""

# --- CONFIGURATION ---
# Exemple d'identifiant d'arrêt (StopPoint). 
STOP_POINT_ID = "STIF:StopPoint:Q:463158:" #FONCTIONNE pour l'arrêt de métro châtelet
STOP_POINT_ID = "STIF:StopArea:SP:43159:" #FONCTIONNE MAROLLES
STOP_POINT_ID = "STIF:StopArea:SP:43188:" #sainte geneviève fonctionne
LINE_ID = "STIF:Line::C01727:" # Identifiant unique du RER C

class Train:
    def __init__(self, code, destination, arrivee, arrivee_initiale, depart, stopped, retard, numero_train, habituel=False):
        self.code_mission = code
        self.destination = destination
        self.arrivee = arrivee
        self.depart = depart
        self.immobile = stopped
        self.retard = retard
        self.numero_train = numero_train
        self.key = numero_train+code

        self.orientation=""
        self.couleur = ""

        self.extra = ""
        self.arrivee_initiale = arrivee_initiale
        self.arrivee_prec = arrivee_initiale
        self.nb_decalage = 0

        self.habituel=habituel

    def should_be_logged(self):
        return self.retard != "onTime" or self.extra != ""
    
    def get_hash(self):
        """Crée un hash court basé sur l'identité, l'état et l'heure (sans les minutes pour la comparaison libre)."""
        signature = f"{self.code_mission}|{self.destination}|{self.retard}|{self.immobile}|{self.extra}"
        return hashlib.md5(signature.encode()).hexdigest()[:10]

def log_trains(train_list):
    try:
        now = datetime.now()
        filename = f"{repertoire_script}/trains_{now.strftime('%Y-%m-%d')}.log"
        precision_minutes = 5
        
        history = []
        if os.path.exists(filename):
            with open(filename, "r", encoding="utf-8") as f:
                for line in f:
                    try:
                        history.append(json.loads(line))
                    except: continue

        with open(filename, "a", encoding="utf-8") as f:
            for train in train_list:
                if not train.should_be_logged():
                    continue
                    
                current_hash = train.get_hash()
                d1 = datetime.strptime(train.arrivee, "%H:%M")
                
                is_duplicate = False
                for entry in history:
                    # On compare le hash (qui contient code, destination, retard, stopped, extra)
                    # ET la proximité temporelle de l'arrivée
                    if entry.get('hash_id') == current_hash:
                        d2 = datetime.strptime(entry['arrivee'], "%H:%M")
                        if abs((d1 - d2).total_seconds()) / 60 <= precision_minutes:
                            is_duplicate = True
                            break
                
                if not is_duplicate:
                    data = train.__dict__.copy()
                    data['hash_id'] = current_hash  # On stocke le hash pour la prochaine lecture
                    f.write(json.dumps(data, default=str) + "\n")
                    history.append(data)
    except Exception:
        source, detail_erreur = dump_debug()
        if source !="create_html_template":
            update_display(erreur=detail_erreur)    

def get_prim_schedules(api_key, stop_id):
    try:
        url = "https://prim.iledefrance-mobilites.fr/marketplace/stop-monitoring"
        # Requête : https://prim.iledefrance-mobilites.fr/marketplace/stop-monitoring?MonitoringRef=STIF:StopPoint:Q:463158:
        
        headers = {
            "apikey": api_key,
            "Accept": "application/json"
        }
        
        params = {
            "MonitoringRef": stop_id,
        }

        response = requests.get(url, headers=headers, params=params)
        response.raise_for_status()
        data = response.json()

        # Navigation dans l'arborescence SIRI Lite
        debut = data.get('Siri', {}).get('ServiceDelivery', {}).get('StopMonitoringDelivery', [{}])[0]
        StopMonitoringDelivery = debut.get('MonitoredStopVisit', [])
        # print(StopMonitoringDelivery)
        # destinationRef = debut.get('DestinationRef', [])

        # print(f"--- Prochains passages (PRIM) ---")
        if not StopMonitoringDelivery:
            # print("Aucun train détecté ou identifiants incorrects.")
            return []

        all_trains = []
        for visit in StopMonitoringDelivery:
            journey = visit.get('MonitoredVehicleJourney', {})
            destination = journey.get('DestinationName', [{}])[0].get('value', 'Inconnue')
            if "Saint-Quentin en Yvelines" in destination:
                destination="Saint-Quentin en Yvelines"
            code_mission = journey.get('JourneyNote', [{}])[0].get('value', 'Inconnue')
            numero_train = journey.get('VehicleJourneyName', [{}])[0].get('value', 'Inconnue')
            #sens = journey.get('DirectionRef', {}).get('value', 'Inconnue') #Aller ou Retour : pas suffisant pour indiquer la direction

            # print(code,sens)
            
            # Récupération de l'heure 
            monitored_call = journey.get('MonitoredCall', {})
            expected_arrival_time_str = monitored_call.get('ExpectedArrivalTime')
            aimed_departure_time_str = monitored_call.get('AimedDepartureTime')
            # print(expected_arrival_time_str, aimed_departure_time_str)
            stopped = monitored_call.get('VehicleAtStop')
            retard = monitored_call.get('DepartureStatus')
            
            # Formatage de l'heure pour la lisibilité
            dt_expected = datetime.fromisoformat(expected_arrival_time_str.replace('Z', '+00:00'))
            dt_paris_expected = dt_expected.astimezone(ZoneInfo("Europe/Paris"))
            maintenant_paris = datetime.now(ZoneInfo("Europe/Paris"))
            if dt_paris_expected < maintenant_paris + timedelta(minutes=4):#même en courant on ne l'atteint pas
                continue
            heure_expected_formatee = dt_paris_expected.strftime("%H:%M")
            heure_expected_initiale = dt_paris_expected
            dt_aimed = datetime.fromisoformat(aimed_departure_time_str.replace('Z', '+00:00'))
            dt_paris_aimed = dt_aimed.astimezone(ZoneInfo("Europe/Paris"))
            heure_aimed_formatee = dt_paris_aimed.strftime("%H:%M")

            # print(f"{code_mission} | {destination:<20} | {heure_expected_formatee} | {heure_aimed_formatee} | Stoppé : {stopped} | {retard}")
            all_trains.append(Train(code_mission, destination, heure_expected_formatee, heure_expected_initiale, heure_aimed_formatee, stopped, retard, numero_train))

        return all_trains
    except Exception:
        source, detail_erreur = dump_debug()
        if source !="create_html_template":
            update_display(erreur=detail_erreur)
        return []

sud = ['B','E','D']
couleurs_contrastees = [
    "#f1c40f",  # Jaune Tournesol (Complémentaire classique)
    "#e67e22",  # Orange Carotte (Contraste thermique)
    "#2ecc71",  # Émeraude (Fraîcheur et clarté)
    "#1abc9c",  # Turquoise (Harmonie lumineuse)
    "#fd79a8",  # Rose Persan (Douceur contrastée)
    "#badc58",  # Vert Citron (Haute visibilité)
    "#f39c12",  # Orange Orange (Éclatant)
    "#8e44ad",
    "#00ffea",  # Cyan Électrique (Effet néon garanti)
    "#fff200",  # Jaune Canari (Luminosité pure)
    "#ff9ff3",  # Rose Bonbon (Contraste doux mais marqué)
    "#fab1a0",  # Corail Pâle (Chaleur discrète)
    "#a29bfe",  # Bleu Lavande (Contraste de teinte, harmonie proche)
    "#ffeaa7",  # Jaune Paille (Doux pour les yeux)
    "#ff7675",  # Rose Corail (Vibrant)
]

trains_habituels = [("ELBA","07:55"),("ELBA","08:25"),("KNAK","08:04")]
precision_habitude = 3 #plus ou moins de minutes autour de l'heure prévue

repertoire_script = os.path.dirname(os.path.abspath(__file__))
with open(repertoire_script+"/dico_couleurs.txt","r") as fichier:
    dico_couleurs = eval(fichier.read())

def traitements(trains, memoire={}):
    try:
        trains_sud = []
        trains_nord = []
        old_memoire = memoire.copy()
        memoire = {}
        for train in trains:
            #orientation
            if train.code_mission[0] in sud:
                train.orientation="sud"
                trains_sud.append(train)
            else:
                train.orientation="nord"
                trains_nord.append(train)
            #couleur
            if train.code_mission in dico_couleurs.keys():
                train.couleur=dico_couleurs[train.code_mission]
            elif len(dico_couleurs) < len(couleurs_contrastees):
                i=0
                while couleurs_contrastees[i] in dico_couleurs.values():
                    i+=1
                dico_couleurs[train.code_mission] = couleurs_contrastees[i]
                train.couleur=couleurs_contrastees[i]
                with open(repertoire_script+"/dico_couleurs.txt","w") as fichier:
                    fichier.write(str(dico_couleurs))
            else:
                train.couleur="#e74c3c"
            #mémoire des retards
            if train.key in old_memoire.keys():
                maintenant = datetime.now()
                heure_cible = maintenant.replace(
                    hour=int(train.arrivee.split(':')[0]), 
                    minute=int(train.arrivee.split(':')[1]), 
                    second=0, 
                    microsecond=0
                    )
                if heure_cible > maintenant:
                    if train.retard != "onTime":
                        if train.arrivee_prec + timedelta(minutes=5) < heure_cible.replace(tzinfo=ZoneInfo("Europe/Paris")):
                            train.arrivee_prec = heure_cible
                            train.nb_decalage = old_memoire[train.key].nb_decalage + 1
                            train.extra = f"Heure prévue initiale {train.arrivee_initiale.strftime('%H:%M')} décalée {train.nb_decalage} fois."
                        if train.immobile: train.extra+= " Train à l'arrêt."
                        train.arrivee = heure_cible.strftime("%H:%M")
                    
                    memoire[train.key] = train
            else:
                memoire[train.key] = train 
            #habitude
            for habitude in trains_habituels:
                d1 = datetime.strptime(train.arrivee, "%H:%M")
                d2 = datetime.strptime(habitude[1], "%H:%M")
                if train.code_mission == habitude[0] and abs((d1 - d2).total_seconds()) / 60 <= precision_habitude:
                    train.habituel=True
                    break


        return trains_nord, trains_sud, memoire       
    except Exception:
        source, detail_erreur = dump_debug()
        if source !="create_html_template":
            update_display(erreur=detail_erreur)
        return [],[],{}



# Lancement
if __name__ == "__main__":
    trains = get_prim_schedules(API_KEY, STOP_POINT_ID)
    trains_nord, trains_sud, memoire = traitements(trains) 
    for i in trains_nord:
        print(vars(i))

