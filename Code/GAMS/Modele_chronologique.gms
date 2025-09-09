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

* -------------------------------------------------------------------------------------------------------------------------------
* --------- Centrales de production d'électricité
* -------------------------------------------------------------------------------------------------------------------------------

Set iunit Power plant /
    NPP     Nuclear Power Plant,
    THC     Coal Thermal power plant,
    CTP     Combustion turbine Power Plant,
    CCG     Combined Cycle Gas turbine Power plant,
    WPO     Windpower,
    PVP     Photovoltaic (with subsidies),
    HYW     Hydraulic water-flow station,
    IPO     Imports,
    IPVP    Imports of PV
    /;

Set iurenew(iunit)/WPO,PVP,HYW/;

Set ifuel Combustibles /
    OU Uranium 233,
    COAL  Hard coal,
    HTO   Heating Fuel Domestic,
    GAS   Gas,
    WI    Wind,
    SU    Sun,
    WA    Water
    /;

* Capacités iniiales
Parameter capini(iunit) GW /
    NPP   61.37
    THC   1.810
    CTP   2.628
    CCG   12.624
    WPO   23.273
    PVP   18.816
    HYW   11
    IPO   999.
    IPVP  11.
    /;

* On passe en MW pour exprimer les capacités installées
loop(iunit, capini(iunit)=1000*capini(iunit));

Scalar nb_bess Nombte de maisons équipées de batteries / 1000000 /;

* Disponibilité  -------------------------------------------------------------------------------
parameter dispo(iunit, t) Disponibilité de chaque centrale en fonction de la période ;
loop(t, loop(iunit, dispo(iunit, t) = 1) ;);
dispo("NPP", t) = 0.90 ;
dispo("THC", t) = 0.85 ;
dispo("CTP", t) = 0.95 ;
dispo("CCG", t) = 0.95 ;
dispo("WPO", t) = 0.30 ;
*dispo("PVP", t) = 0.15 ;
*dispo("IPVP", t) = 0.15 ;
dispo("IPO", t) = 1.00 ;

PARAMETER dispo_PV(t) %
/
$ondelim
$include %dispo_PV_csv%
$offdelim
/;

loop(t, dispo("PVP", t) =
    dispo_PV(t)
);

loop(t, dispo("IPVP", t) =
    dispo_PV(t)
);

scalar Eolien_puiss / 2800/;

PARAMETER dispo_eolien(t) %
/
$ondelim
$include %dispo_eolien_csv%
$offdelim
/;

loop(t, dispo("WPO", t) =
    dispo_eolien(t) 
);

set interunitfuel(iunit,ifuel) Combustible de chaque centrale
    /NPP.OU,THC.COAL,CTP.HTO,CCG.GAS, WPO.WI, PVP.SU, HYW.WA, IPO.COAL, IPVP.SU/;

Table alpha(iunit,ifuel) Rendement des centrales [%]
* MWh combustible => MWh électrique ou Combien de MWh électrique proviennent d'1 MWh combustible
               OU           COAL         HTO          GAS        WI         SU           WA
    NPP        0.360        0.000        0.000        0.000      0.000      0.000        0.000
    THC        0.000        0.400        0.000        0.000      0.000      0.000        0.000
    CTP        0.000        0.000        0.330        0.330      0.000      0.000        0.000
    CCG        0.000        0.000        0.000        0.550      0.000      0.000        0.000
    WPO        0.000        0.000        0.000        0.000      1.000      0.000        0.000
    PVP        0.000        0.000        0.000        0.000      0.000      1.000        0.000
    HYW        0.000        0.000        0.000        0.000      0.000      0.000        1.000
    IPO        0.000        0.400        0.000        0.000      0.000      0.000        0.000
    IPVP       0.000        0.000        0.000        0.000      0.000      1.000        0.000   
    ;

* -------------------------------------------------------------------------------------------------------------------------------
* --------- Calcul du coût des combustibles 
* -------------------------------------------------------------------------------------------------------------------------------

*On veut convertir les €/t en $/MWh

Parameter fuelcost1(ifuel) Dollars (euros par défaut) par tonne
    /OU    60.370
    COAL   129.540
    HTO    82.640
    GAS    12.870
    WI     0.0
    SU     0.0
    WA     0.0
    /;
* OU : US$/lb_U308
* COAL : US$/t (dollars par tonne)
* HTO : US$/bbl (dollars par barril)
* GAS : US$/MBtu (dollars par million de BTU)

set convdollar(ifuel) Combustibles dont les valeurs sont en $ (on doit donc les convertir)
    /OU   yes
    COAL  yes
    HTO   yes
    GAS   yes/;
    
