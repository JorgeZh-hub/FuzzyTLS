#!/bin/bash

# Ejecutar el script Python para generar rutas
python3 generate_routes.py

# Ejecutar SUMO con el archivo de configuración osm_static.sumocfg
sudo sumo -c ./sumo_files/osm_static.sumocfg
python3 /opt/sumo/tools/xml/xml2csv.py -s , ./sumo_files/tripinfo_static.xml -o ./tripinfo_static.csv
#python3 /opt/sumo/tools/xml/xml2csv.py -s , ./sumo_files/stats_static.xml -o ./stats_static.csv

# Ejecutar SUMO con el archivo de configuración osm_actuated.sumocfg
sudo sumo -c ./sumo_files/osm_actuated.sumocfg
python3 /opt/sumo/tools/xml/xml2csv.py -s , ./sumo_files/tripinfo_actuated.xml -o ./tripinfo_actuated.csv
#python3 /opt/sumo/tools/xml/xml2csv.py -s , ./sumo_files/stats_actuated.xml -o ./stats_actuated.csv

# Ejecutar SUMO con TraCi para el algoritmo de control
python Controller_30_rules.py
python3 /opt/sumo/tools/xml/xml2csv.py -s , ./sumo_files/tripinfo_fuzzy.xml -o ./tripinfo_fuzzy.csv
#python3 /opt/sumo/tools/xml/xml2csv.py -s , ./sumo_files/stats_fuzzy.xml -o ./stats_fuzzy.csv

#python3 /opt/sumo/tools/xml/xml2csv.py -s , ./Project1/tripinfos.xml
#python3 /opt/sumo/tools/xml/xml2csv.py -s , ./teleports.xml
# Ejecutar el script Python para graficar
python3 ../plotters/barras.py
