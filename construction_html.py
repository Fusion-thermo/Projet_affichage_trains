from datetime import datetime
import sys
import os
# import requests
repertoire_script = os.path.dirname(os.path.abspath(__file__))
sys.path.append(repertoire_script)
from heures_debut_fin import PAUSE_DEBUT, PAUSE_FIN
from gestion_erreurs import dump_debug
from last_try import manual_debug

MAX_TRAINS_DISPLAY = 6


def couleur_texte_optimale(hex_fond):
    try:
        hex_fond = hex_fond.lstrip('#')
        r, g, b = tuple(int(hex_fond[i:i+2], 16) for i in (0, 2, 4))
        rn, gn, bn = r / 255, g / 255, b / 255
        luminance = 0.2126 * rn + 0.7152 * gn + 0.0722 * bn
        return "#000000" if luminance > 0.5 else "#ffffff"
    except Exception:
        dump_debug(source="create_html_template")
        manual_debug()
        return "#000000"

def minutes_restantes(heure_arrivee_str):
    try:
        now = datetime.now()
        heure_arr = datetime.strptime(heure_arrivee_str, "%H:%M").replace(
            year=now.year, month=now.month, day=now.day
        )
        diff = (heure_arr - now).total_seconds() / 60
        if diff < -60:
            diff += 24 * 60
        return int(diff)
    except Exception:
        dump_debug(source="create_html_template")
        manual_debug()
        return 666

def format_remaining(mins):
    try:
        """Formate le temps restant : '12 mn' ou '1h19' si >= 60 mn."""
        if mins >= 60:
            h = mins // 60
            m = mins % 60
            return f"{h}h{m:02d}"
        else:
            return f"{mins} mn"
    except Exception:
        dump_debug(source="create_html_template")
        manual_debug()
        return "999 mn"

INFO_PANEL_MAX_HEIGHT = 150  # px — hauteur maximale de l'encadré bas de page

