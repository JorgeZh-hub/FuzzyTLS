# Lista de rutas (origen, destino)
routes = [
    ("40668087#1", "542428845#0", 0.3),
    ("40668087#1", "337277957#0", 1),
    ("40668087#1", "1053072563", 0.3),
    ("40668087#1", "337277973#1", 1),
    ("40668087#1", "337277984#0", 1),
    ("40668087#1", "337277970#1", 1),
    ("40668087#1", "337277951#1", 1),
    ("49217102", "337277951#3", 1),
    ("49217102", "1053072563", 1),
    ("49217102", "337277973#1", 1),
    ("49217102", "337277984#0", 1),
    ("49217102", "542428845#0", 1),
    ("42143912#5", "337277957#0", 1),
    ("42143912#5", "542428845#0", 1),
    ("42143912#5", "1053072563", 1),
    ("42143912#5", "337277973#1", 1),
    ("567060342#0", "337277984#0", 1),
    ("567060342#0", "542428845#0", 1),
    ("567060342#0", "337277957#0", 1),
]


routes_straight = [
    ("40668087#1", "337277957#0", 1),   # Horizontal
    ("567060342#0", "337277984#0", 1),   # Horizontal
    ("49217102", "1053072563", 1),
    ("42143912#5", "542428845#0", 1),
]

#routes = [
#    ("567060342#0", "337277973#1", 1 ),
#    ("337277951#1", "1053072563", 1)
#]

# Intervalos horarios (hora en segundos desde 00:00) 
hourly_intervals = [
    (0, 18000, 2000//2),  #(Hora inicio, hora fin, veh que se distribuye entre todas las rutas)
    (18000, 28000, 3000//2),
    (28000, 38000, 2500//2),
    #(10200, 20400, 1500),
    #(20400, 30600 , 3000),
]

routes = routes

# Generar todas las entradas y ordenarlas por tiempo
all_flows = []
flow_id = 1
for begin, end, vph in hourly_intervals:
    for route_from, route_to, density in routes:
        all_flows.append({
            "id": f"f{flow_id}",
            "from": route_from,
            "to": route_to,
            "begin": begin,
            "end": end,
            "vph": int((vph // len(routes))*density)
        })
        flow_id += 1

# Ordenar flujos por tiempo de inicio
all_flows.sort(key=lambda x: x["begin"])

# Escribir archivo XML
output_lines = ['<?xml version="1.0" encoding="UTF-8"?>', '<routes>']
output_lines.append('    <vType id="car" accel="1.0" decel="4.5" sigma="0.5" length="5" maxSpeed="25"/>')

for flow in all_flows:
    output_lines.append(
        f'    <flow id="{flow["id"]}" from="{flow["from"]}" to="{flow["to"]}" type="car" begin="{flow["begin"]}" end="{flow["end"]}" vehsPerHour="{flow["vph"]}"/>'
    )

output_lines.append('</routes>')

# Guardar archivo
with open("./sumo_files/generated_routes_hourly.rou.xml", "w") as f:
    f.write("\n".join(output_lines))
