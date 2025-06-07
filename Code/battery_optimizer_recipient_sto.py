import os
os.system('cls' if os.name == 'nt' else 'clear')

from pathlib import Path

from functools import cache
from itertools import product

import numpy as np
import pandas as pd
import timeit
import sys

# Limite le nombre de decimales
from decimal import Decimal, getcontext
getcontext().prec = 5

# Evite les messages d'erreur de pandas
import warnings
warnings.simplefilter(action='ignore', category=FutureWarning) 

# Note le temps de calcul
start = timeit.default_timer()
sys.setrecursionlimit(1500)

# --------------------------------------------------------------------------------------------------------------
#  Données -----------------------------------------------------------------------------------------------------
# --------------------------------------------------------------------------------------------------------------

annee_conso_foyer = 2021

PROJECT_ROOT = Path(__file__).parent.parent 

DATA_DIR = PROJECT_ROOT / "data"
INPUT_PYTHON_DIR = DATA_DIR / "input_residential"
INPUT_GAMS_DIR = DATA_DIR / "input_national"
OUTPUT_GAMS_DIR = DATA_DIR / "Modele_chronologique"

DEMANDM_PATH = OUTPUT_GAMS_DIR / "demandM.csv"
DEMANDFOYER_PATH = INPUT_PYTHON_DIR / f"Demande Foyer-{annee_conso_foyer}.csv"
PRODPV_PATH = INPUT_PYTHON_DIR / "dispo_python.csv"
PRODVALUES_PATH = OUTPUT_GAMS_DIR / "prodValues.csv"

BESSSOC_PATH = INPUT_GAMS_DIR / "bessSOC.csv"
ACHAT_PATH = INPUT_GAMS_DIR / "achat.csv"

# Paramètres ---------------------------------------------------------------------------------------------------
BESS_MAX_TEST = (0, 6, 10, 14) # Les différentes capacités maximales des batteries que l'on teste (Il faut que ça soit cohérent avec le dictionnaire des CAPEX)
PERIODS = 8760 # 
EPSILON = 1e-5

malus_vente =  1 - EPSILON # Malus sur la vente par rapport à l'achat
malus_achat = 1 + EPSILON
max_vente = 10 # Test de vente maximal (pour limiter le nombre de calcul)
bess_opex = 0+EPSILON # OPEX
bess_capex = {0:0, 6:5300, 10:6400, 14:7500} # € - Prix des Beem battery (kWh:€)

PV_capa = 2.800 # Wc

turpe = 0.06 # €/kWh
taxes = 0.3 # % 

sto = True # Calcul stochastique ou pas (sur le solaire)
profil = 'RES11 (+ RES11WE)' # RES11 (+ RES11WE) | RES2 (+ RES5) | RES2WE | RES3 | RES4

# Calcul eco
n = 15 # Durée de vie d'une batterie
TA = 0.05 # Taux d'actualisation

# Capacité de la batterie à tester
BESS_CAPA = 60 # kWh ou 10 kWh (dépendemment de la précision)
BESS_PUISS = 30 # kW ou 10 kWh (dépendemment de la précision)
PRECISION = 10

# Données ----------------------------------------------------------------------------------------------------

df_elecprice = pd.read_csv(DEMANDM_PATH, delimiter=',') 
df_dem = pd.read_csv(DEMANDFOYER_PATH, delimiter=';') 
df_pv = pd.read_csv(PRODPV_PATH, delimiter=',')
df_prodvalues = pd.read_csv(PRODVALUES_PATH, delimiter=',')

