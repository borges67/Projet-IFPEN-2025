import pandas as pd
from tqdm import tqdm

from config import config as cf

# ----- Données -----
SEMAINES = cf.SEMAINES

PRECISION = cf.PRECISION
malus_achat = cf.MALUS_ACHAT
malus_vente = cf.MALUS_VENTE
sto = cf.STO

BESS_PUISS = cf.BESS_PUISS
bess_opex = cf.BESS_OPEX
bess_capex = cf.BESS_OPEX

DEM = cf.DEM
ELECPRICE = cf.ELECPRICE
PV_probs = cf.PV_PROBS
PV = cf.PV
df_pv = cf.DF_PV

n = cf.n
TA = cf.taxes

df = cf.DF

# ----- Fonctions -----
import battery_layer as batt

def max_BESS_installed(BESS_MAX_TEST: int) :
    min_total = float('inf')
    best = None
    cost_zero = 0
    for Bmax in BESS_MAX_TEST :
        if Bmax == 0 : 
            cost_zero, _ = batt.dp_charge_vente_zero(1, 0, Bmax)
        elif Bmax != 0 : 
            cost, _ = batt.dp_charge_vente(1, 0, Bmax)
            couts_actualises = bess_capex[Bmax] - sum(list((cost_zero - cost)/(1 + TA)**i for i in range(n))) # Coût batterie - Gains grâce à la batterie 
            print(round(couts_actualises, 2))
            if couts_actualises < min_total :
                min_total = couts_actualises
                best = (cost, bess_capex[Bmax], couts_actualises, Bmax)
    return best

def week_behavior(Bmax: int) -> list :
    for semaine in SEMAINES :
        if sto : 
            cost, best_action = batt.dp_charge_vente_sto(SEMAINES[semaine][0][0], SEMAINES[semaine][0][-1], 0, Bmax)
        else :
            cost, best_action = batt.dp_charge_vente(SEMAINES[semaine][0][0], SEMAINES[semaine][0][-1], 0, Bmax)
        print(semaine)
        # SEMAINES[semaine][1] = best_action
    # cost_zero, _ = dp_charge_vente(1, 0, BESS_CAPA)
    # cost, _ = dp_charge_vente(1, 0, BESS_CAPA)
    # couts_actualises = bess_capex[BESS_CAPA] - sum(list((cost_zero - cost)/(1 + TA)**i for i in range(n))) # Coût batterie - Gains grâce à la batterie 
    return None

def weeks_behavior(Bmax: int) :
    df_base = pd.DataFrame(columns=['Saison', 'Date', 'Heure', 'Demande', 'Prod PV', 'SOC_t', 'Vente', 'Achat', 'Well', 'Prix elec'])

    for semaine in SEMAINES :
        df_sem = pd.DataFrame(columns=['Saison', 'Date', 'Heure', 'Demande', 'Prod PV', 'SOC_t', 'Vente', 'Achat', 'Well', 'Prix elec'])
        print(semaine)
        start = SEMAINES[semaine][0][0]
        end = SEMAINES[semaine][0][-1]

        print("Modélisation simple du comportement d'un système PV-batterie")
        batt.dp_charge_vente(start, end, 0, Bmax)

        # Simulation pour récupérer l'historique
        current_soc = 0
        history_soc = []
        history_vente = []
        history_achat = []
        history_well = []

        for t in range(start, end):
            history_soc.append(current_soc)

            _, best_action = batt.dp_charge_vente(t, end, current_soc, Bmax)

            if best_action is None:
                break

            X_10, V_10 = best_action
            X = X_10/PRECISION
            V = V_10/PRECISION

            # Calcul de l'achat
            energie_dispo = PV[t] + current_soc
            demande = DEM[t] + V + X
            A = max(demande - energie_dispo, 0)
            well = max(0, PV[t] - demande + current_soc)
            history_vente.append(V)
            history_achat.append(A)
            history_well.append(well)
            new_soc = min(Bmax, X)
            current_soc = new_soc

        df_sem = pd.DataFrame({
            'Saison': [semaine] * (end - start),
            'Date': df_pv['Date'][start:end],
            'Heure': df_pv['Heure Journee'][start:end],
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

def annual_behavior(Bmax: int) :
    df_base = pd.DataFrame(columns=['Saison', 'Date', 'Heure', 'Demande', 'Prod PV', 'SOC_t', 'Vente', 'Achat', 'Well', 'Prix elec'])

    YEAR_WEEKS = {
        sem: [list(range((sem - 1) * 168, sem * 168)), []]
        for sem in range(1, 3)  # 52 semaines
    }

    # with tqdm(total=52 * 168, desc="Progression totale", unit="heure") as pbar_total:
    #     for semaine, (heures, _) in enumerate(tqdm(YEAR_WEEKS.items(), desc="Semaines"), 1):

    for semaine, (heures, _) in YEAR_WEEKS.items():
        df_sem = pd.DataFrame(columns=['Saison', 'Date', 'Heure', 'Demande', 'Prod PV', 'SOC_t', 'Vente', 'Achat', 'Well', 'Prix elec'])
        print(f"Semaine {semaine}")

        start = heures[0]
        end = heures[-1]

        print("Modélisation simple du comportement d'un système PV-batterie")
        batt.dp_charge_vente(start, end, 0, Bmax)
        print("Modélisation intialisée")

        # Simulation pour récupérer l'historique
        current_soc = 0
        history_soc = []
        history_vente = []
        history_achat = []
        history_well = []

        for t in range(start, end):
            print(t)
            history_soc.append(current_soc)

            _, best_action = batt.dp_charge_vente(t, end, current_soc, Bmax)

            if best_action is None:
                break

            X_10, V_10 = best_action
            X = X_10/PRECISION
            V = V_10/PRECISION

            # Calcul de l'achat
            energie_dispo = PV[t] + current_soc
            demande = DEM[t] + V + X
            A = max(demande - energie_dispo, 0)
            well = max(0, PV[t] - demande + current_soc)
            history_vente.append(V)
            history_achat.append(A)
            history_well.append(well)
            new_soc = min(Bmax, X)
            current_soc = new_soc

        df_sem = pd.DataFrame({
            'Saison': [semaine] * (end - start),
            'Date': df_pv['Date'][start:end],
            'Heure': df_pv['Heure Journee'][start:end],
            'Demande': DEM[start:end],
            'Prod PV': PV[start:end],
            'SOC_t': history_soc,
            'Vente': history_vente,
            'Achat': history_achat,
            'Well': history_well,
            'Prix elec': ELECPRICE[start:end]
        })

        # test = 0 * (end - start)
        # df_sem = pd.DataFrame({
        #     'Saison': test,
        #     'Date': test,
        #     'Heure': test,
        #     'Demande': test,
        #     'Prod PV': test,
        #     'SOC_t': test,
        #     'Vente': test,
        #     'Achat': test,
        #     'Well': test,
        #     'Prix elec': test
        # })

        df_base = pd.concat([df_base, df_sem]).round(3)

    return df_base



def full_year_df_creation(df) :
    segments = []

    saisons_config = [
        ('hiver', 10),
        ('printemps', 12),
        ('ete', 14),
        ('automne', 12),
        ('hiver', 4),
        ]

    for saison, repetitions in saisons_config:
        semaine_type = df[df['Saison'] == saison]
        
        segment = pd.concat([semaine_type] * repetitions, ignore_index=True)
        segments.append(segment)

    full_year_df = pd.concat(segments, ignore_index=True)
    
    full_year_df.index += 1
    return full_year_df