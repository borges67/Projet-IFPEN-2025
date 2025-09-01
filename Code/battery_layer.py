import os
os.system('cls' if os.name == 'nt' else 'clear')


from functools import cache
from config import config as cf

# ----- Données -----
bess_opex = cf.BESS_OPEX
malus_achat = cf.MALUS_ACHAT
malus_vente = cf.MALUS_VENTE

DEM = cf.DEM
ELECPRICE = cf.ELECPRICE
PV_probs = cf.PV_PROBS
PV = cf.PV
BESS_PUISS = cf.BESS_PUISS
PRECISION = cf.PRECISION


# ----- Fonctions -----

@cache
def dp_charge_vente_zero(t: int, end:int) -> list :
    """
    Simule le comportement d'un système Maison-PV seul qui peut vendre et acheter de l'électricité,
    mais qui ne peut pas la stocker.
    L'optimisation est stochastique et prend en compte les incertitudes sur la production PV. 

    Utile pour comparer le coût du système avec et sans batterie.
    - PV_probs : liste qui contient trois valeurs de production PV associée à des probabilité 
    à chaque pas de temps
    - DEM = demande à chaque pas de temps
    - ELECPRICE = prix de l'électricité à chaque pas de temps
    """

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
    """
    Simule le comportement d'un système Maison-PV-batterie qui peut vendre, acheter et stocker 
    de l'électricité.
    L'optimisation est stochastique et prend en compte les incertitudes sur la production PV. 
    
    Entrée : 
    - PV_probs : liste qui contient trois valeurs de production PV associée à des probabilité 
    à chaque pas de temps
    - BESS_PUISS : Puissance de la batterie. Détermine le max à charger/décharger par pas de temps
    - PRECISION : facteur de division (exemple : BESS_PUISS = 60, PRECISION = 10 : vrai puissance = 6 kWh)
    - DEM = demande à chaque pas de temps
    - ELECPRICE = prix de l'électricité à chaque pas de temps
    """

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
    """
    Simule le comportement d'un système Maison-PV-batterie qui peut vendre, acheter et stocker 
    de l'électricité.
    
    Entrée : 
    - PV : production PV à chaque pas de temps
    - BESS_PUISS : Puissance de la batterie. Détermine le max à charger/décharger par pas de temps
    - PRECISION : facteur de division (exemple : BESS_PUISS = 60, PRECISION = 10 : vrai puissance = 6 kWh)
    - DEM = demande à chaque pas de temps
    - ELECPRICE = prix de l'électricité à chaque pas de temps
    """


    if t > end:
        return (0, None)
    
    min_cost = float('inf')
    best_action = None

    # Bornes de X1 basées sur la puissance max
    min_X = int(max(0, soc*PRECISION - BESS_PUISS))
    max_X = int(min(Bmax, soc*PRECISION + BESS_PUISS))
    
    for X_10 in range(min_X, max_X+1) : 
        for V_10 in range(BESS_PUISS + 1 - int(abs(X_10/PRECISION - soc))) : 
        # for V in range(max_vente + 1 - int(max(0, X_10/PRECISION - soc))) : 
            X = X_10/PRECISION
            V = V_10/PRECISION

            energie_dispo = PV[t] + soc
            demande = DEM[t] + V + X
            A = max(demande - energie_dispo, 0)
            well = max(0, PV[t] - demande + soc)

            new_soc = min(Bmax, X)

            current_cost = ( (abs(X-soc))*bess_opex + (A*malus_achat - V*malus_vente)*ELECPRICE[t] )
            future_cost, _ = dp_charge_vente(t+1, end, new_soc, Bmax) # Équation de Bellman
            total_cost = current_cost + future_cost

            if total_cost < min_cost:
                min_cost = total_cost
                best_action = (X_10, V_10)

    return (min_cost, best_action)
