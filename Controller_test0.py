import traci
import numpy as np
import skfuzzy as fuzz
from skfuzzy import control as ctrl
from collections import defaultdict

import numpy as np
import skfuzzy as fuzz
from skfuzzy import control as ctrl
import traci
from collections import defaultdict

# === Sistema difuso para duración inicial del verde ===
vehiculos = ctrl.Antecedent(np.arange(0, 26, 1), 'vehiculos')
llegada = ctrl.Antecedent(np.arange(0, 1.1, 0.1), 'llegada')
duracion = ctrl.Consequent(np.arange(10, 61, 1), 'duracion')

vehiculos.automf(names=['pocos', 'moderados', 'muchos'])
llegada.automf(names=['lenta', 'moderada', 'rápida'])

duracion['corta'] = fuzz.trimf(duracion.universe, [10, 10, 25])
duracion['media'] = fuzz.trimf(duracion.universe, [20, 35, 50])
duracion['larga'] = fuzz.trimf(duracion.universe, [40, 60, 60])

reglas = [
    ctrl.Rule(vehiculos['muchos'] & llegada['rápida'], duracion['larga']),
    ctrl.Rule(vehiculos['moderados'] & llegada['moderada'], duracion['media']),
    ctrl.Rule(vehiculos['pocos'] & llegada['lenta'], duracion['corta']),
]

sistema_ctrl = ctrl.ControlSystem(reglas)

# === Sistema difuso para alargamiento durante el verde ===
alargamiento = ctrl.Consequent(np.arange(0, 6, 1), 'alargamiento')

alargamiento['nulo'] = fuzz.trimf(alargamiento.universe, [0, 0, 1])
alargamiento['leve'] = fuzz.trimf(alargamiento.universe, [0, 2, 4])
alargamiento['fuerte'] = fuzz.trimf(alargamiento.universe, [3, 5, 5])

reglas_alargamiento = [
    ctrl.Rule(vehiculos['muchos'] & llegada['rápida'], alargamiento['fuerte']),
    ctrl.Rule(vehiculos['moderados'] & llegada['moderada'], alargamiento['leve']),
    ctrl.Rule(vehiculos['pocos'] & llegada['lenta'], alargamiento['nulo']),
]

sistema_alargamiento_ctrl = ctrl.ControlSystem(reglas_alargamiento)

# === Variables y funciones auxiliares ===
estado_semaforos = {}
tasa_llegada = defaultdict(lambda: {'vehiculos': 0, 'tiempo': 0})

def contar_vehiculos(lanes):
    total = 0
    for lane in lanes:
        total += len(traci.lane.getLastStepVehicleIDs(lane))
    return total

def actualizar_tasa_llegada(lanes, simTime):
    for lane in lanes:
        vehiculos = traci.lane.getLastStepVehicleIDs(lane)
        if vehiculos:
            tasa_llegada[lane]['vehiculos'] += len(vehiculos)
            tasa_llegada[lane]['tiempo'] += 1

def obtener_promedio_tasa_llegada(lanes):
    tasas = []
    for lane in lanes:
        datos = tasa_llegada[lane]
        if datos['tiempo'] > 0:
            tasas.append(datos['vehiculos'] / datos['tiempo'])
        tasa_llegada[lane] = {'vehiculos': 0, 'tiempo': 0}
    return np.mean(tasas) if tasas else 0

