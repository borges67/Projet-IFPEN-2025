from __future__ import annotations

import os
os.system('cls' if os.name == 'nt' else 'clear')

import pandas as pd
import timeit
import sys
import numpy as np
import random
import multiprocessing as mp
from tqdm import tqdm
from typing import TypeVar
from enum import Enum
import matplotlib.pyplot as plt

# Limite le nombre de decimales
from decimal import Decimal, getcontext
getcontext().prec = 5

# Evite les messages d'erreur de pandas
import warnings
warnings.simplefilter(action='ignore', category=FutureWarning) 

# Note le temps de calcul
start = timeit.default_timer()
sys.setrecursionlimit(1500)

# Importation des autres script
from config import config as cf
import elec_price_layer

# --------------------------------------------------------------------------------------------------------------
#  Chemins -----------------------------------------------------------------------------------------------------
# --------------------------------------------------------------------------------------------------------------

DATA_DIR = cf.PROJECT_ROOT / "data"
INPUT_PYTHON_DIR = DATA_DIR / "input_residential"
INPUT_GAMS_DIR = DATA_DIR / "input_national"
OUTPUT_GAMS_DIR = DATA_DIR / "Modele_chronologique"

DEMANDM_PATH = OUTPUT_GAMS_DIR / "demandM.csv"
DEMANDFOYER_PATH = INPUT_PYTHON_DIR / f"Demande Foyer-{cf.annee_conso_foyer}.csv"
PRODPV_PATH = INPUT_PYTHON_DIR / "dispo_python.csv"
PRODVALUES_PATH = OUTPUT_GAMS_DIR / "prodValues.csv"

BESSSOC_PATH = INPUT_GAMS_DIR / "bessSOC.csv"
ACHAT_PATH = INPUT_GAMS_DIR / "achat.csv"


# --------------------------------------------------------------------------------------------------------------
#  Paramètres --------------------------------------------------------------------------------------------------
# --------------------------------------------------------------------------------------------------------------

cf.PERIODS = 8736 # 
cf.annee_conso_foyer = 2021

cf.STO = True # Calcul stochastique ou pas (sur le solaire)
cf.PRECISION = 10 # Précision du calcul (1: unité, 10: dizième d'unité)

#  Caractéristiques batterie
cf.PV_capa = 2.800 # Wc
cf.BESS_OPEX = 0 # OPEX
cf.BESS_MAX_TEST = (0, 6, 10, 14) # (0, 6, 10, 14)  Les différentes capacités maximales des batteries que l'on teste (cohérent avec BESS_CAPEX)
cf.BESS_CAPEX = {0:0, 6:5300, 10:6400, 14:7500} # {0:0, 6:5300, 10:6400, 14:7500} € - Prix des Beem battery (kWh:€)
cf.BESS_CAPA = 6 # kWh ou 10 kWh (dépendemment de la précision)
cf.BESS_PUISS = 3 # kW ou 10 kWh (dépendemment de la précision)

# Données de consommation
cf.PROFIL_CONSO = 'RES11 (+ RES11WE)' # RES11 (+ RES11WE) | RES2 (+ RES5) | RES2WE | RES3 | RES4

# Calcul économique
cf.n = 15 # Durée de vie d'une batterie
cf.TA = 0.05 # Taux d'actualisation
cf.turpe = 0.06 # €/kWh
cf.taxes = 0.3 # % 

#  Définition des semaines-types par saison
cf.SEMAINES = {
    "hiver" : [list(range(72, 241)), []], 
    "printemps" : [list(range(2256, 2425)), []],
    "ete" : [list(range(4440, 4609)), []],
    "automne" : [list(range(6624, 6793)), []]
    }

cf.TRANSITION_MATRIX = {'p11_solar': 7.349472, 'p11_wind': 14.28572,
                     'p21_solar': -13.9232, 'p21_wind': -17.944}
cf.REGIME_1  = {'c': -6.06971624956,
                'rload': 6.98511187179e-05,
                'share_solar': -1.57793342889,
                'share_wind': -1.06511552798 }
cf.REGIME_2 = {'c': 2.63225434198,
               'rload': 3.2477216102e-05,
               'share_solar': -0.54220999006,
               'share_wind': -4.12400593849 }

# ----- Paramètres calculés automatiquement (à ne pas modifier) -----
cf.bess_opex = 0 + cf.EPSILON # OPEX
cf.BESS_CAPA = cf.BESS_CAPA * cf.PRECISION # kWh ou 10 kWh (dépendemment de la précision)
cf.BESS_PUISS = cf.BESS_PUISS * cf.PRECISION # kW ou 10 kWh (dépendemment de la précision)


# --------------------------------------------------------------------------------------------------------------
#  Importation données -----------------------------------------------------------------------------------------
# --------------------------------------------------------------------------------------------------------------

