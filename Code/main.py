import os
os.system('cls' if os.name == 'nt' else 'clear')

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

# Importation des autres script
from config import config as cf

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
#  Paramètres -----------------------------------------------------------------------------------------------------
# --------------------------------------------------------------------------------------------------------------

cf.PERIODS = 8760 # 
cf.annee_conso_foyer = 2021

cf.STO = True # Calcul stochastique ou pas (sur le solaire)
cf.PRECISION = 10 # Précision du calcul (1: unité, 10: dizième d'unité)

#  Caractéristiques batterie
cf.PV_capa = 2.800 # Wc
cf.BESS_OPEX = 0 # OPEX
cf.BESS_MAX_TEST = (0, 6, 10, 14) # Les différentes capacités maximales des batteries que l'on teste (cohérent avec BESS_CAPEX)
cf.BESS_CAPEX = {0:0, 6:5300, 10:6400, 14:7500} # € - Prix des Beem battery (kWh:€)
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

#  Paramètres du calcul du prix de l'électricité (chaine de Markov)
cf.TRANSITION_MATRIX = {'p11_solar' : 7.349472, 'p11_wind' : 14.28572, 'p21_solar' : -13.9232, 'p21_wind' : -17.944}
cf.REGIME_1 = {'c' : -6.07, 'rload' : 6.99e-05, 'share_solar' : - 1.58, 'share_wind' : - 1.07}
cf.REGIME_2 = {'c' : 2.63, 'rload' : 3.25e-05, 'share_solar' : - 0.54, 'share_wind' : - 4.12}

# ----- Paramètres calculés automatiquement (à ne pas modifier) -----
cf.max_vente = 10 # Nombre de test de vente maximal (pour limiter le nombre de calcul)
cf.bess_opex = 0 + cf.EPSILON # OPEX
cf.BESS_CAPA = cf.BESS_CAPA * cf.PRECISION # kWh ou 10 kWh (dépendemment de la précision)
cf.BESS_PUISS = cf.BESS_PUISS * cf.PRECISION # kW ou 10 kWh (dépendemment de la précision)


# --------------------------------------------------------------------------------------------------------------
#  Importation données -----------------------------------------------------------------------------------------------------
# --------------------------------------------------------------------------------------------------------------

df_elecprice = pd.read_csv(DEMANDM_PATH, sep=',') # Coût marginal
df_dem = pd.read_csv(DEMANDFOYER_PATH, sep=';') # Demande
cf.DF_PV = pd.read_csv(PRODPV_PATH, sep=',') # Producion PV
df_pv = cf.DF_PV
df_prodvalues = pd.read_csv(PRODVALUES_PATH, sep=',') # Production nationale PV et éolienne

#  Ajout de colonnes calculées
df_prodvalues['Rload'] = df_prodvalues['prod totale'] - df_prodvalues['prod PV'] - df_prodvalues['prod eolien']
df_prodvalues['share solar'] = df_prodvalues['prod PV']/df_prodvalues['prod totale']
df_prodvalues['share wind'] = df_prodvalues['prod eolien']/df_prodvalues['prod totale']
# df_prodvalues.loc[df_prodvalues['Rload'] < 50000, 'Prix elec'] = ( cf.regime_1["c"] + cf.regime_1["rload"]*(df_prodvalues['Rload']) 
# + cf.regime_1["share_solar"]*df_prodvalues['share solar'] + cf.regime_1["share_wind"]*df_prodvalues['share wind'] )
df_prodvalues.loc[df_prodvalues['Rload'] < 150000, 'Prix elec'] = ( cf.regime_2["c"] + cf.regime_2["rload"]*(df_prodvalues['Rload']) 
+ cf.regime_2["share_solar"]*df_prodvalues['share solar'] + cf.regime_2["share_wind"]*df_prodvalues['share wind'] )

# Listes et DataFrame finaux utilisés
cf.ELECPRICE = df_prodvalues['Prix elec'].round(3).tolist()
cf.DEM = df_dem[cf.PROFIL_CONSO].div(1000).round(2).tolist()
cf.PV = (df_pv['dispo PV'] * cf.PV_capa).round(2)
cf.PV_PROBS = [[(me, 0.16), (m, 0.68), (me_plus, 0.16)] for me, m, me_plus in 
            zip((df_pv['M-E'] * cf.PV_capa).round(2).tolist(), 
                (df_pv['M'] * cf.PV_capa).round(2).tolist(), 
                (df_pv['M+E'] * cf.PV_capa).round(2).tolist())]


# --------------------------------------------------------------------------------------------------------------
#  Modèle batterie -----------------------------------------------------------------------------------------------------
# --------------------------------------------------------------------------------------------------------------
import behavior_layer

cf.DF = behavior_layer.annual_behavior(cf.BESS_CAPA)
df = cf.DF
print(f"Taille finale : {len(df)} lignes")

def export_df_for_graph() :
    return df, cf.SEMAINES

# --------------------------------------------------------------------------------------------------------------
#  Exportation (pour GAMS) -----------------------------------------------------------------------------------------------------
# --------------------------------------------------------------------------------------------------------------

full_year_df = behavior_layer.full_year_df_creation(df)

# Exporter les valeurs d'injection provenant des BESS pour le modèle GAMS
full_year_df["SOC_injectee"] = (
    full_year_df.apply(
        lambda row: max(0, float(Decimal(str(row['Demande'])) + Decimal(str(row['Vente'])) - Decimal(str(row['Prod PV'])) - Decimal(str(row['Achat'])))),
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


