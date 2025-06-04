import traci
import numpy as np
import skfuzzy as fuzz
from skfuzzy import control as ctrl
import csv
import os

# Archivo CSV para guardar los datos
CSV_PATH = "datos_colas_fuzzy.csv"

# Inicializar archivo con encabezados
with open(CSV_PATH, mode='w', newline='') as f:
    writer = csv.writer(f)
    writer.writerow(['tiempo', 'lane_id', 'vehiculos_en_cola'])

CSV_SEMAFORO = "datos_semaforos.csv"

with open(CSV_SEMAFORO, mode='w', newline='') as f:
    writer = csv.writer(f)
    writer.writerow(['semaforo_id', 'num_vehiculos', 'fase', 'duracion_verde'])

# ========= Definición de Universos =========
vehiculos = ctrl.Antecedent(np.arange(0, 26, 1), 'vehiculos')
llegada = ctrl.Antecedent(np.arange(0, 0.5, 0.01), 'llegada')
verde = ctrl.Consequent(np.arange(15, 51, 1), 'verde')

# ========= Funciones de membresía =========
vehiculos['pocos'] = fuzz.trapmf(vehiculos.universe, [0, 0, 5, 8])
vehiculos['moderados'] = fuzz.trimf(vehiculos.universe, [7, 10, 14])
vehiculos['muchos'] = fuzz.trapmf(vehiculos.universe, [10, 18, 25, 25])

llegada['lenta'] = fuzz.trapmf(llegada.universe, [0, 0, 0.05, 0.1])
llegada['moderada'] = fuzz.trimf(llegada.universe, [0.05, 0.1, 0.15])
llegada['rápida'] = fuzz.trapmf(llegada.universe, [0.1, 0.2, 0.3, 0.5])

verde['corta'] = fuzz.trapmf(verde.universe, [15, 15, 20, 25])
verde['media'] = fuzz.trimf(verde.universe, [20, 30, 40])
verde['larga'] = fuzz.trapmf(verde.universe, [30, 43, 50, 50])

# ========= Reglas Difusas =========
reglas = [
    ctrl.Rule(vehiculos['pocos'] & llegada['lenta'], verde['corta']),
    ctrl.Rule(vehiculos['pocos'] & llegada['moderada'], verde['media']),
    ctrl.Rule(vehiculos['pocos'] & llegada['rápida'], verde['media']),
    ctrl.Rule(vehiculos['moderados'] & llegada['lenta'], verde['media']),
    ctrl.Rule(vehiculos['moderados'] & llegada['moderada'], verde['media']),
    ctrl.Rule(vehiculos['moderados'] & llegada['rápida'], verde['larga']),
    ctrl.Rule(vehiculos['muchos'] & llegada['lenta'], verde['media']),
    ctrl.Rule(vehiculos['muchos'] & llegada['moderada'], verde['larga']),
    ctrl.Rule(vehiculos['muchos'] & llegada['rápida'], verde['larga']),
]

sistema_ctrl = ctrl.ControlSystem(reglas)

# ========= Funciones Auxiliares =========
def contar_vehiculos(lanes, tiempo_simulacion):
    total = 0
    with open(CSV_PATH, mode='a', newline='') as f:
        writer = csv.writer(f)
        for lane in lanes:
            cantidad = traci.lane.getLastStepVehicleNumber(lane)
            total += cantidad
            writer.writerow([tiempo_simulacion, lane, cantidad])
    return total

def tasa_llegada(lanes, historial, ventana_segundos=60):
    tiempo_actual = traci.simulation.getTime()
    tiempo_inicio = tiempo_actual - ventana_segundos

    total_vehiculos = 0

    for lane_id in lanes:
        # Obtener los vehículos actuales en el carril
        vehiculos_actuales = traci.lane.getLastStepVehicleIDs(lane_id)

        if lane_id not in historial:
            historial[lane_id] = []

        # Registrar los nuevos vehículos que aún no estaban en el historial
        for veh_id in vehiculos_actuales:
            if veh_id not in [veh[0] for veh in historial[lane_id]]:
                historial[lane_id].append((veh_id, tiempo_actual))

        # Filtrar vehículos que llegaron en la ventana de tiempo
        historial[lane_id] = [
            (veh_id, t) for veh_id, t in historial[lane_id] if t >= tiempo_inicio
        ]
        total_vehiculos += len(historial[lane_id])

    # Convertimos la tasa a vehículos por hora
    tasa = (total_vehiculos / ventana_segundos) * 3600
    return tasa

def actualizar_tasa_llegada(lanes_id, tasa_llegada, simTime):
    print(f"[{simTime:.2f}s] >>> Actualizando tasa de llegada...")  # Inicio de evaluación

    for lane_id in lanes_id:
        vehiculos = traci.lane.getLastStepVehicleIDs(lane_id)
        print(f"  - Lane: {lane_id}, Vehículos detectados: {vehiculos}")

        # Si hay al menos un vehículo en el carril
        if vehiculos:
            veh_id_actual = vehiculos[0]  # El primero en el carril
            ultimo_veh_id = tasa_llegada[lane_id]["ultimo_vehiculo"]

            # Si es un nuevo vehículo (distinto del anterior)
            if veh_id_actual != ultimo_veh_id:
                print(f"    > Nuevo vehículo detectado en {lane_id}: {veh_id_actual} (anterior: {ultimo_veh_id})")

                tiempo_actual = simTime

                if tasa_llegada[lane_id]["tiempo_ultimo"] is not None:
                    intervalo = tiempo_actual - tasa_llegada[lane_id]["tiempo_ultimo"]
                    tasa_llegada[lane_id]["intervalos"].append(intervalo)
                    print(f"    > Intervalo registrado: {intervalo:.2f}s")

                # Actualizamos el estado del sensor virtual
                tasa_llegada[lane_id]["ultimo_vehiculo"] = veh_id_actual
                tasa_llegada[lane_id]["tiempo_ultimo"] = tiempo_actual

        else:
            print(f"    > No hay vehículos en {lane_id}")

    print()  # Línea en blanco para legibilidad



