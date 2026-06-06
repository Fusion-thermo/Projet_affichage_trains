"""
System Monitor — Raspberry Pi 3B+ compatible
Enregistre toutes les minutes dans un fichier CSV par jour.

Dépendances :
    pip install psutil

Sur Raspberry Pi OS, vcgencmd est disponible nativement.
"""

import psutil
import subprocess
import time
from datetime import datetime
from pathlib import Path

INTERVAL = 30        # secondes entre chaque mesure
OUTPUT_DIR = "."     # dossier de sortie des CSV


# ──────────────────────────────────────────────
# Colonnes du CSV
# ──────────────────────────────────────────────
HEADER = (
    "heure,"
    "CPU(%),"
    "CPU_freq(MHz),"
    "load_1min,"
    "RAM(%),"
    "RAM_utilisee(MB),"
    "swap(%),"
    "disque(%),"
    "disque_lu(MB/s),"
    "disque_ecrit(MB/s),"
    "temp_cpu(C),"
    "temp_gpu(C),"
    "net_envoye(KB/s),"
    "net_recu(KB/s)"
)


# ──────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────

def safe(fn, default=""):
    """Exécute fn(), retourne default si une exception est levée."""
    try:
        return fn()
    except Exception:
        return default


def vcgencmd_temp():
    """Lit la température GPU via vcgencmd (Raspberry Pi uniquement)."""
    result = subprocess.run(
        ["vcgencmd", "measure_temp"],
        capture_output=True, text=True, timeout=2
    )
    # Retourne quelque chose comme "temp=47.2'C"
    raw = result.stdout.strip()          # "temp=47.2'C"
    return float(raw.split("=")[1].replace("'C", ""))


def cpu_temp_sysfs():
    """Lit la température CPU via /sys (Linux générique)."""
    raw = Path("/sys/class/thermal/thermal_zone0/temp").read_text().strip()
    return round(int(raw) / 1000, 1)


def get_cpu_temp():
    """Température CPU : essaie psutil, puis sysfs."""
    temps = safe(lambda: psutil.sensors_temperatures(), {})
    # Raspberry Pi OS expose souvent 'cpu_thermal' ou 'cpu-thermal'
    for key in ("cpu_thermal", "cpu-thermal", "coretemp", "k10temp", "acpitz"):
        if key in temps and temps[key]:
            return round(temps[key][0].current, 1)
    # Fallback sysfs
    return safe(cpu_temp_sysfs, "")


def get_gpu_temp():
    """Température GPU via vcgencmd (RPi) — retourne '' sinon."""
    return safe(vcgencmd_temp, "")


# ──────────────────────────────────────────────
# Collecte des métriques
# ──────────────────────────────────────────────

# Snapshots précédents pour calculer les deltas
_prev_disk_io = None
_prev_net_io = None
_prev_time = None


def collect(elapsed):
    """Collecte toutes les métriques. elapsed = secondes depuis la dernière mesure."""
    global _prev_disk_io, _prev_net_io

    now = datetime.now()
    heure = now.strftime("%Hh%M")

    # CPU
    cpu_pct   = safe(lambda: psutil.cpu_percent(interval=1), "")
    cpu_freq  = safe(lambda: round(psutil.cpu_freq().current), "")
    load_1min = safe(lambda: round(psutil.getloadavg()[0], 2), "")

    # RAM
    vm        = psutil.virtual_memory()
    ram_pct   = vm.percent
    ram_mb    = round(vm.used / 1024**2)

    # Swap
    swap_pct  = safe(lambda: psutil.swap_memory().percent, "")

    # Disque (partition racine)
    disk_pct  = safe(lambda: psutil.disk_usage("/").percent, "")

    # Débit disque (MB/s depuis la dernière mesure)
    cur_disk = safe(psutil.disk_io_counters)
    if cur_disk and _prev_disk_io and elapsed > 0:
        disk_read  = round((cur_disk.read_bytes  - _prev_disk_io.read_bytes)  / elapsed / 1024**2, 2)
        disk_write = round((cur_disk.write_bytes - _prev_disk_io.write_bytes) / elapsed / 1024**2, 2)
    else:
        disk_read = disk_write = ""
    _prev_disk_io = cur_disk

    # Températures
    temp_cpu = get_cpu_temp()
    temp_gpu = get_gpu_temp()

    # Débit réseau (KB/s depuis la dernière mesure)
    cur_net = safe(psutil.net_io_counters)
    if cur_net and _prev_net_io and elapsed > 0:
        net_sent = round((cur_net.bytes_sent - _prev_net_io.bytes_sent) / elapsed / 1024, 1)
        net_recv = round((cur_net.bytes_recv - _prev_net_io.bytes_recv) / elapsed / 1024, 1)
    else:
        net_sent = net_recv = ""
    _prev_net_io = cur_net

    return (
        heure, cpu_pct, cpu_freq, load_1min,
        ram_pct, ram_mb, swap_pct,
        disk_pct, disk_read, disk_write,
        temp_cpu, temp_gpu,
        net_sent, net_recv
    )


# ──────────────────────────────────────────────
# Écriture CSV
# ──────────────────────────────────────────────

def get_filepath():
    date = datetime.now().strftime("%Y-%m-%d")
    return Path(OUTPUT_DIR) / f"system_monitor_{date}.csv"


def write_stats(elapsed):
    metrics = collect(elapsed)
    ligne   = ",".join(str(v) for v in metrics)

    filepath = get_filepath()
    new_file = not filepath.exists()

    with open(filepath, "a", encoding="utf-8") as f:
        if new_file:
            f.write(HEADER + "\n")
            print(f"\n  → Nouveau fichier : {filepath.resolve()}")
        f.write(ligne + "\n")

    print(f"  [{filepath.name}]  {ligne}")


# ──────────────────────────────────────────────
# Point d'entrée
# ──────────────────────────────────────────────

def main():
    print("System Monitor démarré")
    print(f"Intervalle : {INTERVAL}s  |  Dossier : {Path(OUTPUT_DIR).resolve()}")
    print("Ctrl+C pour arrêter.\n")

    # Initialiser les snapshots réseau/disque avant la première mesure
    global _prev_disk_io, _prev_net_io
    _prev_disk_io = safe(psutil.disk_io_counters)
    _prev_net_io  = safe(psutil.net_io_counters)

    last = time.monotonic()

    try:
        while True:
            # cpu_percent(interval=1) bloque 1s — on soustrait du sleep
            elapsed = time.monotonic() - last
            last    = time.monotonic()

            write_stats(elapsed if elapsed > 0 else INTERVAL)

            remaining = INTERVAL - (time.monotonic() - last)
            if remaining > 0:
                time.sleep(remaining)

    except KeyboardInterrupt:
        print("\nMonitoring arrêté.")


if __name__ == "__main__":
    main()
