import os
import inspect
from datetime import datetime
import traceback
import sys

repertoire_script = os.path.dirname(os.path.abspath(__file__))
sys.path.append(repertoire_script)
OUTPUT_PATH = os.path.join(repertoire_script, "train_board.html")


def manual_debug():
    try:
        exc_type, exc_value, exc_traceback = inspect.sys.exc_info()
        current_exception_str = "".join(traceback.format_exception(exc_type, exc_value, exc_traceback))

        with open(OUTPUT_PATH, "r", encoding="utf-8") as f:
                texte = f.read()

        now_str = datetime.now().strftime("%H:%M")

        # Mise à jour de l'horloge — on vérifie que la balise est bien présente
        clock_tag = '<div class="clock">'
        debut = texte.find(clock_tag)
        if debut != -1:
            fin = texte.find('</div>', debut)
            if fin != -1:
                old_block = texte[debut:fin]
                texte = texte.replace(old_block, f'{clock_tag}{now_str}', 1)

        # Construction du bloc d'erreur (on échappe les caractères HTML dangereux)
        import html as html_module
        exc_safe = html_module.escape(str({
            "exception_type": str(exc_type.__name__) if exc_type else "Unknown",
            "exception_message": str(exc_value),
            "exception_detail": current_exception_str
        }))
        infos = f'<div class="panel-error">{exc_safe}</div>'

        # Insertion dans le panneau d'info
        info_tag = '<div class="info-panel">'
        if info_tag in texte:
            avant = texte.find(info_tag) + len(info_tag)
            texte = texte[:avant] + infos + texte[avant:]
        else:
            # Fallback : insertion avant la dernière </div>
            pos = texte.rfind('</div>')
            if pos != -1:
                texte = texte[:pos] + "\n        " + infos + "\n" + texte[pos:]

        if texte != "":
            # Écriture atomique via fichier temporaire
            tmp_path = OUTPUT_PATH + ".tmp"
            with open(tmp_path, "w", encoding="utf-8") as f:
                f.write(texte)
            os.replace(tmp_path, OUTPUT_PATH)  # Atomique sur la plupart des OS
    except Exception as e:
        print(e)