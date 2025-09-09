* Pour tous les problèmes MIP (Mixed-Integer Programming, GAMS utilisera le solveur CPLEX au lieu du solveur par défaut)
option mip=cplex

* Imports
$setglobal bessSOC_csv ../../data/input_national/bessSOC.csv
$setglobal achat_csv ../../data/input_national/achat.csv
$setglobal demandeNAT_csv ../../data/input_national/Demande Nat.csv
$setglobal dispo_PV_csv ../../data/input_national/dispo_PV_gams.csv
$setglobal dispo_eolien_csv ../../data/input_national/dispo_eolien_gams.csv

* Exports
$setglobal demandM_csv D:\Perso\Projet IFPEN\Projet-IFPEN-2025\data\Modele_chronologique\demandM.csv
$setglobal results_csv D:\Perso\Projet IFPEN\Projet-IFPEN-2025\data\Modele_chronologique\results.csv
$setglobal prodValues_csv D:\Perso\Projet IFPEN\Projet-IFPEN-2025\data\Modele_chronologique\prodValues.csv

*$setglobal demandM_csv demandM.csv
*$setglobal results_csv results.csv
*$setglobal prodValues_csv prodValues.csv

* -------------------------------------------------------------------------------------------------------------------------------
* --------- Périodes
* -------------------------------------------------------------------------------------------------------------------------------

set t Périodes /1*8736/;

set hiver(t), printemps_automne(t), ete(t), juillet_aout Sous-ensemble de saisons ;

* Saisons
hiver(t) = yes$(1002 < ord(t)-1 and ord(t)-1 < 1095) or (0 < ord(t) and ord(t) < 177)  ;
printemps_automne(t) = yes$(177 < ord(t)-1 and ord(t)-1 < 270) or (729 < ord(t) and ord(t) < 1002) ;
ete(t) = yes$(271 < ord(t)-1 and ord(t)-1 < 543) ;
juillet_aout(t) = yes$(544 < ord(t)-1 and ord(t)-1 < 729) ;

Scalar nb_bess Nombte de maisons équipées de batteries / 1 /;

PARAMETER dispo_PV(t) %
/
$ondelim
$include %dispo_PV_csv%
$offdelim
/;

* ------------------------------------------------------------------------------------------------------
* Importation depuis le fichier CSV de la quantité d'électricité provenant des batteries
PARAMETER bess(t) kW
/
$ondelim
$include %bessSOC_csv%
$offdelim
/;

* On multiplie par le nombre de maison puis on divise par 1000 pour convertir en MW
loop(t, bess(t) = nb_bess * bess(t) / 1000 );
* ------------------------------------------------------------------------------------------------------

* ------------------------------------------------------------------------------------------------------
* Importation depuis le fichier CSV de la quantité d'électricité acheté par les batteries
PARAMETER achat(t) kW
/
$ondelim
$include %achat_csv%
$offdelim
/;

* On multiplie par le nombre de maison puis on divise par 1000 pour convertir en MW
loop(t, achat(t) = nb_bess * achat(t) / 1000 );



display achat
display bess
display dispo_PV