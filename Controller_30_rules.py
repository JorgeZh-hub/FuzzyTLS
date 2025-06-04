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
llegada = ctrl.Antecedent(np.arange(0, 0.61, 0.01), 'llegada')
vehiculos = ctrl.Antecedent(np.arange(0, 8.1, 0.1), 'vehiculos')
verde = ctrl.Consequent(np.arange(15, 21.1, 0.1), 'verde')

# --------- Funciones de membresía ---------
"""
# VEHICULOS
vehiculos['muy pocos'] = fuzz.trapmf(vehiculos.universe, [0, 0, 2, 3])
vehiculos['pocos'] = fuzz.trimf(vehiculos.universe, [2, 4, 5])
vehiculos['normal'] = fuzz.trimf(vehiculos.universe, [4, 6, 8])
vehiculos['moderados'] = fuzz.trimf(vehiculos.universe, [6, 9, 12])
vehiculos['muchos'] = fuzz.trapmf(vehiculos.universe, [10, 13, 15, 15])
"""

# LLEGADA
llegada['muy lenta'] = fuzz.trapmf(llegada.universe, [0.00, 0.00, 0.03, 0.05])
llegada['lenta'] = fuzz.trimf(llegada.universe, [0.03, 0.06, 0.09])
llegada['media'] = fuzz.trimf(llegada.universe, [0.08, 0.12, 0.16])
llegada['moderada'] = fuzz.trimf(llegada.universe, [0.15, 0.20, 0.25])
llegada['alta'] = fuzz.trimf(llegada.universe, [0.23, 0.30, 0.37])
llegada['muy alta'] = fuzz.trapmf(llegada.universe, [0.35, 0.45, 0.60, 0.60])
"""
# Funciones de membresía
verde['muy corto'] = fuzz.trapmf(verde.universe, [15, 15, 17, 20])
verde['corto']     = fuzz.trimf(verde.universe, [18, 21, 24])
verde['normal']    = fuzz.trimf(verde.universe, [22, 26, 30])
verde['alto']      = fuzz.trimf(verde.universe, [28, 32, 36])
verde['muy alto']  = fuzz.trapmf(verde.universe, [34, 37, 39, 39])"""

# --------- Funciones de membresía para VEHICULOS ---------

vehiculos['muy pocos']  = fuzz.trapmf(vehiculos.universe, [0, 0, 1, 2])
vehiculos['pocos']      = fuzz.trimf(vehiculos.universe, [1, 2.5, 4])
vehiculos['normal']     = fuzz.trimf(vehiculos.universe, [3, 4.5, 6])
vehiculos['moderados']  = fuzz.trimf(vehiculos.universe, [4.5, 6.5, 7.5])
vehiculos['muchos']     = fuzz.trapmf(vehiculos.universe, [6.5, 7.5, 8, 8])

# --------- Funciones de membresía para VERDE (tiempo en segundos) ---------

verde['muy corto'] = fuzz.trapmf(verde.universe, [15, 15, 15.5, 16])
verde['corto']     = fuzz.trimf(verde.universe, [15.5, 16.5, 17])
verde['normal']    = fuzz.trimf(verde.universe, [16.5, 17.5, 18.5])
verde['alto']      = fuzz.trimf(verde.universe, [18, 19, 20])
verde['muy alto']  = fuzz.trapmf(verde.universe, [19.5, 20.5, 21, 21])

