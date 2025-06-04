import traci
import csv
from collections import defaultdict

# Configuración de SUMO
sumo_binary = "sumo"  # o "sumo-gui"
sumo_config = "./sumo_files/osm_actuated.sumocfg"
traci.start([sumo_binary, "-c", sumo_config])

# Semáforos y fases asociadas a carriles
semaforos_ids = [
    "2496228891",
    "cluster_12013799525_12013799526_2496228894",
    "cluster_12013799527_12013799528_2190601967",
    "cluster_12013799529_12013799530_473195061"
]

fases_lanes_dict = {
    "2496228891": {
        0: ["337277951#3_0", "337277951#3_1", "337277951#1_0", "337277951#1_0", "337277951#4_0", "337277951#4_1", "337277951#2_0", "337277951#2_1", "49217102_0"], 
        2: ["567060342#1_0", "567060342#0_0"], 
    },
    "cluster_12013799525_12013799526_2496228894": {
        0: ["42143912#5_0", "42143912#3_0", "42143912#4_0"],
        2: ["337277973#1_0", "337277973#1_1", "337277973#0_1", "337277973#0_0", "567060342#1_0", "567060342#0_0"]
    },
    "cluster_12013799527_12013799528_2190601967": {
        0: ["40668087#1_0"],
        2: ["337277981#1_1", "337277981#1_0", "337277981#2_1", "337277981#2_0", "42143912#5_0", "42143912#3_0", "42143912#4_0"]
    },
    "cluster_12013799529_12013799530_473195061": {
        0: ["49217102_0"],
        2: ["337277970#1_0", "337277970#1_1", "40668087#1_0"]
    }
}

# Variables de control
fase_actual = {}
inicio_fase = {}
historial_fases = []

print("Iniciando simulación...\n")
step = 0

try:
    while traci.simulation.getMinExpectedNumber() > 0:
        traci.simulationStep()

        for tls_id in semaforos_ids:
            fase = traci.trafficlight.getPhase(tls_id)

            if tls_id not in fase_actual:
                fase_actual[tls_id] = fase
                inicio_fase[tls_id] = step
                continue

            if fase != fase_actual[tls_id]:
                # Cambio de fase detectado
                duracion = step - inicio_fase[tls_id]
                fase_anterior = fase_actual[tls_id]

                # Contar vehículos si la fase está en el dict
                vehiculos_en_fase = 0
                if tls_id in fases_lanes_dict and fase_anterior in fases_lanes_dict[tls_id]:
                    carriles = fases_lanes_dict[tls_id][fase_anterior]
                    for lane_id in carriles:
                        vehiculos_en_fase += traci.lane.getLastStepVehicleNumber(lane_id)

                historial_fases.append({
                    "semaforo_id": tls_id,
                    "fase": fase_anterior,
                    "duracion": duracion,
                    "vehiculos_en_carriles": vehiculos_en_fase,
                    "paso_inicio": inicio_fase[tls_id]
                })

                print(f"[{step}s] Semáforo {tls_id} - Fase {fase_anterior} duró {duracion}s con {vehiculos_en_fase} vehículos")

                # Actualizar
                fase_actual[tls_id] = fase
                inicio_fase[tls_id] = step

        step += 1

    # Registrar fase final
    for tls_id in semaforos_ids:
        if tls_id in fase_actual:
            duracion = step - inicio_fase[tls_id]
            fase_anterior = fase_actual[tls_id]
            vehiculos_en_fase = 0
            if tls_id in fases_lanes_dict and fase_anterior in fases_lanes_dict[tls_id]:
                carriles = fases_lanes_dict[tls_id][fase_anterior]
                for lane_id in carriles:
                    vehiculos_en_fase += traci.lane.getLastStepVehicleNumber(lane_id)

            historial_fases.append({
                "semaforo_id": tls_id,
                "fase": fase_anterior,
                "duracion": duracion,
                "vehiculos_en_carriles": vehiculos_en_fase,
                "paso_inicio": inicio_fase[tls_id]
            })

finally:
    traci.close()

# Guardar resultados en un CSV
csv_file = "historial_fases_vehiculos.csv"
with open(csv_file, mode='w', newline='') as file:
    writer = csv.DictWriter(file, fieldnames=["semaforo_id", "fase", "duracion", "vehiculos_en_carriles", "paso_inicio"])
    writer.writeheader()
    for entry in historial_fases:
        writer.writerow(entry)

print(f"\nHistorial guardado en {csv_file}")