* Fuel cost exprimé en euros
set conveuro(ifuel) Combustibles dont les valeurs sont déjà en € (on n'a pas besoin des les convertir)
    //;

* Facteur de conversion : on a des euros / tonne, on souhaite des euros / MWh ==> ce sont des MWh / tonne
Parameter factconv(ifuel) ;
loop(ifuel, factconv(ifuel)=1);
Factconv('OU')= 16.667;
Factconv('COAL')= 8.010  ;
Factconv('HTO') = 1.700  ;
Factconv('GAS') = 0.293  ;
* OU : 16.667lb_U308/MWh
* COAL : 8.01 MWh/t (tonne de charbon équivaut à 8.01 MWh).
* HTO  : 1.7 Boe (barril equivalent oil) / MWh
* GAS : 0.293 MWh/MBtu (1 million de BTU de gaz équivaut à 0.293 MWh).

* Conversion Euros => Dollar [dollars / euro]
* Valeur spot 14 Mars 2025
scalar exchrate / 1.087/;

Parameter fuelcost2(ifuel);
LOOP(ifuel$convdollar(ifuel),
fuelcost2(ifuel)=fuelcost1(ifuel)/exchrate;
);
* On divise par le facteur de conversio Euro -> Dollar

LOOP(ifuel,
fuelcost2(ifuel)=fuelcost2(ifuel)/factconv(ifuel);
);
* On divise par le facteur de conversion t -> MWh

Parameter fuelcost3(ifuel);
LOOP(ifuel$conveuro(ifuel),
fuelcost3(ifuel)=fuelcost1(ifuel)/factconv(ifuel);
);
* On divise par le facteur de conversion t -> MWh

Parameter fuelcost4(ifuel);
LOOP(ifuel,
fuelcost4(ifuel)= fuelcost3(ifuel)+fuelcost2(ifuel);
);
* On groupe le tout : €/MWh

* -------------------------------------------------------------------------------------------------------------------------------
* --------- CO2 (émissions et coût)
* -------------------------------------------------------------------------------------------------------------------------------

Scalar co2cost euro par tCO2
    /70/;

* Emissions par fuel en tCO2/MWh
Parameter em(ifuel)
    /OU     0.006
    COAL    0.986
    HTO     0.777
    GAS     0.494
    SU      0.0
    WI      0.0
    WA      0.0/;
    
* -------------------------------------------------------------------------------------------------------------------------------
* --------- Demande et disponibilité
* -------------------------------------------------------------------------------------------------------------------------------
    
PARAMETER demelec(t) MW
/
$ondelim
$include %demandeNAT_csv%
$offdelim
/;

* -------------------------------------------------------------------------------------------------------------------------------
* --------- Coûts fixes, variables, initiaux
* -------------------------------------------------------------------------------------------------------------------------------

Parameter fcost(iunit) /
* Coûts fixes annuel - euro/MWh incluant le coût du capital ((à multiplier par 8760 dans les coûts car ici €/MWh)
* Les données sont convertis directement en €, taux de conversion prix du 26 Mars 2025
    NPP   19.35
    THC   7.65
    CTP   0.90
    CCG   0.90
    WPO   3.49
    PVP   2.13
    HYW   4.17
    IPO   0.0
    IPVP  0.0
    /;

Parameter vcost(iunit) /
* Coûts variables - euro/MWh 
    NPP    2.33
    THC    5.92
    CTP    5.92
    CCG    1.14
    WPO    0.
    PVP    0.
    HYW    0.0
    IPO    50.
    IPVP   0
    /;

vcost(iunit) = vcost(iunit) * 15;


Parameter invcost(iunit) /
* Coûts d'investissement d'une nouvelle centrale - euro/MWh (à multiplier par 8760 dans les coûts car ici €/MWh)
*TA de 7%
    NPP    24.44
    THC    25.52
    CTP    5.35
    CCG    5.35
    WPO    29.88
    PVP    37.06
    HYW    22.23
    IPO    0.
    IPVP   0.
    /;

Parameter sub(iunit) /
* Montant des subventions - €/MWh produits
    NPP    0.
    THC    0.
    CTP    0.
    CCG    0.
    WPO    0.
    PVP    0
    HYW    0.
    IPO    0.
    IPVP   0.
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
* ------------------------------------------------------------------------------------------------------

Parameter demnetWhydro(t);
LOOP(t, demnetWhydro(t) =
  demelec(t)
- dispo('HYW',t)*capini('HYW')
- bess(t)
+ achat(t)
);

Parameter demnet(t);
LOOP(t, demnet(t) =
  demelec(t)
- bess(t)
+ achat(t)
);

* -------------------------------------------------------------------------------------------------------------------------------
* --------- Contrainte sur les investissements maximaux
* -------------------------------------------------------------------------------------------------------------------------------

Parameter invmax(iunit)/
* Ajouts maximaux de moyen de production - MW
    NPP    21000.
    THC    0.
    CTP    1000.
    CCG    10000.
    WPO    20000.
    PVP    600.
    HYW    0.
    IPO    0.
    IPVP   0.
    /;

* -------------------------------------------------------------------------------------------------------------------------------
* --------- Définition des variables
* -------------------------------------------------------------------------------------------------------------------------------

Variables
       puiss(iunit,t)              Power loaded on the grid [MW]
       inv(iunit)                          Investment [MW]
       capavailable(iunit, t)     Available capacity
       capro(iunit)                        Capacity of production
       emiss(ifuel,iunit,t)        Emissions per unit [tonnes]
       emiss_tot 
       z                                   Cost
       fuel(ifuel,iunit,t)         Fossil and Free Feedstock to supply the unit [MWh]

Positive Variables puiss,inv,capavailable,capro,emiss,fuel ;

* -------------------------------------------------------------------------------------------------------------------------------
* --------- Définition des équations
* -------------------------------------------------------------------------------------------------------------------------------

Equations
cost
fuelneed(iunit, t)
emission(ifuel,iunit,t)
emiss_calc
capa(iunit)
capacity(iunit,t)
invest
supply(iunit,t)
supplyH(t)
demand(t)
;

* -------------------------------------------------------------------------------------------------------------------------------
* --------- Fonction objective
* -------------------------------------------------------------------------------------------------------------------------------
cost.. z =e=
* Coût variable d'exploitation : 
sum((t,iunit), vcost(iunit)* Puiss(iunit,t))

* Coûts fixes et coûts d'investissement (multiplié par 8760 car la valeur est en €/MWh) : 
+ sum(iunit, 8760*(invcost(iunit) * inv(iunit) + capro(iunit) * fcost(iunit)) )

* Coûts de combustible : 
+ sum((ifuel,iunit,t)$interunitfuel(iunit, ifuel), fuelcost4(ifuel) * fuel(ifuel, iunit, t))

* Coûts d'émissions de CO2 :
+ sum((ifuel, iunit, t)$interunitfuel(iunit, ifuel), co2cost * emiss(ifuel, iunit, t))

* Diminution du coût dû au aides gouvernementales : 
- sum(iunit, (sum(t, sub(iunit) * PUISS(iunit,t))))
;

* -------------------------------------------------------------------------------------------------------------------------------
* --------- Contraintes
* -------------------------------------------------------------------------------------------------------------------------------

* --------- Efficacité des centrales à combustible
fuelneed(iunit,t)..
PUISS(iunit,t) =e= sum(ifuel$interunitfuel(iunit,ifuel), alpha(iunit,ifuel) * fuel(ifuel,iunit,t)) ;

* --------- Émissions produites par le système
emission(ifuel, iunit, t)..
emiss(ifuel, iunit, t) =e= fuel(ifuel, iunit, t) * em(ifuel) ;

* --------- Émissions totales
emiss_calc..
emiss_tot =e= sum((ifuel, iunit, t), emiss(ifuel, iunit, t)) ;

* --------- Capacités de production
capa(iunit) .. capro(iunit) =e= capini(iunit) + inv(iunit) ;
capacity(iunit, t) .. capavailable(iunit, t) =e= capro(iunit) * dispo(iunit, t) ;
invest(iunit).. inv(iunit) =l= invmax(iunit) ;

* --------- Production d'électricité
supply(iunit,t) .. puiss(iunit,t) =l= capavailable(iunit, t);
supplyH(t)..   puiss('HYW',t) =e=  capavailable('HYW', t) ;

* --------- Fonction de production = demande (+ charge batteries)
demand(t).. sum(iunit, PUISS(iunit,t)) =g= demnetWhydro(t) ;

* -------------------------------------------------------------------------------------------------------------------------------
* --------- Lancement du modèle
* -------------------------------------------------------------------------------------------------------------------------------

Model Elec /all/;

Solve Elec using lp minimizing z ;

Parameter marginalcost(t);
marginalcost(t) = demand.m(t)

display demelec
display demnet
display demand.m
display dispo
display fuelcost4
display bess
display achat
display dispo_PV

*--- Exporter les valeurs marginales dans demandM.csv ---
* Ouvrir un fichier pour écrire les valeurs marginales
file demandM /%demandM_csv%/;
put demandM;
demandM.PC= 5;
demandM.ND= 3;
demandM.PW= 255;
* Écrire l'en-tête du fichier CSV
put "periode",put "marginale"/;
* Itérer sur les périodes et écrire les valeurs marginales
loop(t,
    put ord(t):0:0,put demand.m(t):10:3/; 
);
putclose demandM;

*--- Exporter les valeurs de production pour le calcul des prix ---
file prodValues /%prodValues_csv%/;
put prodValues;
prodValues.PC= 5;
prodValues.ND= 3;
prodValues.PW= 255;
* Écrire l'en-tête du fichier CSV
put "periode",put "prod totale", put "prod PV", put "prod eolien"/;
* Itérer sur les périodes et écrire les valeurs marginales
loop(t,
    put ord(t):0:0, put demnet(t):10:3, put puiss.l('PVP', t):10:3, put puiss.l('WPO', t):10:3/; 
);
putclose prodValues;

*--- Exporter les résultats pour tracer des graphiques ---
* Ouvrir un fichier pour écrire les valeurs marginales
file results /%results_csv%/;
put results;
results.PC= 5;
results.ND= 3;
results.PW= 255;
* Écrire l'en-tête du fichier CSV
put "periode",put "demande brute", put "demande nette"/;
* Itérer sur les périodes et écrire les valeurs marginales
loop(t,
    put ord(t):0:0,put demelec(t), put demnet(t) /; 
);
putclose results;