df_dem = pd.read_csv(DEMANDFOYER_PATH, sep=';') # Demande
cf.DEM = df_dem[cf.PROFIL_CONSO].div(1000).round(2).tolist()
cf.DF_PV = pd.read_csv(PRODPV_PATH, sep=',') # Producion PV
cf.PV = (cf.DF_PV['dispo PV'] * cf.PV_capa).round(2) # Production PV = disponibilité nationale * Puissance PV résidentiel
cf.DF_PRODVALUES = pd.read_csv(PRODVALUES_PATH, sep=",", decimal =".").replace('"', '') # Production nationale PV et éolienne


# --------------------------------------------------------------------------------------------------------------
#  Calcul prix électricité  ------------------------------------------------------------------------------------
# --------------------------------------------------------------------------------------------------------------

import electricity_price

cf.HISTORIC_ELECTRICITY_PRICE = 32.2  # €/MWh

cf.ITERATIONS = 1
cf.DURATION = cf.PERIODS  # hours
cf.SHIFT = 0  # hours
cf.SEED = 42

# if __name__ == "__main__":
#     electricity_price.set_seed(cf.SEED)
#
#     df = pd.read_csv(PRODVALUES_PATH)
#     df["Rload"] = df["prod totale"] - df["prod PV"] - df["prod eolien"]
#     df["share solar"] = df["prod PV"] / df["prod totale"]
#     df["share wind"] = df["prod eolien"] / df["prod totale"]
#
#     rload = df["Rload"].iloc[cf.SHIFT : cf.SHIFT + cf.DURATION].to_numpy()
#     share_solar = df["share solar"].iloc[cf.SHIFT : cf.SHIFT + cf.DURATION].to_numpy()
#     share_wind = df["share wind"].iloc[cf.SHIFT : cf.SHIFT + cf.DURATION].to_numpy()
#
#     with mp.Pool(mp.cpu_count()) as pool:
#         results = list(
#             tqdm(
#                 pool.starmap(
#                     electricity_price.run_iteration,
#                     [(rload, share_solar, share_wind) for _ in range(cf.ITERATIONS)],
#                 ),
#                 total=cf.ITERATIONS,
#             )
#         )
#
#     rows = [row for sublist in results for row in sublist]
#     elecprice_df = (
#         pd.DataFrame(rows)
#         .groupby(["timestep"])
#         .agg(
#             {
#                 "timestep": "first",
#                 "regime": "mean",
#                 "price": "mean",
#             }
#         )
#         .reset_index(drop=True)
#         # .to_csv("results.csv", index=False)
#     )
#
#     cf.ELECPRICE = elecprice_df["price"].to_list()
#     print("Prix de l'électricité calculés : longueur = ", len(cf.ELECPRICE))


    # plot_range = range(4440,4609)
    # plt.figure(figsize=(30, 8))
    # plt.plot(cf.ELECPRICE[4440:4609], 'b-', linewidth=2, label='Prix moyen')
    # plt.xlabel('Périodes')
    # plt.ylabel('Prix (€/MWh)')
    # plt.title('Évolution du prix de l\'électricité\n(Moyenne sur {} tirages Markov)'.format(cf.ITERATIONS))
    # plt.grid(True, alpha=0.3)
    # plt.ylim(bottom = 0)
    # plt.legend()
    # plt.show()


cf.ELECPRICE = [random.randint(300, 600)/10 for t in range(cf.PERIODS)]
# --------------------------------------------------------------------------------------------------------------
#  Modèle batterie ---------------------------------------------------------------------------------------------
# --------------------------------------------------------------------------------------------------------------
import behavior_layer

cf.DF = behavior_layer.weeks_behavior(cf.BESS_CAPA)
# cf.DF = behavior_layer.annual_behavior(cf.BESS_CAPA)
df = cf.DF
print(f"Taille finale : {len(df)} lignes")

def export_df_for_graph() :
    return df, cf.SEMAINES


# --------------------------------------------------------------------------------------------------------------
#  Exportation (pour GAMS) -------------------------------------------------------------------------------------
# --------------------------------------------------------------------------------------------------------------

# full_year_df = behavior_layer.full_year_df_creation(df)
full_year_df = df

# Exporter les valeurs d'injection provenant des BESS pour le modèle GAMS
full_year_df["SOC_injectee"] = (
    full_year_df.apply( lambda row:
        max(0, float(Decimal(str(row['Demande'])) + Decimal(str(row['Vente'])) - Decimal(str(row['Prod PV'])) - Decimal(str(row['Achat'])))),
        axis=1).round(2)) # opérations pour forcer l'arrondi
df_subset = full_year_df[["SOC_injectee"]].copy()
df_subset.to_csv(BESSSOC_PATH, index=True, header=False)

# Exporter les valeurs d'achat d'électricité pour les BESS pour le modèle GAMS
full_year_df['Achat batterie'] = (full_year_df['Achat'] + full_year_df['Prod PV'] - full_year_df['Demande']).clip(lower=0)
df_subset = full_year_df[["Achat batterie"]].copy().round(3)
df_subset.to_csv(ACHAT_PATH, index=True, header=False)

# Affichage du temps d'exécution
# os.system( "say bip" ) # Fait un petit bruit à la fin
stop = timeit.default_timer()
print(f'\nTime: {round(stop - start, 2)}', )


