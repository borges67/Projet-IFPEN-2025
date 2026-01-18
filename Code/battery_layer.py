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
    Simule le comportement d'un système Maison-PV seul qui ne peut qu'acheter de l'électricité 
    sur le réseau pour répondre à sa demande lorsque le PV ne suffit plus. Pas de possibilité
    de stocker dans des batteries.

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

# @cache
# def dp_charge_vente_old(t: int, end:int, soc: int, Bmax: int) :
#     """
#     Simule le comportement d'un système Maison-PV-batterie qui peut vendre, acheter et stocker 
#     de l'électricité.
    
#     Entrée : 
#     - PV : production PV à chaque pas de temps
#     - BESS_PUISS : Puissance de la batterie. Détermine le max à charger/décharger par pas de temps
#     - PRECISION : facteur de division (exemple : BESS_PUISS = 60, PRECISION = 10 : vrai puissance = 6 kWh)
#     - DEM = demande à chaque pas de temps
#     - ELECPRICE = prix de l'électricité à chaque pas de temps
#     """
#     if t > end:
#         return (0, None)
    
#     # if t % 24 == 0 :
#     #     soc = 0
    
#     min_cost = float('inf')
#     best_action = None

#     surplus_pv = max(0, PV[t] - DEM[t]) * PRECISION

#     # Bornes de X basées sur la puissance max
#     min_X = int(max(0, soc*PRECISION - BESS_PUISS))
#     max_X = int(min(Bmax, soc*PRECISION + BESS_PUISS, surplus_pv))
#     # print("\nBmax = ", Bmax)
#     # print("soc*PRECISION + BESS_PUISS = ", soc*PRECISION + BESS_PUISS) 
#     # print("surplus PV = ", surplus_pv)

#     for X_10 in range(min_X, max_X+1) : 
#         X = X_10/PRECISION

#         charge_batterie = max(0, X - soc)  # Énergie utilisée pour charger
#         surplus_pv = max(0, PV[t] - DEM[t] - charge_batterie)

#         max_V_surplus = int(surplus_pv * PRECISION)
#         # max_V_charge = BESS_PUISS - int(abs(X_10 - soc*PRECISION))
#         # max_range_V = min(max_V_surplus, max_V_charge)
        
#         for V_10 in range(max_V_surplus + 1) : 
#             V = V_10/PRECISION

#             # surplus_pv = max(0, PV[t] - DEM[t] - max(0, X - soc))
#             # V = min(V, surplus_pv)

#             energie_dispo = PV[t] + soc
#             demande = DEM[t] + V + X

#             A = max(demande - energie_dispo, 0)
#             well = max(0, PV[t] - demande + soc)

#             new_soc = min(Bmax, X)

#             # try :
#             current_cost = ( (abs(X-soc))*bess_opex + (A*malus_achat - V*malus_vente)*ELECPRICE[t] )
#             # except :
#             #     current_cost = 0
#             #     print("Index out of range : ", t)
#             future_cost, _ = dp_charge_vente(t+1, end, new_soc, Bmax) # Équation de Bellman
#             total_cost = current_cost + future_cost

#             if total_cost < min_cost:
#                 min_cost = total_cost
#                 best_action = (X_10, V_10)

#     return (min_cost, best_action)


# from functools import cache
# from enum import Enum


# @cache
# def dp_diminuee(t: int, end: int, soc: int, Bmax: int, cycle_state: int):
#     """
#     Version qui permet de continuer le même cycle (charge multiple puis décharge multiple)
#     mais limite à une seule transition entre charge et décharge par jour.
#     """
#     NO_CYCLE = 0  # Aucun cycle commencé
#     IN_CHARGE_CYCLE = 1  # En cours de cycle de charge (peut continuer à charger ou passer en décharge)
#     IN_DISCHARGE_CYCLE = 2  # En cours de cycle de décharge (peut continuer à décharger ou passer en charge)
#     CYCLE_COMPLETE = 3  # Cycle complet terminé (charge→décharge ou décharge→charge déjà fait)
    
#     if t > end:
#         return (0, None)