def create_html_template(trains_nord=[], trains_sud=[], erreur="", disruptions=[], non_desservi=[], nuit=False):
    try:
        now_time = datetime.now().strftime("%H:%M")
 
        # ── Contenu de l'encadré bas de page ─────────────────────────────────
        panel_items = []
 
        if erreur:
            panel_items.append(f'<div class="panel-error">{erreur}</div>')
        elif nuit:
            panel_items.append(f'<div class="panel-msg">Pas de requêtes entre {PAUSE_DEBUT} et {PAUSE_FIN}</div>')
        elif trains_nord == [] and trains_sud == []:
            panel_items.append(f'<div class="panel-msg">Aucun train ne circule actuellement.</div>')
        if non_desservi != []:
            texte = f'<div class="panel-msg">Arrêt{"s"*min(1,len(non_desservi))} non desservi{"s"*min(1,len(non_desservi))} : '
            for arret in non_desservi:
                texte+=arret+", "
            texte = texte[:-2] + "</div>"
            panel_items.append(texte)
        for dis in disruptions:
            panel_items.append(f'<div class="panel-info-traffic">{dis.short_message} : {dis.message}</div>')
 
 
        panel_html = ""
        if panel_items:
            panel_html = f"""
        <div class="info-panel">
            {''.join(panel_items)}
        </div>"""
        # ─────────────────────────────────────────────────────────────────────
 
        def render_list(trains):
            try:
                rows = ""
                for i, t in enumerate(trains[:MAX_TRAINS_DISPLAY]):
                    bg_color = "rgba(0, 70, 227, 1)" if i % 2 == 0 else "transparent"
                    mission_bg = t.get('couleur', '#444')
                    extra_html = f'<div class="extra">{t["extra"]}</div>' if t.get('extra') else ""
                    retard_html = f'<div class="retard">{t["retard"]}</div>' if t.get('retard') != "onTime" else ""
 
                    mins = minutes_restantes(t['arrivee'])
                    if mins is not None and mins >= 0:
                        if t.get('nb_decalage') > 0 : 
                            ajouter=" ou plus" 
                        else:
                            ajouter=""
                        remaining_html = f'<span class="remaining">{format_remaining(mins)}{ajouter}</span>'
                    else:
                        remaining_html = '<span class="remaining"></span>'
 
                    # Bordure verte si le train est à l'heure habituelle
                    habituel_style = "border-left: 20px solid #00cc66;" if t.get('habituel') else ""
 
                    rows += f"""
                    <div class="row" style="background-color: {bg_color}; {habituel_style}">
                        <div class="mission" style="background-color: {mission_bg}; color:{couleur_texte_optimale(mission_bg)};">{t['code_mission']}</div>
                        <div class="details">
                            <div class="top-line">
                                <span class="dest">{t['destination']}</span>
                                <div class="time-block">
                                    <span class="time">{t['arrivee']}</span>
                                    {retard_html}
                                </div>
                                {remaining_html}
                            </div>
                            {extra_html}
                        </div>
                    </div>
                    """
                return rows
            except Exception as e:
                dump_debug(source="create_html_template")
                manual_debug()
                return f"Erreur {e}"
 
        return f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <meta http-equiv="refresh" content="2">
        <style>
            body {{ 
                background: #001f3f; color: white; font-family: sans-serif; 
                margin: 0; padding: 0; width: 1024px; height: 600px; overflow: hidden;
                display: flex; flex-direction: column;
            }}
            .header {{ 
                background: rgba(0,0,0,0.6); padding: 10px 25px; 
                display: flex; justify-content: space-between; align-items: center;
                border-bottom: 2px solid #ffcc00;
                flex-shrink: 0;
            }}
            .header h1 {{ margin: 0; font-size: 20px; letter-spacing: 2px; color: #ccc; }}
            .clock {{ font-family: monospace; font-size: 24px; color: #ffcc00; font-weight: bold; }}
 
            .container {{
                display: flex;
                flex: 1;
                min-height: 0;       /* permet la compression quand l'encadré est présent */
                overflow: hidden;
            }}
            .col {{ flex: 1; display: flex; flex-direction: column; min-width: 0; overflow: hidden; }}
            .col-nord {{ border-right: 1px solid rgba(255,255,255,0.1); }}
            .col-title {{ 
                background: #003366; text-align: center; padding: 8px; 
                font-weight: 900; letter-spacing: 4px; border-bottom: 1px solid rgba(255,204,0,0.3);
                color: #ccc; flex-shrink: 0;
            }}
 
            .row {{
                display: flex; min-height: 70px;
                border-bottom: 1px solid rgba(255,255,255,0.1);
                /* La bordure verte est injectée en style inline sur chaque row habituelle */
            }}
            .mission {{ 
                width: 90px; display: flex; align-items: center; justify-content: center;
                font-weight: bold; font-size: 22px; flex-shrink: 0;
            }}
            .details {{
                flex: 1; padding: 6px 10px;
                display: flex; flex-direction: column; justify-content: center;
                min-width: 0;
            }}
            .top-line {{ display: flex; align-items: center; gap: 10px; }}
            .dest {{
                flex: 1; font-size: 20px; font-weight: 600;
                text-transform: uppercase; min-width: 0;
                word-break: break-word; line-height: 1.2;
            }}
            .time-block {{
                flex-shrink: 0; width: 88px;
                display: flex; flex-direction: column;
                align-items: flex-end; justify-content: center;
            }}
            .time {{ font-size: 28px; font-weight: bold; color: #ffcc00; line-height: 1; }}
            .retard {{ color: #ff4444; font-size: 13px; font-weight: bold; margin-top: 2px; }}
            .remaining {{
                flex-shrink: 0; width: 54px;
                font-size: 16px; font-weight: 600;
                color: #7ecfff; text-align: right;
            }}
            .extra {{ 
                font-size: 13px; color: #aaa; font-style: italic; margin-top: 4px;
                border-left: 2px solid #ffcc00; padding-left: 8px;
            }}
 
            /* ── Encadré bas de page ────────────────────────────────────────── */
            .info-panel {{
                flex-shrink: 0;
                max-height: {INFO_PANEL_MAX_HEIGHT}px;
                overflow-y: auto;
                background: rgba(0, 0, 0, 0.55);
                border-top: 1px solid rgba(255, 255, 255, 0.15);
                padding: 8px 16px;
                display: flex;
                flex-direction: column;
                gap: 4px;
            }}
            .panel-error {{
                color: #ff6b6b;
                font-size: 13px;
                font-weight: bold;
                font-family: monospace;
            }}
            .panel-msg {{
                color: #e8e8e8;
                font-size: 20px;
                line-height: 1.5;
                padding: 2px 0;
            }}
            .panel-info-traffic {{
                color: #ffcc00;
                font-size: 17px;
                line-height: 1.5;
                padding: 2px 0;
            }}
            
            /* ────────────────────────────────────────────────────────────────── */
 
            * {{ cursor: none; }}
        </style>
    </head>
    <body>
        <div class="header">
            <h1>Sainte-Geneviève-des-Bois</h1>
            <div class="clock">{now_time}</div>
        </div>
        <div class="container">
            <div class="col col-nord">
                <div class="col-title">NORD</div>
                {render_list(trains_nord)}
            </div>
            <div class="col">
                <div class="col-title">SUD</div>
                {render_list(trains_sud)}
            </div>
        </div>
        {panel_html}
    </body>
    </html>
    """
    except Exception:
        dump_debug(source="create_html_template")
        manual_debug()
        return ""
