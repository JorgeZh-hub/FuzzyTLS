import traci
import numpy as np
import skfuzzy as fuzz
from skfuzzy import control as ctrl
import csv
import os
from fuzzy_defs import *
from fuzzy_utils import *
from logs_functions import *


# Archivo CSV para guardar los datos
CSV_PATH = "datos_colas_fuzzy.csv"

# Inicializar archivo con encabezados
with open(CSV_PATH, mode='w', newline='') as f:
    writer = csv.writer(f)
    writer.writerow(['tiempo', 'lane_id', 'vehiculos_en_cola'])

CSV_SEMAFORO = "datos_semaforos_fuzzy.csv"

with open(CSV_SEMAFORO, mode='w', newline='') as f:
    writer = csv.writer(f)
    writer.writerow(['tiempo', 'semaforo_id', 'num_vehiculos', 'fase', 'duracion_verde'])

# Crear las variables con funciones de membresía
fuzzy_vars = generar_membresias_fuzzy(funciones)
llegada = fuzzy_vars["llegada"]
vehiculos = fuzzy_vars["vehiculos"]
verde = fuzzy_vars["verde"]

reglas = crear_reglas_desde_lista(reglas_definidas, vehiculos, llegada, verde)
sistema_ctrl = ctrl.ControlSystem(reglas)

# ========= Funciones Auxiliares =========
def contar_vehiculos(lanes, tiempo_simulacion, registro_all_lanes, csv_path="datos_colas_fuzzy.csv"):
    total = 0
    with open(csv_path, mode='a', newline='') as f:
        writer = csv.writer(f)
        for lane in lanes:
            registro = registro_all_lanes.get(lane)
            if registro:
                cantidad = len(registro["vehiculos_ids"])
                total += cantidad
                writer.writerow([tiempo_simulacion, lane, cantidad])
                #print(f"📌 [{tiempo_simulacion:.2f}s] Lane: {lane} → {cantidad} vehículos")
            #else:
                #print(f"⚠️  Lane {lane} no encontrado en registro_all_lanes.")
    return total

def actualizar_limites_lanes(lanes, registro_all_lanes, limites_globales_lanes):
    for lane_id in lanes:
        if lane_id not in registro_all_lanes or lane_id not in limites_globales_lanes:
            continue

        reg = registro_all_lanes[lane_id]
        lim = limites_globales_lanes[lane_id]

        # Extraer métricas actuales
        num_vehiculos = len(reg["vehiculos_ids"])
        en_movimiento = len(reg["vehiculos_movimiento"])
        detenidos = len(reg["vehiculos_detencion"])
        velocidad = reg["velocidad_promedio"]
        tasa = reg["tasa_llegada"]

        # Actualizar límites
        lim["vehiculos_min"] = min(lim["vehiculos_min"], num_vehiculos)
        lim["vehiculos_max"] = max(lim["vehiculos_max"], num_vehiculos)

        lim["movimiento_min"] = min(lim["movimiento_min"], en_movimiento)
        lim["movimiento_max"] = max(lim["movimiento_max"], en_movimiento)

        lim["detenidos_min"] = min(lim["detenidos_min"], detenidos)
        lim["detenidos_max"] = max(lim["detenidos_max"], detenidos)

        lim["velocidad_prom_min"] = min(lim["velocidad_prom_min"], velocidad)
        lim["velocidad_prom_max"] = max(lim["velocidad_prom_max"], velocidad)

        lim["tasa_llegada_min"] = min(lim["tasa_llegada_min"], tasa)
        lim["tasa_llegada_max"] = max(lim["tasa_llegada_max"], tasa)

def update_parameters_fuzzy(lanes_id_seleccionados, registro_all_lanes):
    simTime = traci.simulation.getTime()

    for lane_id in lanes_id_seleccionados:
        vehiculos = traci.lane.getLastStepVehicleIDs(lane_id)
        vehiculos_set = set(vehiculos)

        vehs_mov = set()
        vehs_det = set()
        velocidades = []

        for veh_id in vehiculos:
            vel = traci.vehicle.getSpeed(veh_id)
            if vel > 0.1:
                vehs_mov.add(veh_id)
                velocidades.append(vel)
            else:
                vehs_det.add(veh_id)

        velocidad_promedio = np.mean(velocidades) if velocidades else 0.0

        registro = registro_all_lanes[lane_id]
        vehiculos_anteriores = registro["vehiculos_ids"]
        tiempo_anterior = registro["tiempo_ultimo"]

        nuevos_vehiculos = vehiculos_set - vehiculos_anteriores
        num_nuevos = len(nuevos_vehiculos)

        if tiempo_anterior is not None:
            delta_t = simTime - tiempo_anterior
            tasa_llegada = num_nuevos / delta_t if delta_t > 0 else 0.0
        else:
            tasa_llegada = 0.0

        # Actualización del registro
        registro_all_lanes[lane_id] = {
            "vehiculos_ids": vehiculos_set,
            "vehiculos_movimiento": vehs_mov,
            "vehiculos_detencion": vehs_det,
            "velocidades": velocidades,
            "velocidad_promedio": velocidad_promedio,
            "nuevos_vehiculos": num_nuevos,
            "tiempo_ultimo": simTime,
            "tasa_llegada": tasa_llegada
        }
