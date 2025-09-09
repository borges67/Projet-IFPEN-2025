import os
os.system('cls' if os.name == 'nt' else 'clear')

import math
import random
import numpy as np
import matplotlib.pyplot as plt
import pandas as pd
import math
import random

from config import config as cf

# ----- Fonctions -----

def elec_price_old(t: int, regime_precedent, df_prodvalues)  :
    transition_matrix = cf.TRANSITION_MATRIX
    regime_1 = cf.REGIME_1
    regime_2 = cf.REGIME_2

    # Configuration des paramètres du modèle
    transition_matrix = {'p11_solar': 7.349472, 'p11_wind': 14.28572, 
                        'p21_solar': -13.9232, 'p21_wind': -17.944}

    regime_1 = {
        'c': -6.06971624956,
        'rload': 6.98511187179e-05,
        'share_solar': -1.57793342889,
        'share_wind': -1.06511552798
    }
    regime_2 = {
        'c': 2.63225434198,
        'rload': 3.2477216102e-05,
        'share_solar': -0.54220999006,
        'share_wind': -4.12400593849
    }

    moyenne_historique_prix = 32.2 # 2021


    # Récupérer les valeurs pour la période t (utilisation de .iloc[t] pour éviter l'erreur)
    share_solar_t = df_prodvalues['share solar'].iloc[t]
    share_wind_t = df_prodvalues['share wind'].iloc[t]
    rload_t = df_prodvalues['Rload'].iloc[t]

    p11 = 1 / (1 + np.exp(-transition_matrix['p11_solar'] * share_solar_t - 
                         transition_matrix['p11_wind'] * share_wind_t))
    p21 = 1 / (1 + np.exp(-transition_matrix['p21_solar'] * share_solar_t - 
                         transition_matrix['p21_wind'] * share_wind_t))
    p12 = 1 - p11
    p22 = 1 - p21

    # Règles de transition
    if regime_precedent == 'Régime 1':
        regime = random.choices(['Régime 1', 'Régime 2'], weights=[p11, p12])[0]
    elif regime_precedent == 'Régime 2':
        regime = random.choices(['Régime 1', 'Régime 2'], weights=[p21, p22])[0]
    else:
        # Initialisation
        # Probabilités stationnaires pour la période t
        pi_1 = p21 / (p12 + p21)  # Probabilité ergodique du régime 1
        pi_2 = 1 - pi_1
        regime = random.choices(['Régime 1', 'Régime 2'], weights=[pi_1, pi_2])[0]

        # Calcul du prix selon le régime
    if regime == 'Régime 1':
        price_log = (regime_1["c"] + 
                    regime_1["rload"] * rload_t +
                    regime_1["share_solar"] * share_solar_t +
                    regime_1["share_wind"] * share_wind_t)
    else :
        price_log = (regime_2["c"] +
                    regime_2["rload"] * rload_t +
                    regime_2["share_solar"] * share_solar_t +
                    regime_2["share_wind"] * share_wind_t)

    price = np.sinh(price_log) + moyenne_historique_prix

    return regime, price



# ------------------------------------------------------------------
# todo : à supprimer

# DATA_DIR = cf.PROJECT_ROOT / "data"
# OUTPUT_GAMS_DIR = DATA_DIR / "Modele_chronologique"
# PRODVALUES_PATH = OUTPUT_GAMS_DIR / "prodValues.csv"
#
# cf.TRANSITION_MATRIX = {'p11_solar' : 7.349472, 'p11_wind' : 14.28572, 'p21_solar' : -13.9232, 'p21_wind' : -17.944}
# cf.REGIME_1 = {'c' : -6.07, 'rload' : 6.99e-05, 'share_solar' : - 1.58, 'share_wind' : - 1.07}
# cf.REGIME_2 = {'c' : 2.63, 'rload' : 3.25e-05, 'share_solar' : - 0.54, 'share_wind' : - 4.12}
# df_prodvalues = pd.read_csv(PRODVALUES_PATH, sep=',') # Production nationale PV et éolienne
#
# #  Ajout de colonnes calculées
# df_prodvalues['Rload'] = df_prodvalues['prod totale'] - df_prodvalues['prod PV'] - df_prodvalues['prod eolien']
# df_prodvalues['share solar'] = df_prodvalues['prod PV']/df_prodvalues['prod totale']
# df_prodvalues['share wind'] = df_prodvalues['prod eolien']/df_prodvalues['prod totale']


