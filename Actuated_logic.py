import statistics
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
        0: ["337277951#3_0", "337277951#3_1", "337277951#1_0", "337277951#1_1", "337277951#4_0", "337277951#4_1", "337277951#2_0", "337277951#2_1", "49217102_0"], 
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

# Límites de verde globales
tiempo_verde_min = float('inf')
tiempo_verde_max = float('-inf')

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

            # Detectar inicio de una nueva fase
            if fase != fase_actual[tls_id]:
                fase_anterior = fase_actual[tls_id]

                # ✅ Solo fases 0 y 2
                if fase_anterior in [0, 2]:
                    duracion = step - inicio_fase[tls_id]
                    vehiculos_en_fase = 0
                    vehiculos_detectados = set()

                    if tls_id in fases_lanes_dict and fase_anterior in fases_lanes_dict[tls_id]:
                        carriles = list(set(fases_lanes_dict[tls_id][fase_anterior]))
                        for lane_id in carriles:
                            ids = traci.lane.getLastStepVehicleIDs(lane_id)
                            vehiculos_detectados.update(ids)

                        vehiculos_en_fase = len(vehiculos_detectados)

                    historial_fases.append({
                        "tiempo": traci.simulation.getTime() - duracion,
                        "semaforo_id": tls_id,
                        "fase": fase_anterior,
                        "duracion": duracion,
                        "vehiculos_en_carriles": vehiculos_en_fase,
                        "paso_inicio": inicio_fase[tls_id]
                    })

                    # ⏱️ Actualizar tiempos mínimos y máximos
                    tiempo_verde_min = min(tiempo_verde_min, duracion)
                    tiempo_verde_max = max(tiempo_verde_max, duracion)

                # Actualizar fase actual
                fase_actual[tls_id] = fase
                inicio_fase[tls_id] = step

        step += 1

    # Registrar fase final
    for tls_id in semaforos_ids:
        if tls_id in fase_actual:
            fase_anterior = fase_actual[tls_id]

            if fase_anterior in [0, 2]:
                duracion = step - inicio_fase[tls_id]
                vehiculos_en_fase = 0
                if tls_id in fases_lanes_dict and fase_anterior in fases_lanes_dict[tls_id]:
                    carriles = fases_lanes_dict[tls_id][fase_anterior]
                    for lane_id in carriles:
                        vehiculos_en_fase += traci.lane.getLastStepVehicleNumber(lane_id)

                historial_fases.append({
                    "tiempo": traci.simulation.getTime() - duracion,
                    "semaforo_id": tls_id,
                    "fase": fase_anterior,
                    "duracion": duracion,
                    "vehiculos_en_carriles": vehiculos_en_fase,
                    "paso_inicio": inicio_fase[tls_id]
                })
finally:
    traci.close()

# Reporte final
if tiempo_verde_min != float('inf'):
    print(f"\n⏱️ Tiempo mínimo de verde observado: {tiempo_verde_min}s")
    print(f"⏱️ Tiempo máximo de verde observado: {tiempo_verde_max}s")
else:
    print("\n⚠️ No se detectaron fases verdes (0 o 2)")

# Obtener solo las duraciones de fases verdes (0 y 2)
duraciones_verdes = [f["duracion"] for f in historial_fases if f["fase"] in [0, 2]]

if duraciones_verdes:
    media = statistics.mean(duraciones_verdes)
    varianza = statistics.variance(duraciones_verdes) if len(duraciones_verdes) > 1 else 0
    try:
        moda = statistics.mode(duraciones_verdes)
    except statistics.StatisticsError:
        moda = "No única"

    print(f"📊 Media de duración de verde     : {media:.2f}s")
    print(f"📊 Moda de duración de verde      : {moda}")
    print(f"📊 Varianza de duración de verde  : {varianza:.2f}")

    # Guardar en CSV (añadir fila resumen al final)
    csv_file = "datos_semaforos_actuated.csv"
    with open(csv_file, mode='w', newline='') as file:
        fieldnames = ["tiempo", "semaforo_id", "fase", "duracion", "vehiculos_en_carriles", "paso_inicio"]
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        writer.writeheader()
        for entry in historial_fases:
            writer.writerow(entry)
    print(f"\nHistorial guardado en {csv_file}")
else:
    print("⚠️ No se encontraron fases verdes para cálculo estadístico.")