# ========= Reglas Difusas =========
reglas = [
    ctrl.Rule(vehiculos['muy pocos'] & llegada['muy lenta'], verde['muy corto']),
    ctrl.Rule(vehiculos['muy pocos'] & llegada['lenta'], verde['muy corto']),
    ctrl.Rule(vehiculos['muy pocos'] & llegada['media'], verde['corto']),
    ctrl.Rule(vehiculos['muy pocos'] & llegada['moderada'], verde['corto']),
    ctrl.Rule(vehiculos['muy pocos'] & llegada['alta'], verde['normal']),
    ctrl.Rule(vehiculos['muy pocos'] & llegada['muy alta'], verde['normal']),

    ctrl.Rule(vehiculos['pocos'] & llegada['muy lenta'], verde['muy corto']),
    ctrl.Rule(vehiculos['pocos'] & llegada['lenta'], verde['corto']),
    ctrl.Rule(vehiculos['pocos'] & llegada['media'], verde['corto']),
    ctrl.Rule(vehiculos['pocos'] & llegada['moderada'], verde['normal']),
    ctrl.Rule(vehiculos['pocos'] & llegada['alta'], verde['normal']),
    ctrl.Rule(vehiculos['pocos'] & llegada['muy alta'], verde['alto']),

    ctrl.Rule(vehiculos['normal'] & llegada['muy lenta'], verde['corto']),
    ctrl.Rule(vehiculos['normal'] & llegada['lenta'], verde['corto']),
    ctrl.Rule(vehiculos['normal'] & llegada['media'], verde['normal']),
    ctrl.Rule(vehiculos['normal'] & llegada['moderada'], verde['normal']),
    ctrl.Rule(vehiculos['normal'] & llegada['alta'], verde['alto']),
    ctrl.Rule(vehiculos['normal'] & llegada['muy alta'], verde['alto']),

    ctrl.Rule(vehiculos['moderados'] & llegada['muy lenta'], verde['normal']),
    ctrl.Rule(vehiculos['moderados'] & llegada['lenta'], verde['normal']),
    ctrl.Rule(vehiculos['moderados'] & llegada['media'], verde['alto']),
    ctrl.Rule(vehiculos['moderados'] & llegada['moderada'], verde['alto']),
    ctrl.Rule(vehiculos['moderados'] & llegada['alta'], verde['muy alto']),
    ctrl.Rule(vehiculos['moderados'] & llegada['muy alta'], verde['muy alto']),

    ctrl.Rule(vehiculos['muchos'] & llegada['muy lenta'], verde['alto']),
    ctrl.Rule(vehiculos['muchos'] & llegada['lenta'], verde['alto']),
    ctrl.Rule(vehiculos['muchos'] & llegada['media'], verde['muy alto']),
    ctrl.Rule(vehiculos['muchos'] & llegada['moderada'], verde['muy alto']),
    ctrl.Rule(vehiculos['muchos'] & llegada['alta'], verde['muy alto']),
    ctrl.Rule(vehiculos['muchos'] & llegada['muy alta'], verde['muy alto']),
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
    #print(f"[{simTime:.2f}s] >>> Actualizando tasa de llegada...")  # Inicio de evaluación

    for lane_id in lanes_id:
        vehiculos = traci.lane.getLastStepVehicleIDs(lane_id)
        #print(f"  - Lane: {lane_id}, Vehículos detectados: {vehiculos}")

        # Si hay al menos un vehículo en el carril
        if vehiculos:
            veh_id_actual = vehiculos[0]  # El primero en el carril
            ultimo_veh_id = tasa_llegada[lane_id]["ultimo_vehiculo"]

            # Si es un nuevo vehículo (distinto del anterior)
            if veh_id_actual != ultimo_veh_id:
                #print(f"    > Nuevo vehículo detectado en {lane_id}: {veh_id_actual} (anterior: {ultimo_veh_id})")

                tiempo_actual = simTime

                if tasa_llegada[lane_id]["tiempo_ultimo"] is not None:
                    intervalo = tiempo_actual - tasa_llegada[lane_id]["tiempo_ultimo"]
                    tasa_llegada[lane_id]["intervalos"].append(intervalo)
                    #print(f"    > Intervalo registrado: {intervalo:.2f}s")

                # Actualizamos el estado del sensor virtual
                tasa_llegada[lane_id]["ultimo_vehiculo"] = veh_id_actual
                tasa_llegada[lane_id]["tiempo_ultimo"] = tiempo_actual

        #else:
         #   print(f"    > No hay vehículos en {lane_id}")

    #print()  # Línea en blanco para legibilidad



def calcular_verde(num_vehiculos, tasa_llegada):
    if num_vehiculos <= 2:
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
            "fases_lanes": fases_lanes_dict[semaforo_id],
            "tiempo_verde_asignado": 0,
            "verde_extendido": False

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
        fase = datos["fase"]  # fase actual
        # Control de tiempo
        if datos["tiempo_restante"] > 0:
            datos["tiempo_restante"] -= 1
            continue

        if datos["modo"] == "verde":
            # Evaluar alargar el verde antes de pasar a amarillo
            lanes = datos["fases_lanes"].get(fase, [])
            simTime = traci.simulation.getTime()

            actualizar_tasa_llegada(lanes, tasa_llegada, simTime)
            tasa = obtener_promedio_tasa_llegada(lanes, tasa_llegada)
            total_vehiculos = contar_vehiculos(lanes, simTime)

            nuevo_verde = calcular_verde(total_vehiculos, tasa)
            verde_actual = datos["tiempo_verde_asignado"]
            extension =int(max(0, min(10, (nuevo_verde - 15) * (10 / (25 - 15)))))
            extension = 0


            if extension > 0 and datos["verde_extendido"] == False:
                print(f"EXTENSIÖN:   [{semaforo_id}] Fase {fase} → Vehículos: {total_vehiculos}, Llegada: {tasa:.2f} → Verde: {extension}s")
                #print(f"[{simTime:.2f}s] ↪ Extensión de verde en {semaforo_id}: +{extension}s")
                datos["tiempo_restante"] = extension
                # Solo extendemos una vez, así que guardamos una marca
                datos["verde_extendido"] = True
            else:
                # Si no hay extensión, cambiamos a amarillo
                nueva_fase = fase + 1
                traci.trafficlight.setPhase(semaforo_id, nueva_fase)
                datos["modo"] = "amarillo"
                datos["tiempo_restante"] = duracion_amarillo
                datos["fase"] = nueva_fase

        elif datos["modo"] == "amarillo":
            # Cambiar a la siguiente fase verde y calcular nuevo tiempo
            nueva_fase = (fase + 1) % 4
            lanes = datos["fases_lanes"].get(nueva_fase, [])
            simTime = traci.simulation.getTime()

            actualizar_tasa_llegada(lanes, tasa_llegada, simTime)
            tasa = obtener_promedio_tasa_llegada(lanes, tasa_llegada)
            total_vehiculos = contar_vehiculos(lanes, simTime)

            duracion_verde = calcular_verde(total_vehiculos, tasa)
            print(f"[{semaforo_id}] Fase {fase} → Vehículos: {total_vehiculos}, Llegada: {tasa:.2f} → Verde: {duracion_verde}s")
            guardar_datos_semaforo(semaforo_id, nueva_fase, duracion_verde, total_vehiculos)

            traci.trafficlight.setPhase(semaforo_id, nueva_fase)
            datos["modo"] = "verde"
            datos["tiempo_restante"] = duracion_verde
            datos["fase"] = nueva_fase
            datos["tiempo_verde_asignado"] = duracion_verde
            datos["verde_extendido"] = False  # reiniciar para la nueva fase


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
