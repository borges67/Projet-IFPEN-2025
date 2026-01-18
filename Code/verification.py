import pandas as pd
from collections import Counter
from config import config as cf

# Chemin vers votre fichier
DATA_DIR = cf.PROJECT_ROOT / "data"
INPUT_PYTHON_DIR = DATA_DIR / "input_residential"
INPUT_GAMS_DIR = DATA_DIR / "input_national"
OUTPUT_GAMS_DIR = DATA_DIR / "Modele_chronologique"

DEMANDM_PATH = OUTPUT_GAMS_DIR / "demandM.csv"
DEMANDFOYER_PATH = INPUT_PYTHON_DIR / f"Demande Foyer-{cf.annee_conso_foyer}.csv"

# Lire le fichier
df_dem = pd.read_csv(DEMANDFOYER_PATH, sep=';')

print("=== ANALYSE DU FICHIER DE DEMANDE ===")
print(f"Nombre total de lignes : {len(df_dem)}")
print(f"Nombre de colonnes : {len(df_dem.columns)}")
print(f"Colonnes : {df_dem.columns.tolist()}")

# Vérifier les dates uniques et compter le nombre d'heures par date
print("\n=== COMPTAGE DES HEURES PAR DATE ===")
dates_count = df_dem['Date'].value_counts().sort_index()
print(f"Nombre de dates uniques : {len(dates_count)}")

# Trouver les dates qui n'ont pas 24 heures
dates_with_problems = dates_count[dates_count != 24]
print(f"\n=== DATES AVEC UN NOMBRE D'HEURES DIFFÉRENT DE 24 ===")
if len(dates_with_problems) > 0:
    for date, count in dates_with_problems.items():
        print(f"Date {date} : {count} heures")
else:
    print("Aucune date avec un nombre d'heures différent de 24")

# Vérifier la plage de dates
print(f"\n=== PLAGE DE DATES ===")
print(f"Première date : {df_dem['Date'].min()}")
print(f"Dernière date : {df_dem['Date'].max()}")

# Vérifier les heures pour chaque date
print(f"\n=== VÉRIFICATION DÉTAILLÉE PAR DATE ===")
all_dates = df_dem['Date'].unique()
all_dates.sort()

for date in all_dates:
    date_data = df_dem[df_dem['Date'] == date]
    heures = date_data['Heure'].tolist()

    if len(heures) != 24:
        print(f"PROBLÈME - Date {date} : {len(heures)} heures au lieu de 24")
        print(f"  Heures présentes : {sorted(heures)}")

        # Trouver les heures manquantes
        heures_attendues = list(range(24))
        heures_manquantes = [h for h in heures_attendues if h not in heures]
        if heures_manquantes:
            print(f"  Heures manquantes : {heures_manquantes}")

        heures_en_double = [h for h, count in Counter(heures).items() if count > 1]
        if heures_en_double:
            print(f"  Heures en double : {heures_en_double}")
    else:
        # Vérifier si toutes les heures de 0 à 23 sont présentes
        heures_presentes = sorted(heures)
        if heures_presentes != list(range(24)):
            print(f"PROBLÈME - Date {date} : heures non consécutives")
            print(f"  Heures présentes : {heures_presentes}")

# Vérifier les doublons
print(f"\n=== RECHERCHE DE DOUBLONS ===")
doublons = df_dem[df_dem.duplicated(subset=['Date', 'Heure'], keep=False)]
if len(doublons) > 0:
    print(f"Doublons trouvés : {len(doublons)} lignes")
    print(doublons[['Date', 'Heure']].head(10))
else:
    print("Aucun doublon trouvé")

# Vérifier les valeurs manquantes
print(f"\n=== VALEURS MANQUANTES ===")
valeurs_manquantes = df_dem.isnull().sum()
print(valeurs_manquantes)

# Calcul du nombre théorique de lignes
print(f"\n=== CALCUL THÉORIQUE ===")
nombre_dates = len(dates_count)
lignes_theoriques = nombre_dates * 24
print(f"Nombre de dates : {nombre_dates}")
print(f"Lignes théoriques (dates × 24) : {nombre_dates} × 24 = {lignes_theoriques}")
print(f"Lignes réelles : {len(df_dem)}")
print(f"Différence : {lignes_theoriques - len(df_dem)}")

# Si la différence est de 1, chercher quelle heure spécifique manque
if lignes_theoriques - len(df_dem) == 1:
    print(f"\n=== RECHERCHE DE L'HEURE MANQUANTE ===")
    # Créer un DataFrame avec toutes les combinaisons date-heure attendues
    toutes_dates = df_dem['Date'].unique()
    toutes_heures = list(range(24))

    combinaisons_attendues = []
    for date in toutes_dates:
        for heure in toutes_heures:
            combinaisons_attendues.append((date, heure))

    combinaisons_reelles = list(zip(df_dem['Date'], df_dem['Heure']))

    combinaison_manquante = set(combinaisons_attendues) - set(combinaisons_reelles)
    if combinaison_manquante:
        print(f"Combinaison date-heure manquante : {list(combinaison_manquante)[0]}")

print(f"\n=== RÉSUMÉ ===")
print(f"Le fichier contient {len(df_dem)} lignes sur {lignes_theoriques} attendues")