"""
        # Log opcional para depuración
        print(f"[{simTime:.2f}s] Lane: {lane_id}")
        print(f"   Vehs totales     : {len(vehiculos)}")
        print(f"   Nuevos detectados: {num_nuevos}")
        print(f"   Vel. promedio    : {velocidad_promedio:.2f} m/s")
        print(f"   En movimiento    : {len(vehs_mov)}")
        print(f"   Detenidos        : {len(vehs_det)}")
        print(f"   Tasa de llegada  : {tasa_llegada:.3f} veh/s\n")
"""

def obtener_promedio_tasa_llegada(lane_ids_seleccionados, registro_all_lanes):
    tasas = []

    for lane_id in lane_ids_seleccionados:
        registro = registro_all_lanes.get(lane_id)
        if registro:
            tasa = registro.get("tasa_llegada", 0.0)
            if tasa > 0:
                tasas.append(tasa)

    if tasas:
        promedio = sum(tasas) / len(tasas)
    else:
        promedio = 0.0

    #print(f"↪ Tasa promedio para {lane_ids_seleccionados} = {promedio:.3f} veh/s")
    return promedio


def calcular_verde(num_vehiculos, tasa_llegada):

    if num_vehiculos <= 3:
        return funciones["verde"]["lmin"]
    
    fuzzy_sim = ctrl.ControlSystemSimulation(sistema_ctrl)

    try:
        fuzzy_sim.input['vehiculos'] = num_vehiculos
        fuzzy_sim.input['llegada'] = tasa_llegada
        fuzzy_sim.compute()
        return int(fuzzy_sim.output['verde'])
    except Exception as e:
        #print(f"[ERROR] Difuso: {e}, usando valor por defecto (30s).")
        return 30

def guardar_datos_semaforo(tiempo, semaforo_id, fase, duracion, num_vehiculos):
    with open(CSV_SEMAFORO, mode='a', newline='') as f:
        writer = csv.writer(f)
        writer.writerow([tiempo, semaforo_id, num_vehiculos, fase, duracion])

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
    
    registro = {}
    for fases in fases_lanes_dict.values():
        for lanes in fases.values():
            for lane_id in lanes:
                if lane_id not in registro:
                    registro[lane_id] = {
                        "vehiculos_ids": set(),
                        "vehiculos_movimiento": set(),
                        "vehiculos_detencion": set(),
                        "velocidades": [],
                        "velocidad_promedio": 0.0,
                        "nuevos_vehiculos": 0,
                        "tiempo_ultimo": None,
                        "tasa_llegada": 0.0
                    }

    return estado, registro


def actualizar_controladores(estado, registro_all_lanes, duracion_amarillo=3):
    for semaforo_id, datos in estado.items():
        fase = datos["fase"]  # fase actual
        # Control de tiempo
        if datos["tiempo_restante"] > 0:
            datos["tiempo_restante"] -= 1
            continue

        if datos["modo"] == "verde":
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

            update_parameters_fuzzy(lanes, registro_all_lanes)
            tasa = obtener_promedio_tasa_llegada(lanes, registro_all_lanes)
            total_vehiculos = contar_vehiculos(lanes, simTime, registro_all_lanes)
            actualizar_limites_lanes(lanes, registro_all_lanes, limites_globales_lanes)

            duracion_verde = calcular_verde(total_vehiculos, tasa)
            #print(f"[{semaforo_id}] Fase {fase} → Vehículos: {total_vehiculos}, Llegada: {tasa:.2f} → Verde: {duracion_verde}s")
            guardar_datos_semaforo(simTime, semaforo_id, nueva_fase, duracion_verde, total_vehiculos)

            traci.trafficlight.setPhase(semaforo_id, nueva_fase)
            datos["modo"] = "verde"
            datos["tiempo_restante"] = duracion_verde
            datos["fase"] = nueva_fase
            datos["tiempo_verde_asignado"] = duracion_verde
            datos["verde_extendido"] = False  # reiniciar para la nueva fase

# ========= MAIN =========
if __name__ == "__main__":
    traci.start([
        "sumo",
        "-c", sumo_cfg
    ])

    estado, registro = inicializar_controladores(semaforos_ids, fases_lanes_dict)

    # Inicializa los límites globales por cada lane
    limites_globales_lanes = {
        lane_id: {
            "vehiculos_min": float('inf'),
            "vehiculos_max": float('-inf'),
            "movimiento_min": float('inf'),
            "movimiento_max": float('-inf'),
            "detenidos_min": float('inf'),
            "detenidos_max": float('-inf'),
            "velocidad_prom_min": float('inf'),
            "velocidad_prom_max": float('-inf'),
            "tasa_llegada_min": float('inf'),
            "tasa_llegada_max": float('-inf')
        }
        for lane_id in registro.keys()
    }

    while traci.simulation.getMinExpectedNumber() > 0:
        actualizar_controladores(estado, registro)
        traci.simulationStep()

    # Mostrar resumen general
    imprimir_limites_globales(limites_globales_lanes)
    imprimir_limites_por_semaforo_y_fase(fases_lanes_dict, limites_globales_lanes)
    traci.close()