df_prodvalues['Rload'] = df_prodvalues['prod totale'] - df_prodvalues['prod PV'] - df_prodvalues['prod eolien']
df_prodvalues['share solar'] = df_prodvalues['prod PV']/df_prodvalues['prod totale']
df_prodvalues['share wind'] = df_prodvalues['prod eolien']/df_prodvalues['prod totale']
# df_prodvalues.loc[df_prodvalues['Rload'] < 50000, 'Prix elec'] = -6.06971624956 + 6.98511187179e-05*(df_prodvalues['Rload']) - 1.57793342889*df_prodvalues['share solar'] - 1.06511552798*df_prodvalues['share wind']
df_prodvalues.loc[df_prodvalues['Rload'] < 150000, 'Prix elec'] = 2.63225434198 + 3.2477216102e-05*(df_prodvalues['Rload']) - 0.54220999006*df_prodvalues['share solar'] - 4.12400593849*df_prodvalues['share wind']
ELECPRICE = df_prodvalues['Prix elec'].round(3).tolist()
DEM = df_dem[profil].div(1000).round(2).tolist()
PV = (df_pv['dispo PV'] * PV_capa).round(2)
PV_probs = [[(me, 0.16), (m, 0.68), (me_plus, 0.16)] for me, m, me_plus in 
            zip((df_pv['M-E'] * PV_capa).round(2).tolist(), 
                (df_pv['M'] * PV_capa).round(2).tolist(), 
                (df_pv['M+E'] * PV_capa).round(2).tolist())]

SEMAINES = {
    "hiver" : [list(range(72, 241)), []], 
    # "printemps" : [list(range(2256, 2425)), []],
    # "ete" : [list(range(4440, 4609)), []],
    # "automne" : [list(range(6624, 6793)), []]
}

# --------------------------------------------------------------------------------------------------------------
#  Fonctions ---------------------------------------------------------------------------------------------------
# --------------------------------------------------------------------------------------------------------------

def price_elec(df) -> list : 
    return df

@cache
def dp_charge_vente_zero(t: int, end:int) -> list :
    if t > end:
        return (0, None)
    
    min_cost = float('inf')
    best_action = None

    expected_cost = 0

    for PV_val, prob in PV_probs[t] : 
        energie_dispo = PV_val
        demande = DEM[t]
        A = max(demande - energie_dispo, 0)

        scenario_cost = prob * A * ELECPRICE[t]
        future_cost, _ = dp_charge_vente_zero(t+1, end)
        expected_cost += scenario_cost + prob * future_cost
    
    if expected_cost < min_cost : 
        min_cost = expected_cost
        best_action = (0, 0)
    
    return (min_cost, best_action)

@cache
def dp_charge_vente_sto(t: int, end:int, soc: int, Bmax: int) -> list :
    if t > end:
        return (0, None)
    
    min_cost = float('inf')
    best_action = None

    # Bornes de X1 basées sur la puissance max
    min_X1 = int(max(0, soc*PRECISION - BESS_PUISS))
    max_X1 = int(min(Bmax, soc*PRECISION + BESS_PUISS))

    for X1_10 in range(min_X1, max_X1+1) : 
        for V_10 in range(BESS_PUISS + 1 - int(abs(X1_10/PRECISION - soc))) : 
            expected_cost = 0
            X1 = X1_10/PRECISION
            V = V_10/PRECISION
            for PV_val, prob in PV_probs[t] : 
                energie_dispo = PV_val + soc
                demande = DEM[t] + V + X1
                A = max(demande - energie_dispo, 0)

                new_soc = min(Bmax, X1)

                scenario_cost = prob * ((abs(X1-soc))*bess_opex + (A*malus_achat - V*malus_vente)*ELECPRICE[t])
                future_cost, _ = dp_charge_vente_sto(t+1, end, new_soc, Bmax)
                expected_cost += scenario_cost + prob * future_cost

            if expected_cost < min_cost : 
                min_cost = expected_cost
                best_action = (X1_10, V_10)
    
    return (min_cost, best_action)