# === Controlador principal ===
def actualizar_controladores(semaforos):
    for semaforo_id, datos in estado_semaforos.items():
        fase = datos["fase"]
        if datos["modo"] == "verde":
            if datos["tiempo_restante"] > 0:
                datos["tiempo_restante"] -= 1

                # Evaluar alargamiento si sigue en verde y no ha alcanzado el máximo
                if datos.get("alargado_total", 0) < 20:
                    lanes = datos["fases_lanes"].get(fase, [])
                    simTime = traci.simulation.getTime()
                    actualizar_tasa_llegada(lanes, simTime)
                    tasa = obtener_promedio_tasa_llegada(lanes)
                    total_vehiculos = contar_vehiculos(lanes)

                    fuzzy_alargue = ctrl.ControlSystemSimulation(sistema_alargamiento_ctrl)
                    fuzzy_alargue.input['vehiculos'] = np.clip(total_vehiculos, 0, 25)
                    fuzzy_alargue.input['llegada'] = np.clip(tasa, 0, 1)
                    fuzzy_alargue.compute()
                    incremento = int(fuzzy_alargue.output['alargamiento'])

                    restante = 20 - datos.get("alargado_total", 0)
                    incremento = min(incremento, restante)

                    if incremento > 0:
                        datos["tiempo_restante"] += incremento
                        datos["alargado_total"] += incremento
                        print(f"🔁 {semaforo_id} Fase {fase} alargada +{incremento}s (Total: {datos['alargado_total']}s)")

                continue  # Sigue en verde

        # Cambiar de fase
        siguiente_fase = (fase + 1) % len(semaforos[semaforo_id])
        nueva_fase = siguiente_fase
        lanes = datos["fases_lanes"].get(nueva_fase, [])
        simTime = traci.simulation.getTime()
        actualizar_tasa_llegada(lanes, simTime)
        tasa = obtener_promedio_tasa_llegada(lanes)
        total_vehiculos = contar_vehiculos(lanes)

        fuzzy = ctrl.ControlSystemSimulation(sistema_ctrl)
        fuzzy.input['vehiculos'] = np.clip(total_vehiculos, 0, 25)
        fuzzy.input['llegada'] = np.clip(tasa, 0, 1)
        fuzzy.compute()
        duracion_verde = int(fuzzy.output['duracion'])

        # Actualizar estado
        traci.trafficlight.setPhase(semaforo_id, nueva_fase)
        datos.update({
            "modo": "verde",
            "fase": nueva_fase,
            "tiempo_restante": duracion_verde,
            "alargado_total": 0
        })
        print(f"🔄 {semaforo_id} nueva fase {nueva_fase} → {duracion_verde}s")

# === Inicialización del sistema ===
def inicializar_semaforos(semaforos):
    for semaforo_id in semaforos:
        estado_semaforos[semaforo_id] = {
            "fase": 0,
            "modo": "verde",
            "tiempo_restante": 10,
            "fases_lanes": {},  # A llenar externamente
            "alargado_total": 0
        }

def inicializar_controladores(semaforos_ids, fases_lanes_dict):
    estado = {}
    for semaforo_id in semaforos_ids:
        estado[semaforo_id] = {
            "modo": "verde",
            "fase": 0,
            "tiempo_restante": 0,
            "historial": {},
            "fases_lanes": fases_lanes_dict[semaforo_id]
        }
        traci.trafficlight.setPhase(semaforo_id, 1)

    todos_los_lanes = set()
    for fases in fases_lanes_dict.values():
        for lanes in fases.values():
            todos_los_lanes.update(lanes)

    tasa_llegada = {
        lane_id: {
            "vehiculos": 0,
            "tiempo": 0
        } for lane_id in todos_los_lanes
    }

    return estado, tasa_llegada

# ========= MAIN =========
if __name__ == "__main__":
    sumo_cfg = "./sumo_files/osm_fuzzy.sumocfg"

    semaforos_ids = ["2496228891", 
                     "cluster_12013799525_12013799526_2496228894", 
                     "cluster_12013799527_12013799528_2190601967",
                     "cluster_12013799529_12013799530_473195061"]

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

    traci.start([
        "sumo",
        "-c", sumo_cfg
    ])

    estado, tasa_llegada = inicializar_controladores(semaforos_ids, fases_lanes_dict)

    while traci.simulation.getMinExpectedNumber() > 0:
        actualizar_controladores(estado)
        traci.simulationStep()

    traci.close()
