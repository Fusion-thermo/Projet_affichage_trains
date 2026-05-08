import json
import types
import inspect
import os
from datetime import datetime
import traceback


def serialize_all(obj, _seen=None):
    # Protection contre les références circulaires
    if _seen is None:
        _seen = set()

    obj_id = id(obj)
    if obj_id in _seen:
        return "<référence circulaire>"
    
    # Types de base : on garde tel quel
    if isinstance(obj, (str, int, float, bool, type(None))):
        return obj
    
    # Marquer l'objet comme "en cours de traitement" avant de descendre
    _seen.add(obj_id)

    try:
        if isinstance(obj, dict):
            return {str(k): serialize_all(v, _seen) for k, v in obj.items()}

        if isinstance(obj, (list, tuple, set, frozenset)):
            return [serialize_all(v, _seen) for v in obj]

        if hasattr(obj, '__dict__'):
            return serialize_all(obj.__dict__, _seen)

        # Modules, classes, fonctions → texte
        return str(obj)

    except Exception:
        return f"<erreur sérialisation: {type(obj).__name__}>"

    finally:
        _seen.discard(obj_id)


def dump_debug(source="source inconnue"):
    folder = os.path.dirname(os.path.abspath(__file__))

    # Ne pas utiliser sys directement, ne fonctionne pas si l'erreur a lieu en dehors de ce script contrairement inspect.sys
    exc_type, exc_value, exc_traceback = inspect.sys.exc_info() 
    current_exception_str = "".join(traceback.format_exception(exc_type, exc_value, exc_traceback))

    ecriture=True
    try:
        files = [os.path.join(folder, f) for f in os.listdir(folder) if f.endswith('.json')]
        if len(files) >= 20:
            # return "dump_debug","Plus de 20 fichiers dans le dossier"
            ecriture=False
        total_size = sum(os.path.getsize(f) for f in files)
        if total_size > 100 * 1024 * 1024:
            # return "dump_debug","Plus de 100 mo dans le dossier"
            ecriture=False
        if files:#si le dernier log n'est pas déjà cette erreur
            latest_file = max(files, key=os.path.getmtime) 
            with open(latest_file, 'r', encoding='utf-8') as lf:
                last_data = json.load(lf)
                if last_data.get("exception_detail") == current_exception_str:
                    ecriture=False  
    except Exception as e:
        print(e)
        return "dump_debug",str(e)  # Si on ne peut même pas lister les fichiers, on abandonne proprement

    # Capture des variables de l'appelant
    try:
        caller_frame = inspect.currentframe().f_back
        caller_locals = caller_frame.f_locals
        variables = {}
        for name, val in caller_locals.items():
            if (not name.startswith('__') and
                not isinstance(val, types.ModuleType) and
                not callable(val)):
                variables[name] = serialize_all(val)
    except Exception:
        variables = {}

    if ecriture:
        dump = {
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M"),
            "exception_type": str(exc_type.__name__) if exc_type else "Unknown",
            "exception_message": str(exc_value),
            "exception_detail": current_exception_str,
            "variables": variables
        }

        # Écriture du JSON de debug
        try:
            filename = f"debug_{datetime.now().strftime('%Y%m%d_%H%M')}.json"
            full_path = os.path.join(folder, filename)
            with open(full_path, "w", encoding="utf-8") as f:
                json.dump(dump, f, indent=4, ensure_ascii=False)
        except Exception as e:
            print(f"Erreur lors de l'écriture du debug JSON : {e}")

    # Mise à jour de train_board.html
    try:
        # Construction du bloc d'erreur (on échappe les caractères HTML dangereux)
        import html as html_module
        exc_safe = html_module.escape(str({
            "exception_type": str(exc_type.__name__) if exc_type else "Unknown",
            "exception_message": str(exc_value),
            "exception_detail": current_exception_str
        }))
        # print(source,exc_safe)
        return source, exc_safe
    except Exception as e:
        print(f"Erreur lors de la mise à jour de train_board.html : {e}")
        return "dump_debug",str(e)


if __name__ == "__main__":
    class Train:
        def __init__(self, code, destination, arrivee, depart, stopped, retard, numero_train):
            self.code_mission = code
            self.destination = destination
            self.arrivee = arrivee
            self.depart = depart
            self.immobile = stopped
            self.retard = retard

            self.orientation=""
            self.couleur = ""

            self.extra = ""
            self.arrivee_initiale = ""
            self.nb_decalage = 0
            self.retard_prec = retard


    try:
        a=2
        b="test"
        l=[1,2,3,4]
        dico = {3:3,"rr":"wow"}
        trainc = Train("elba","rouen","arrive","depart",False,True,12)
        bf=(3,4,5)
        ds+=1
    except Exception:
        
        dump_debug()