def calcular_verde(num_vehiculos, tasa_llegada):
    if num_vehiculos == 0:
        return 15
    
    fuzzy_sim = ctrl.ControlSystemSimulation(sistema_ctrl)
    num_vehiculos = np.clip(num_vehiculos, 0, 25)
    #tasa_llegada = np.clip(tasa_llegada, 0, 1)

    try:
        fuzzy_sim.input['vehiculos'] = num_vehiculos
        fuzzy_sim.input['llegada'] = tasa_llegada
        fuzzy_sim.compute()
        return int(fuzzy_sim.output['verde'])
    except Exception as e:
        print(f"[ERROR] Difuso: {e}, usando valor por defecto (30s).")
        return 30

def guardar_datos_semaforo(semaforo_id, fase, duracion, num_vehiculos):
    with open(CSV_SEMAFORO, mode='a', newline='') as f:
        writer = csv.writer(f)
        writer.writerow([semaforo_id, num_vehiculos, fase, duracion])

# ========= Controlador Múltiple =========
def inicializar_controladores(semaforos_ids, fases_lanes_dict):
    estado = {}
    for semaforo_id in semaforos_ids:
        estado[semaforo_id] = {
            "modo": "verde",  # verde o amarillo
            "fase": 0,  # fase actual (0 o 2)
            "tiempo_restante": 0,
            "historial": {},
            "fases_lanes": fases_lanes_dict[semaforo_id]
        }
        traci.trafficlight.setPhase(semaforo_id, 1)
    
    # Extraer todos los lane_ids únicos desde fases_lanes_dict
    todos_los_lanes = set()

    for semaforo_id, fases in fases_lanes_dict.items():
        for fase_lanes in fases.values():
            todos_los_lanes.update(fase_lanes)

    # Inicializar el diccionario tasa_llegada
    tasa_llegada = {
        lane_id: {
            "ultimo_vehiculo": None,
            "tiempo_ultimo": None,
            "intervalos": []
        } for lane_id in todos_los_lanes
    }

    return estado, tasa_llegada

def obtener_promedio_tasa_llegada(lane_ids, tasa_llegada):
    intervalos = []

    for lane_id in lane_ids:
        datos = tasa_llegada.get(lane_id)
        if datos and datos["intervalos"]:
            intervalos.extend(datos["intervalos"])

    if intervalos:
        promedio_intervalo = sum(intervalos) / len(intervalos)
        tasa_promedio = 1 / promedio_intervalo  # veh/s
        return tasa_promedio
    else:
        return 0.0  # No hay datos suficientes


def actualizar_controladores(estado, tasa_llegada, duracion_amarillo=3):
    for semaforo_id, datos in estado.items():
        fase = datos["fase"]  # Usamos la fase *guardada*, no la de TraCI
        # Control de tiempo
        if datos["tiempo_restante"] > 0:
            datos["tiempo_restante"] -= 1
            continue

        if datos["modo"] == "verde":
            # Cambiar a amarillo
            nueva_fase = fase + 1  # 0->1, 2->3
            traci.trafficlight.setPhase(semaforo_id, nueva_fase)
            datos["modo"] = "amarillo"
            datos["tiempo_restante"] = duracion_amarillo
            datos["fase"] = nueva_fase
            #print(f"→ {semaforo_id} Cambiando a AMARILLO: Fase {nueva_fase}")

        elif datos["modo"] == "amarillo":
            # Cambiar a siguiente verde calculado
            nueva_fase = (fase + 1) % 4  # 1->2, 3->0
            lanes = datos["fases_lanes"].get(nueva_fase, [])
            tiempo_actual = traci.simulation.getTime()
            total_vehiculos = contar_vehiculos(lanes, tiempo_actual)
            #tasa = tasa_llegada(lanes, datos["historial"])
            simTime = traci.simulation.getTime()
            actualizar_tasa_llegada(lanes, tasa_llegada, simTime)

            tasa = obtener_promedio_tasa_llegada(lanes, tasa_llegada)

            duracion_verde = calcular_verde(total_vehiculos, tasa)
            guardar_datos_semaforo(semaforo_id, nueva_fase, duracion_verde, total_vehiculos)

            traci.trafficlight.setPhase(semaforo_id, nueva_fase)
            datos["modo"] = "verde"
            datos["tiempo_restante"] = duracion_verde
            datos["fase"] = nueva_fase
            print(f"[{semaforo_id}] Fase {fase} → Vehículos: {total_vehiculos}, Llegada: {tasa:.2f} → Verde: {duracion_verde}s")


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
        actualizar_controladores(estado, tasa_llegada)
        traci.simulationStep()

    traci.close()