#     # Réinitialiser l'état du cycle à chaque nouvelle journée
#     if t % 24 == 0:
#         cycle_state = NO_CYCLE

#     min_cost = float('inf')
#     best_action = None

#     min_X = int(max(0, soc * PRECISION - BESS_PUISS))
#     max_X = int(min(Bmax, soc * PRECISION + BESS_PUISS))

#     for X_10 in range(min_X, max_X + 1):
#         for V_10 in range(BESS_PUISS + 1 - int(abs(X_10 / PRECISION - soc))):
#             X = X_10 / PRECISION
#             V = V_10 / PRECISION

#             # Déterminer le type d'action
#             is_charging = X > soc
#             is_discharging = X < soc
#             is_idle = X == soc

#             # Logique de transition d'état du cycle
#             next_cycle_state = cycle_state

#             if cycle_state == NO_CYCLE:
#                 if is_charging:
#                     next_cycle_state = IN_CHARGE_CYCLE
#                 elif is_discharging:
#                     next_cycle_state = IN_DISCHARGE_CYCLE
#                 # Si idle, reste NO_CYCLE

#             elif cycle_state == IN_CHARGE_CYCLE:
#                 if is_charging:
#                     next_cycle_state = IN_CHARGE_CYCLE  # Continue à charger
#                 elif is_discharging:
#                     next_cycle_state = CYCLE_COMPLETE  # Transition charge→décharge
#                 # Si idle, reste IN_CHARGE_CYCLE

#             elif cycle_state == IN_DISCHARGE_CYCLE:
#                 if is_charging:
#                     next_cycle_state = CYCLE_COMPLETE  # Transition décharge→charge
#                 elif is_discharging:
#                     next_cycle_state = IN_DISCHARGE_CYCLE  # Continue à décharger
#                 # Si idle, reste IN_DISCHARGE_CYCLE

#             elif cycle_state == CYCLE_COMPLETE:
#                 # Une fois le cycle complet, seule l'inaction est permise
#                 if not is_idle:
#                     continue

#             energie_dispo = PV[t] + soc
#             demande = DEM[t] + V + X
#             A = max(demande - energie_dispo, 0)

#             new_soc = min(Bmax, X)

#             current_cost = (abs(X - soc) * bess_opex + (A * malus_achat - V * malus_vente) * ELECPRICE[t])
#             future_cost, _ = dp_diminuee(t + 1, end, new_soc, Bmax, next_cycle_state)
#             total_cost = current_cost + future_cost

#             if total_cost < min_cost:
#                 min_cost = total_cost
#                 best_action = (X_10, V_10)

#     return (min_cost, best_action)

# @cache
# def dp_cycle(t: int, end: int, soc: int, Bmax: int, has_charged: bool = False, has_discharged: bool = False, last_state = "nothing"):
#     """
#     Version ultra-simple : on compte juste si on a chargé et déchargé dans la journée
#     """
#     if t > end:
#         return (0, None)
    
#     # Réinitialiser à chaque nouvelle journée
#     if t % 24 == 0:
#         has_charged = False
#         has_discharged = False
#         last_state = "nothing"
    
#     min_cost = float('inf')
#     best_action = None

#     min_X = int(max(0, soc * PRECISION - BESS_PUISS))
#     max_X = int(min(Bmax, soc * PRECISION + BESS_PUISS))

#     for X_10 in range(min_X, max_X + 1) :
#         max_V = BESS_PUISS + 1 - int(abs(X_10 / PRECISION - soc))

#         for V_10 in range(max_V) :
#             X = X_10 / PRECISION
#             V = V_10 / PRECISION
            
#             is_charging = X > soc
#             is_discharging = X < soc

#             if is_charging : 
#                 last_state = "charging"
#             elif is_discharging : 
#                 last_state = "discharging"
            
#             # Mettre à jour les flags
#             next_has_charged = has_charged or is_charging
#             next_has_discharged = has_discharged or is_discharging
            
#             # Bloquer si on a déjà fait un cycle complet (chargé ET déchargé) et qu'on veut encore agir
#             if next_has_charged and next_has_discharged : 
#                 if is_charging and last_state == "discharging" : 
#                     continue
#                 elif is_discharging and last_state == "charging" :
#                     continue

