from pathlib import Path


class Config : 
    """Classe de configuration partagée pour toutes les données"""

    def __init__(self):

        #  ----- Chemins -----
        self.CHEMIN_ABSOLU = r"/Users/vincentboltz/Documents/DOC_ENPC/Projet_IFPEN/Projet-IFPEN-2025"
        self.PROJECT_ROOT = Path(__file__).parent.parent 

        # Paramètres année
        self.PERIODS = None
        self.SEMAINES = None
        self.annee_conso_foyer = 2021

        # Caractéristiques modélisation
        self.STO = None
        self.PRECISION = None
        self.EPSILON = 1e-5
        self.MALUS_VENTE = 1 - self.EPSILON
        self.MALUS_ACHAT = 1 + self.EPSILON

        # Paramètres de la batterie
        self.PV_capa = None # Wc
        self.BESS_OPEX = None # €
        self.BESS_CAPEX = None # € - Prix des Beem battery (kWh:€)
        self.BESS_CAPA = None # kWh (PRECISION == 1) ou 10kWh (PRECISION == 10)
        self.BESS_PUISS = None # kW (PRECISION == 1) ou 10kW (PRECISION == 10)

        # Données de consommation
        self.PROFIL_CONSO = None

        # Données de prix et production
        self.ELECPRICE = []
        self.DEM = None
        self.PV = None
        self.PV_PROBS = None
        self.DF_PV = None
        self.DF_PRODVALUES = None

        # Calcul économique
        self.n = None # Durée de vie d'une batterie
        self.TA = None # Taux d'actualisation
        self.turpe = None # €/kWh
        self.taxes = None # % 

        # Calcul prix de l'électricité (chaine de Markov)
        self.TRANSITION_MATRIX = None
        self.REGIME_1 = None
        self.REGIME_2 = None

        # Pour export
        self.DF = None

        # Calcul prix
        self.ITERATIONS = None
        self.DURATION = 8736  # hours
        self.SHIFT = 0  # hours
        self.HISTORIC_ELECTRICITY_PRICE = 32.2  # €/MWh
        self.SEED = 42


# Instance globale unique
config = Config()