@cache
def dp_charge_vente(t: int, end:int, soc: int, Bmax: int) -> list :
    if t > end:
        return (0, None)
    
    min_cost = float('inf')
    best_action = None

    # Bornes de X1 basées sur la puissance max
    min_X1 = int(max(0, soc*PRECISION - BESS_PUISS))
    max_X1 = int(min(Bmax, soc*PRECISION + BESS_PUISS))
    
    for X1_10 in range(min_X1, max_X1+1) : 
        for V_10 in range(BESS_PUISS + 1 - int(abs(X1_10/PRECISION - soc))) : 
        # for V in range(max_vente + 1 - int(max(0, X1_10/PRECISION - soc))) : 
            X1 = X1_10/PRECISION
            V = V_10/PRECISION
            energie_dispo = PV[t] + soc
            demande = DEM[t] + V + X1
            A = max(demande - energie_dispo, 0)
            well = max(0, PV[t] - demande + soc)

            new_soc = min(Bmax, X1)

            current_cost = ( (abs(X1-soc))*bess_opex + (A*malus_achat - V*malus_vente)*ELECPRICE[t] )
            future_cost, _ = dp_charge_vente(t+1, end, new_soc, Bmax) # Équation de Bellman
            total_cost = current_cost + future_cost

            if total_cost < min_cost:
                min_cost = total_cost
                best_action = (X1_10, V_10)

    return (min_cost, best_action)

def max_BESS_installed(BESS_MAX_TEST: int) :
    min_total = float('inf')
    best = None
    cost_zero = 0
    for Bmax in BESS_MAX_TEST :
        if Bmax == 0 : 
            cost_zero, _ = dp_charge_vente_zero(1, 0, Bmax)
        elif Bmax != 0 : 
            cost, _ = dp_charge_vente(1, 0, Bmax)
            couts_actualises = bess_capex[Bmax] - sum(list((cost_zero - cost)/(1 + TA)**i for i in range(n))) # Coût batterie - Gains grâce à la batterie 
            print(round(couts_actualises, 2))
            if couts_actualises < min_total :
                min_total = couts_actualises
                best = (cost, bess_capex[Bmax], couts_actualises, Bmax)
    return best

def weekly_behavior(Bmax: int) -> list : 
    for semaine in SEMAINES :
        if sto : 
            cost, best_action = dp_charge_vente_sto(SEMAINES[semaine][0][0], SEMAINES[semaine][0][-1], 0, Bmax)
        else :
            cost, best_action = dp_charge_vente(SEMAINES[semaine][0][0], SEMAINES[semaine][0][-1], 0, Bmax)
        print(semaine)
        # SEMAINES[semaine][1] = best_action
    # cost_zero, _ = dp_charge_vente(1, 0, BESS_CAPA)
    # cost, _ = dp_charge_vente(1, 0, BESS_CAPA)
    # couts_actualises = bess_capex[BESS_CAPA] - sum(list((cost_zero - cost)/(1 + TA)**i for i in range(n))) # Coût batterie - Gains grâce à la batterie 
    return None

def annual_behavior(Bmax: int) :
    df_base = pd.DataFrame(columns=['Saison', 'Date', 'Heure', 'Demande', 'Prod PV', 'SOC_t', 'Vente', 'Achat', 'Well', 'Prix elec'])

    for semaine in SEMAINES :
        df_sem = pd.DataFrame(columns=['Saison', 'Date', 'Heure', 'Demande', 'Prod PV', 'SOC_t', 'Vente', 'Achat', 'Well', 'Prix elec'])
        print(semaine)
        start = SEMAINES[semaine][0][0]
        end = SEMAINES[semaine][0][-1]

        #Execution de la fonction d'optimisation
        if sto : 
            if Bmax == 0 :
                dp_charge_vente_zero(start, end)
            else :
                dp_charge_vente_sto(start, end, 0, Bmax)
        else :
            dp_charge_vente(start, end, 0, Bmax)

        # Simulation pour récupérer l'historique
        current_soc = 0
        history_soc = []
        history_vente = []
        history_achat = []
        history_well = []

        for t in range(start, end):
            history_soc.append(current_soc)
            if sto : 
                    if Bmax == 0 :
                        _, best_action = dp_charge_vente_zero(t, end)
                    else :
                        _, best_action = dp_charge_vente_sto(t, end, current_soc, Bmax)
            else :
                _, best_action = dp_charge_vente(t, end, current_soc, Bmax)
            # _, best_action = dp_charge_vente(t, end, current_soc, Bmax)
            if best_action is None:
                break
            X1_10, V_10 = best_action
            # Calcul de l'achat
            X1 = X1_10/PRECISION
            V = V_10/PRECISION
            energie_dispo = PV[t] + current_soc
            demande = DEM[t] + V + X1
            A = max(demande - energie_dispo, 0)
            well = max(0, PV[t] - demande + current_soc)
            history_vente.append(V)
            history_achat.append(A)
            history_well.append(well)
            new_soc = min(Bmax, X1)
            current_soc = new_soc

        df_sem = pd.DataFrame({
            'Saison': [semaine] * (end - start),  # Liste de taille (end-start) remplie avec 'semaine'
            'Date': df_pv['Date'][start:end],
            'Heure': df_pv['Heure Journée'][start:end],
            'Demande': DEM[start:end],
            'Prod PV': PV[start:end],
            'SOC_t': history_soc,
            'Vente': history_vente,
            'Achat': history_achat,
            'Well': history_well,
            'Prix elec': ELECPRICE[start:end]
        })

        df_base = pd.concat([df_base, df_sem]).round(3)

    return df_base