#             # if next_has_charged and next_has_discharged and (is_charging or is_discharging):
#             #     continue
            
#             energie_dispo = PV[t] + soc
#             demande = DEM[t] + V + X
#             A = max(demande - energie_dispo, 0)
            
#             new_soc = min(Bmax, X)
            
#             current_cost = (abs(X - soc) * bess_opex + (A * malus_achat - V * malus_vente) * ELECPRICE[t])
#             future_cost, _ = dp_cycle(t + 1, end, new_soc, Bmax, next_has_charged, next_has_discharged, last_state)
#             total_cost = current_cost + future_cost

#             if total_cost < min_cost:
#                 min_cost = total_cost
#                 best_action = (X_10, V_10)

#     return (min_cost, best_action)


# @cache
# def dp_charge_vente_new(t: int, end:int, soc: int, Bmax: int) :
#     """
#     Simule le comportement d'un système Maison-PV-batterie qui peut vendre, acheter et stocker 
#     de l'électricité.
    
#     Entrée : 
#     - PV : production PV à chaque pas de temps
#     - BESS_PUISS : Puissance de la batterie. Détermine le max à charger/décharger par pas de temps
#     - PRECISION : facteur de division (exemple : BESS_PUISS = 60, PRECISION = 10 : vrai puissance = 6 kWh)
#     - DEM = demande à chaque pas de temps
#     - ELECPRICE = prix de l'électricité à chaque pas de temps
#     """
#     if t > end:
#         return (0, None)
    
#     min_cost = float('inf')
#     best_action = None

#     # Bornes de X basées sur la puissance max
#     min_X = int(max(0, soc*PRECISION - BESS_PUISS))
#     max_X = int(min(Bmax, soc*PRECISION + BESS_PUISS))

#     for X_10 in range(min_X, max_X+1) : 
#         max_range_V = BESS_PUISS - int(abs(X_10 - soc*PRECISION)) + 1
#         for V_10 in range(max_range_V) : 
#             X = X_10/PRECISION
#             V = V_10/PRECISION

#             energie_dispo = PV[t] + soc
#             demande = DEM[t] + V + X

#             A = max(demande - energie_dispo, 0)

#             new_soc = min(Bmax, X)

#             current_cost = ( (abs(X-soc))*bess_opex + (A*malus_achat - V*malus_vente)*ELECPRICE[t] )
#             future_cost, _ = dp_charge_vente(t+1, end, new_soc, Bmax) # Équation de Bellman
#             total_cost = current_cost + future_cost

#             if total_cost < min_cost:
#                 min_cost = total_cost
#                 best_action = (X_10, V_10)

#     return (min_cost, best_action)


@cache
def dp_charge_vente(t: int, end:int, soc: int, Bmax: int) :
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
    
    if t % 24 == 0 :
        soc = 0
    
    min_cost = float('inf')
    best_action = None

    surplus_pv = max(0, PV[t] - DEM[t]) * PRECISION
    # surplus_pv = PV[t] * PRECISION

    # Bornes de X basées sur la puissance max
    decharge = BESS_PUISS
    charge = min(BESS_PUISS / 4, surplus_pv) 
    min_X = int(max(0, soc*PRECISION - decharge))
    max_X = int(min(Bmax, soc*PRECISION + charge))

    for X_10 in range(min_X, max_X+1) : 
        X = X_10/PRECISION

        energie_dispo = PV[t] + soc
        demande = DEM[t] + X

        A = max(demande - energie_dispo, 0)

        new_soc = min(Bmax, X)

        current_cost = ( (abs(X-soc))*bess_opex + (A*malus_achat)*ELECPRICE[t] )
        if t == 8736 :
            future_cost, _ = 0, None
        else :
            future_cost, _ = dp_charge_vente(t+1, end, new_soc, Bmax) # Équation de Bellman
        total_cost = current_cost + future_cost

        if total_cost < min_cost:
            min_cost = total_cost
            best_action = (X_10)

    return (min_cost, best_action)




