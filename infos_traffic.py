import requests
import os
import sys
import re
from datetime import datetime
from html.parser import HTMLParser
from dataclasses import dataclass
repertoire_script = os.path.dirname(os.path.abspath(__file__))
sys.path.append(repertoire_script)
from gestion_erreurs import dump_debug
from gestion_arrets import is_between, CODE_TO_NAME
from update_display_code import update_display
from clef_api import API_KEY

"""
TO DO

"""

# --- Utilitaire : nettoyer le HTML ---
class HTMLStripper(HTMLParser):
    def __init__(self):
        super().__init__()
        self.reset()
        self.fed = []

    def handle_data(self, d):
        self.fed.append(d)

    def get_data(self):
        return " ".join(self.fed).strip()


def strip_html(html: str) -> str:
    try:
        stripper = HTMLStripper()
        stripper.feed(html)
        raw = stripper.get_data()
        # Normalise les espaces multiples
        return re.sub(r" {2,}", " ", raw)
    except Exception:
        dump_debug()    

# --- Modèles de données ---
@dataclass
class ImpactedSection:
    line_id: str
    from_id: str
    from_name: str
    to_id: str
    to_name: str
    bidirectional: bool = False


@dataclass
class Disruption:
    application_periods: list[tuple[datetime, datetime]]
    cause: str
    severity: str
    title: str
    message: str
    short_message: str
    impacted_sections: list[ImpactedSection]

def is_active_now(periods: list[tuple[datetime, datetime]]) -> bool:
    now = datetime.now()
    return any(begin <= now <= end for begin, end in periods)

# --- Parsing ---
NAVITIA_FMT = "%Y%m%dT%H%M%S"


def parse_dates(periods: list[dict]) -> list[tuple[datetime, datetime]]:
    try:
        """Retourne la liste des intervalles (begin, end) en datetime."""
        return [
            (
                datetime.strptime(p["begin"], NAVITIA_FMT),
                datetime.strptime(p["end"],   NAVITIA_FMT),
            )
            for p in periods
        ]
    except Exception:
        source, detail_erreur = dump_debug()
        if source !="create_html_template":
            update_display(erreur=detail_erreur)  


def parse_sections(raw_sections: list[dict]) -> list[ImpactedSection]:
    try:
        seen: dict[tuple, ImpactedSection] = {}

        for s in raw_sections:
            line_id   = s["lineId"]
            from_id   = s["from"]["id"]
            from_name = s["from"]["name"]
            to_id     = s["to"]["id"]
            to_name   = s["to"]["name"]

            key         = (line_id, from_id, to_id)
            reverse_key = (line_id, to_id, from_id)

            if reverse_key in seen:
                seen[reverse_key].bidirectional = True
            elif key not in seen:
                seen[key] = ImpactedSection(
                    line_id=line_id,
                    from_id=from_id,
                    from_name=from_name,
                    to_id=to_id,
                    to_name=to_name,
                    bidirectional=False,
                )

        return list(seen.values())
    except Exception:
        source, detail_erreur = dump_debug()
        if source !="create_html_template":
            update_display(erreur=detail_erreur)  


def parse_disruptions(data: dict) -> list[Disruption]:
    try:
        total = []
        for d in data.get("disruptions", []):
            disruption = Disruption(
                application_periods=parse_dates(d["applicationPeriods"]),
                cause=d.get("cause", ""),
                severity=d.get("severity", ""),
                title=d.get("title", ""),
                message=strip_html(d.get("message", "")),
                short_message=d.get("shortMessage", ""),
                impacted_sections=parse_sections(d.get("impactedSections", [])),
            )
            total.append(disruption)
        return total
    except Exception:
        source, detail_erreur = dump_debug()
        if source !="create_html_template":
            update_display(erreur=detail_erreur)  

desserte_stations = [60785, 59948, 478505, 71572, 73620] #les stations qui m'intéressent
timer_disruptions = {}

def filter_disruptions_to_files(api_key=API_KEY):
    try:
        url = "https://prim.iledefrance-mobilites.fr/marketplace/disruptions_bulk/disruptions/v2"
        headers = {
            "apikey": api_key,
            "Accept": "application/json"
        }
        
        target_id = "line:IDFM:C01727"
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        data = response.json()
        # with open("C:/Users/jeanb/OneDrive/Documents/Python/Projet affichage trains/All_disruptions.json","wb") as fdfg:
        #     fdfg.write(str(data).encode('utf8'))
        
        all_disruptions = data.get("disruptions", [])
        
        target_list = []
        non_desservi = []
        arrets_restants = desserte_stations[:]

        for d in all_disruptions:


            sections = d.get("impactedSections", [])
            # On récupère tous les lineId de la disruption
            line_ids = [s.get("lineId") for s in sections if s.get("lineId")]
            
            if target_id in line_ids:
                #cas spécial des arrêts non desservis : on les note mais sans tout afficher
                periods = parse_dates(d["applicationPeriods"])
                if not is_active_now(periods):
                    continue

                if ("arret" in d.get("title","").lower() or "arrêt" in d.get("title","").lower()) and "non desservi" in d.get("title","").lower() or (("arret" in d.get("shortMessage","").lower() or "arrêt" in d.get("shortMessage","").lower()) and "non desservi" in d.get("shortMessage","").lower()):
                    # periods = parse_dates(d["applicationPeriods"])
                    me_concerne=False
                    for s in sections:
                        for arret in arrets_restants:
                            debut = s.get('from').get("id")
                            fin = s.get('to').get("id")
                            # print(is_between(int(debut[debut.rfind(":")+1:]), arret, int(fin[fin.rfind(":")+1:])))
                            if is_between(int(debut[debut.rfind(":")+1:]), arret, int(fin[fin.rfind(":")+1:])):
                                non_desservi.append(CODE_TO_NAME[arret])
                                arrets_restants.remove(arret)
                                me_concerne+True
                    if not me_concerne:
                        continue

                id = d.get("id",'no_id')
                if id in timer_disruptions.keys():
                    if timer_disruptions[id] > 24*60:
                        continue
                    else:
                        timer_disruptions[id] += 1
                else:
                        timer_disruptions[id] = 1

                target_list.append(d)

        # target_list.sort(key=lambda target:timer_disruptions[target.get('id',"no_id")])
        target_json_output = {"disruptions": target_list}
        non_desservi.sort()
        return target_json_output, non_desservi
    except Exception:
        source, detail_erreur = dump_debug()
        if source !="create_html_template":
            update_display(erreur=detail_erreur)
        return  {"disruptions": []},[]

# Utilisation


# --- Exemple d'utilisation ---
if __name__ == "__main__":
    data,non_desservi = filter_disruptions_to_files(API_KEY)

    disruptions = parse_disruptions(data)
    # print(type(disruptions))

    for dis in disruptions:
        print(f"\n{'='*60}")
        print(f"Titre     : {dis.title}")
        print(f"Cause     : {dis.cause}  |  Sévérité : {dis.severity}")
        print(f"Dates app.: {[str(d) for d in dis.application_periods]}")
        print(f"Message   : {dis.message[:120]}...")
        print(f"Court msg : {dis.short_message}")
        print(f"Sections  :")
        for sec in dis.impacted_sections:
            direction = "↔" if sec.bidirectional else "→"
            print(f"  [{sec.line_id}]  {sec.from_name}  {direction}  {sec.to_name}")
    
    print(non_desservi)