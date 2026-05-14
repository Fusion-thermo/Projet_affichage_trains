from time import sleep
from datetime import datetime, time
import sys
import os
# import requests
from requests.exceptions import ConnectionError, Timeout, HTTPError, RequestException

repertoire_script = os.path.dirname(os.path.abspath(__file__))
sys.path.append(repertoire_script)
from horaires_rer_c import get_prim_schedules, traitements, log_trains
from gestion_erreurs import dump_debug
from infos_traffic import filter_disruptions_to_files, parse_disruptions
from update_display_code import update_display
from heures_debut_fin import PAUSE_DEBUT, PAUSE_FIN
from clef_api import API_KEY

# --- CONFIGURATION ---
STOP_POINT_ID = "STIF:StopArea:SP:43188:" #sainte-geneviève-des-bois



def parse_heure(h_str):
    try:
        h, m = h_str.split("h")
        return time(int(h), int(m) if m else 0)
    except Exception:
        source, detail_erreur = dump_debug()
        if source !="create_html_template":
            update_display(erreur=detail_erreur)
        return (1,1)

# --- BOUCLE PRINCIPALE ---
debut_pause = parse_heure(PAUSE_DEBUT)
fin_pause   = parse_heure(PAUSE_FIN)
memoire = {}
if __name__ == "__main__":
    while True:
        try:
            try:
                trains = get_prim_schedules(API_KEY, STOP_POINT_ID)
                etat_connexion=""
            except ConnectionError:
                trains = []
                etat_connexion="Pas de connexion"
            except Timeout:
                trains = []
                etat_connexion = "Délai d'attente dépassé"
            except HTTPError as e:
                trains = []
                etat_connexion= f"Erreur HTTP : {e.response.status_code}"
            except RequestException as e:
                trains = []
                etat_connexion = f"Erreur inattendue : {e}"

            trains_nord, trains_sud, memoire = traitements(trains, memoire) 
            mes_trains_nord = [vars(i) for i in trains_nord]
            mes_trains_sud = [vars(i) for i in trains_sud]
            log_trains(trains)
            
            
            data, non_desservi = filter_disruptions_to_files(API_KEY)
            disruptions = parse_disruptions(data)
            
            update_display(mes_trains_nord, mes_trains_sud, etat_connexion, disruptions, non_desservi)

            #update every minute
            last_minute = datetime.now().minute
            while datetime.now().minute == last_minute:
                sleep(1)

            # Pause nocturne
            while datetime.now().time() >= debut_pause and datetime.now().time() < fin_pause:
                last_minute = datetime.now().minute
                update_display([],[], nuit=True)
                while datetime.now().minute == last_minute:
                    sleep(2)

        except Exception as e:
            update_display()
            source, detail_erreur = dump_debug()
            if source !="create_html_template":
                update_display(erreur=detail_erreur)
            sleep(10)