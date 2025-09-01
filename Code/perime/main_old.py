import os
os.system('cls' if os.name == 'nt' else 'clear')

import subprocess
import time
import gams.transfer as gt
from gams import GamsWorkspace
import gams
import sys
import numpy as np

GAMS_SYST_DIR = '/Library/Frameworks/GAMS.framework/Versions/49/Resources/'

# Chemins relatifs des fichiers .gdx
CODE_GAMS_DIR = "Modele_chronologique_simplifie.gms"
CODE_PY_DIR = "battery_optimizer.py"
DEMANDM_DIR = "Modele_chronologique/demandM.gdx"
BESSSOC_DIR = "bessSOC.gdx"

# Courriel pour faire fonctionner NEOS
NEOS_EMAIL = "vincent.boltz@eleves.enpc.fr"

MAX_ITERATIONS = 5
TOLERANCE = 1

def run_gams():
    ws = GamsWorkspace(system_directory=GAMS_SYST_DIR, working_directory='.')
    job = ws.add_job_from_file(CODE_GAMS_DIR)
    job.run()

def run_python():
    subprocess.run(["python3", CODE_PY_DIR], check=True)

def check_convergence(prev, current):
    return abs(prev - current) < TOLERANCE

def main():
    prev_cost = None
    for i in range(MAX_ITERATIONS):
        print(f"Iteration {i+1}")

        # Lancer les deux modèles
        run_gams()
        run_python()

        # Extraire le coût du modèle GAMS
        cost_gdx = gt.Container(DEMANDM_DIR, system_directory=GAMS_SYST_DIR)
        current_cost = np.round(cost_gdx.data['z'].records['level'].values, 2)

        print('prev_cost = ', prev_cost)
        print('current_cost = ', current_cost)

        # Vérifier la convergence
        if prev_cost is not None and check_convergence(prev_cost, current_cost):
            print("Convergence atteinte!")
            break
        prev_cost = current_cost
    else:
        print("Maximum d'itérations atteint.")



if __name__ == "__main__":
    main()
