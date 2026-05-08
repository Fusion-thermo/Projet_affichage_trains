import os
import sys
repertoire_script = os.path.dirname(os.path.abspath(__file__))
sys.path.append(repertoire_script)
from construction_html import create_html_template
from last_try import manual_debug

OUTPUT_PATH = os.path.join(repertoire_script, "train_board.html")


def update_display(nord=[], sud=[], erreur="", disruptions = [], non_desservi = [], nuit=False):
    try:
        html = create_html_template(nord, sud, erreur, disruptions, non_desservi, nuit)
        if html:
            with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
                f.write(html)
    
    except Exception:
        manual_debug()
        
    