# --------------------------------------------------------------------------------------------------------------
#  Appel & affichage -------------------------------------------------------------------------------------------
# --------------------------------------------------------------------------------------------------------------

# min_cost, min_capex, min_total_cost, best_Bmax = max_BESS_installed(BESS_MAX_TEST)
# weekly_behavior(BESS_CAPA)

# cost, best_action = dp_charge_vente(50, 218, 0, BESS_CAPA)

df = annual_behavior(BESS_CAPA)

# display(df.iloc[158:200])
print(f"Taille finale : {len(df)} lignes")
    
# # --------------------------------------------------------------------------------------------------------------
# #  Export ------------------------------------------------------------------------------------------------------
# # --------------------------------------------------------------------------------------------------------------

# Fonction pour exporter dans d'autres codes (graphiques.ipynb par exemple)
def export_df_for_graph() :
    return df, SEMAINES

def full_year_df_creation(df) :
    segments = []

    saisons_config = [
        ('hiver', 12),
        ('printemps', 8),
        ('ete', 4),
        ('automne', 8),
        ('hiver', 4),
    ]

    for saison, repetitions in saisons_config:
        semaine_type = df[df['Saison'] == saison]
        
        segment = pd.concat([semaine_type] * repetitions, ignore_index=True)
        segments.append(segment)

    full_year_df = pd.concat(segments, ignore_index=True)
    journee_hiver = df[df['Saison'] == 'hiver'].head(24)
    full_year_df = pd.concat([full_year_df, journee_hiver], ignore_index=True)

    full_year_df.index += 1
    return full_year_df

full_year_df = full_year_df_creation(df)

# Exporter les valeurs d'injection provenant des BESS pour le modèle GAMS
full_year_df["SOC_injectee"] = (
    full_year_df.apply(
        lambda row: max(0, float(Decimal(str(row['Demande'])) + Decimal(str(row['Vente'])) - Decimal(str(row['Prod PV'])) - Decimal(str(row['Achat'])))),
        axis=1
    )
    .round(2))
df_subset = full_year_df[["SOC_injectee"]].copy()
df_subset.to_csv(BESSSOC_PATH, index=True, header=False)

# Exporter les valeurs d'achat d'électricité pour les BESS pour le modèle GAMS
full_year_df['Achat batterie'] = (full_year_df['Achat'] + full_year_df['Prod PV'] - full_year_df['Demande']).clip(lower=0)
df_subset = full_year_df[["Achat batterie"]].copy().round(3)
df_subset.to_csv(ACHAT_PATH, index=True, header=False)

# --------------------------------------------------------------------------------------------------------------
# Affichage du temps d'exécution
# os.system( "say bip" )
stop = timeit.default_timer()
print(f'\nTime: {round(stop - start, 2)}', )