def plot_elec_price(df_results):
    """
    Fonction pour tracer les résultats de la simulation des prix de l'électricité.
    Affiche les prix simulés, les parts de production solaire et éolienne, 
    la production totale et les régimes de prix.
    """

    # Création des graphiques
    fig, axes = plt.subplots(4, 1, figsize=(16, 15))

    # 1. Prix simulé vs prix réel (si disponible)
    if 'Prix_elec' in df_results.columns:
        axes[0].plot(df_results.index, df_results['Prix_simule'], color='blue', label='Prix simulé', linewidth=1)
        axes[0].plot(df_results.index, df_results['Prix_elec'], color='red', label='Prix réel', linewidth=1, alpha=0.7)
        axes[0].legend()
    else:
        axes[0].plot(df_results.index, df_results['Prix_simule'], color='blue', linewidth=1)
    axes[0].set_ylabel('Prix (€/MWh)')
    axes[0].set_title('Prix de l\'électricité: simulé vs réel')
    axes[0].grid(True, alpha=0.3)

    # 2. Production solaire et éolienne
    axes[1].plot(df_results.index, df_results['share solar'], color='orange', label='Part solaire', linewidth=1)
    axes[1].plot(df_results.index, df_results['share wind'], color='purple', label='Part éolienne', linewidth=1)
    axes[1].set_ylabel('Part de production')
    axes[1].set_title('Parts de production solaire et éolienne')
    axes[1].legend()
    axes[1].grid(True, alpha=0.3)

    # 3. Production totale et composantes
    axes[2].plot(df_results.index, df_results['prod totale'], color='black', label='Production totale', linewidth=1)
    axes[2].plot(df_results.index, df_results['Rload'], color='green', label='Production résiduelle', linewidth=1)
    axes[2].plot(df_results.index, df_results['prod PV'], color='orange', label='PV', linewidth=1, alpha=0.7)
    axes[2].plot(df_results.index, df_results['prod eolien'], color='purple', label='Éolien', linewidth=1, alpha=0.7)
    axes[2].set_ylabel('Production (MW)')
    axes[2].set_title('Production totale et par technologie')
    axes[2].legend()
    axes[2].grid(True, alpha=0.3)

    # 4. Régimes de prix
    axes[3].plot(df_results.index, df_results['Régime_num'], color='red', drawstyle='steps', linewidth=1)
    axes[3].set_yticks([1, 2])
    axes[3].set_yticklabels(['Régime 1', 'Régime 2'])
    axes[3].set_ylabel('Régime')
    axes[3].set_xlabel('Périodes')
    axes[3].set_title('Régimes de prix')
    axes[3].grid(True, alpha=0.3)

    plt.tight_layout()
    plt.show()

def plot_elec_price_regime(df_results):
    import matplotlib.pyplot as plt

    print("=" * 50)
    print("ANALYSE STATISTIQUE DU MODÈLE")
    print("=" * 50)

    # Statistiques descriptives par régime
    print("\n1. STATISTIQUES PAR RÉGIME:")
    print(df_results.groupby('Régime')['Prix_simule'].describe())

    # Pourcentage de temps dans chaque régime
    regime_counts = df_results['Régime'].value_counts()
    print(f"\n2. DISTRIBUTION DES RÉGIMES:")
    for regime, count in regime_counts.items():
        percentage = (count / len(df_results)) * 100
        print(f"  {regime}: {count} périodes ({percentage:.1f}%)")

    # Corrélations
    if 'Prix_elec' in df_results.columns:
        correlation = df_results['Prix_simule'].corr(df_results['Prix_elec'])
        print(f"\n3. CORRÉLATION avec prix réel: {correlation:.3f}")

    print(f"\n4. CORRÉLATIONS avec variables explicatives:")
    correlation_matrix = df_results[['Prix_simule', 'share solar', 'share wind', 'Rload']].corr()
    print(correlation_matrix)

    # Graphique avec légende catégorielle
    plt.figure(figsize=(12, 5))

    for regime, color in zip([1, 2], ['tab:blue', 'tab:orange']):
        subset = df_results[df_results['Régime_num'] == regime]
        plt.scatter(
            subset['share solar'] + subset['share wind'],
            subset['Prix_simule'],
            alpha=0.6,
            label=f"Régime {regime}",
            color=color
        )

    plt.xlabel('Part totale solaire + éolien')
    plt.ylabel('Prix simulé (€/MWh)')
    plt.title('Relation entre énergies renouvelables et prix simulé')
    plt.grid(True, alpha=0.3)
    plt.legend(title="Régime")
    plt.show()


# ------------------------------------------------------------------
# SIMULATION DES PRIX AVEC LES DONNÉES RÉELLES
# ------------------------------------------------------------------

# # Simulation des prix
# regimes = []
# prices = []
# current_regime = None  # Régime initial

# # Limiter le nombre de périodes si nécessaire pour le test
# n_periods = min(8736, len(df_prodvalues))  # Test sur les 1000 premières périodes ou moins

# for t in range(n_periods):
#     try:
#         current_regime, price = elec_price(t, current_regime, df_prodvalues)
#         regimes.append(current_regime)
#         prices.append(price)
#     except Exception as e:
#         print(f"Erreur à la période {t}: {e}")
#         break

# # Ajout des résultats au DataFrame
# df_results = df_prodvalues.iloc[:len(prices)].copy()
# df_results['Prix_simule'] = prices
# df_results['Régime'] = regimes
# df_results['Régime_num'] = [1 if r == 'Régime 1' else 2 for r in regimes]


# plot_elec_price(df_results)
#
# plot_elec_price_regime(df_results)
#
#
