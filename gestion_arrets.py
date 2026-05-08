"""
RER C — Graphe des arrêts avec codes officiels.

Le graphe est construit directement depuis rer_c_branches.json.
Chaque entrée du JSON est un tronçon ou une branche ; les arrêts partagés
entre plusieurs branches ne forment qu'un seul nœud (fusion automatique
par nom).

API publique :
    shortest_path(code_a, code_b)        → liste de noms d'arrêts
    is_between(code_a, code_mid, code_b) → bool
    list_stops()                         → liste triée (code, nom)
"""

import json
from collections import deque
from pathlib import Path
import os
import sys

repertoire_script = os.path.dirname(os.path.abspath(__file__))
sys.path.append(repertoire_script)
from gestion_erreurs import dump_debug
from update_display_code import update_display

# ---------------------------------------------------------------------------
# Chargement + construction du graphe
# ---------------------------------------------------------------------------

_JSON_PATH = Path(__file__).parent / "rer_c_branches.json"


def _build(path: Path = _JSON_PATH):
    with open(path, encoding="utf-8") as f:
        data = json.load(f)

    graph: dict[str, list[str]] = {}
    code_to_name: dict[int, str] = {}
    name_to_code: dict[str, int] = {}

    def add_edge(a: str, b: str):
        graph.setdefault(a, [])
        graph.setdefault(b, [])
        if b not in graph[a]:
            graph[a].append(b)
        if a not in graph[b]:
            graph[b].append(a)

    for _branch, stops in data.items():
        for s in stops:
            name, code = s["list_name"], s["code_zone_arret"]
            if name not in name_to_code:
                name_to_code[name] = code
            if code not in code_to_name:
                code_to_name[code] = name

        for i in range(len(stops) - 1):
            add_edge(stops[i]["list_name"], stops[i + 1]["list_name"])

    return graph, code_to_name, name_to_code


GRAPH, CODE_TO_NAME, NAME_TO_CODE = _build()


# ---------------------------------------------------------------------------
# Résolution code → nom
# ---------------------------------------------------------------------------

def _resolve(code_or_name: int | str) -> str:
    """Accepte un code entier ou directement un nom d'arrêt."""
    if isinstance(code_or_name, int):
        if code_or_name not in CODE_TO_NAME:
            raise ValueError(f"Code inconnu : {code_or_name}")
        return CODE_TO_NAME[code_or_name]
    if code_or_name not in GRAPH:
        raise ValueError(f"Arrêt inconnu : '{code_or_name}'")
    return code_or_name


# ---------------------------------------------------------------------------
# BFS — chemin le plus court (nombre de stations)
# ---------------------------------------------------------------------------

def _bfs(start: str, end: str) -> list[str] | None:
    if start == end:
        return [start]
    visited: dict[str, str | None] = {start: None}
    queue = deque([start])
    while queue:
        cur = queue.popleft()
        if cur == end:
            path, node = [], end
            while node is not None:
                path.append(node)
                node = visited[node]
            return list(reversed(path))
        for nb in GRAPH[cur]:
            if nb not in visited:
                visited[nb] = cur
                queue.append(nb)
    return None


# ---------------------------------------------------------------------------
# API publique
# ---------------------------------------------------------------------------

def shortest_path(stop_a: int | str, stop_b: int | str) -> list[str] | None:
    """
    Retourne la liste des noms d'arrêts du chemin le plus court
    entre stop_a et stop_b (codes entiers ou noms de chaîne).
    Retourne None si aucun chemin n'existe.
    """
    return _bfs(_resolve(stop_a), _resolve(stop_b))


def is_between(stop_a: int | str, stop_mid: int | str, stop_b: int | str) -> bool:
    """
    Retourne True si stop_mid se trouve sur le chemin le plus court
    entre stop_a et stop_b.
    Accepte des codes entiers ou des noms d'arrêts.
    """
    try:
        path = shortest_path(stop_a, stop_b)
        return path is not None and _resolve(stop_mid) in path
    except:
        source, detail_erreur = dump_debug()
        if source !="create_html_template":
            update_display(erreur=detail_erreur)
        return False

def list_stops() -> list[tuple[int, str]]:
    """Retourne tous les arrêts sous forme (code, nom), triés par nom."""
    return sorted(
        [(NAME_TO_CODE[name], name) for name in GRAPH],
        key=lambda x: x[1],
    )


# ---------------------------------------------------------------------------
# Démonstration
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    print("=" * 68)
    print("  RER C — Graphe officiel")
    print("=" * 68)
    print(f"\n  Arrêts : {len(GRAPH)}   |   Codes : {len(CODE_TO_NAME)}\n")

# # --- Exemple de chemin (par codes) ---
    # a, b = 63812, 59531   # SQY → Saint-Martin d'Étampes
    # path = shortest_path(a, b)
    # print(f"Chemin le plus court ({len(path)-1} étapes) :")
    # print(f"  {CODE_TO_NAME[a]} → {CODE_TO_NAME[b]}")
    # for i, stop in enumerate(path):
    #     prefix = "  " if i == 0 else "→ "
    #     print(f"     {prefix}{stop} [{NAME_TO_CODE[stop]}]")
    # print()

    # --- Tests is_between ---
    tests = [
        # (A,       milieu,   B,        attendu, explication)
        (63812, 71274, 59531, True,
         "SQY → [Invalides] → St-Martin : passe par le tronc parisien"),
        (63812, 60247, 59531, True,
         "SQY → [Brétigny] → St-Martin : nœud de bifurcation sud"),
        (63812, 60247, 59843, True,
         "SQY → [Brétigny] → Dourdan la Forêt : bifurcation Dourdan"),
        (60247, 60115, 59843, True,
         "Brétigny → [La Norville] → Dourdan : sur la branche Dourdan"),
        (60247, 60987, 59843, False,
         "Brétigny → [Savigny-sur-Orge] → Dourdan : hors branche Dourdan"),
        (66816, 71274, 63244, True,
         "Pontoise → [Invalides] → Massy-Palaiseau : passe bien par Paris"),
        (66816, 478505, 63244, False,
         "Pontoise → [Juvisy] → Massy-Palaiseau : Juvisy est hors chemin Orly"),
        (69852, 69662, 63244, True,
         "Choisy → [Les Saules] → Massy : sur la branche Orly"),
        (73721, 63886, 63923, True,
         "Versailles Château RG → [Porchefontaine] → Viroflay : tronçon dédié"),
    ]

    print("Tests « est-il entre ? »")
    print("-" * 68)
    all_ok = True
    for ca, cm, cb, expected, expl in tests:
        result = is_between(ca, cm, cb)
        ok = result == expected
        all_ok = all_ok and ok
        status = "✅" if ok else "❌ ERREUR"
        print(f"  {status}  '{CODE_TO_NAME[cm]}'")
        print(f"       entre '{CODE_TO_NAME[ca]}'")
        print(f"       et    '{CODE_TO_NAME[cb]}' → {result}")
        print(f"       ({expl})")
        print()

    print("Bilan :", "tous les tests passent ✅" if all_ok else "⚠️  certains tests échouent")
    print()

    # # --- Liste complète ---
    # print("Tous les arrêts :")
    # for code, name in list_stops():
    #     print(f"  {code:>8}  {name}")

# print(CODE_TO_NAME)
    print(is_between(59531, 60785, 71135))  
