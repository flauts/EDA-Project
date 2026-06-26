# Evaluacion Experimental de BSTs Autoajustables bajo Secuencias No Estacionarias

Framework de evaluacion para comparar el comportamiento dinamico de Splay Trees, Tango Trees y Multi-Splay Trees frente a secuencias de acceso cambiantes. El proyecto mide no solo la complejidad asintotica, sino la **capacidad real de adaptacion** de cada arbol cuando el patron de acceso cambia en el tiempo.

## Objetivo

Los arboles autoajustables (Splay, Tango, Multi-Splay) tienen complejidad asintotica competitiva, pero su rendimiento real depende de como se adaptan a **cambios en el patron de acceso**. Este proyecto evalua:

- **Costo de adaptacion:** penalidad cuando el patron cambia de una fase a otra
- **Memoria estructural:** si el arbol recuerda la estructura previa al volver a un patron visto antes
- **Competitividad real:** que tan cerca opera cada arbol de la cota teorica optima (IB-1)

## Estructuras Evaluadas

| Arbol | Tipo | Complejidad | Descripcion |
|-------|------|-------------|-------------|
| **Splay Tree** | Autoajustable | O(log n) amortizado | Clasico de Sleator y Tarjan. Reorganiza el arbol en cada acceso via operaciones de rotacion (zig, zig-zig, zig-zag). |
| **Tango Tree** | Competitivo | O(log log n)-competitivo vs IB-1 | Implementa el algoritmo de Demaine et al. Usa arboles rojo-negro auxiliares por camino preferido. |
| **Multi-Splay Tree** | Competitivo | O(log log n)-competitivo vs IB-1 | Variante de Busa et al. Usa arboles splay auxiliares con direccion de switch (izquierda-derecha). |
| **Red-Black Tree** | Estatico | O(log n) por operacion | Baseline sin reorganizacion por acceso. Solo rotaciones durante insercion. |

## Patron de Acceso: Propiedades S, W, F, R

Cada traza de acceso se define por una secuencia de **fases**, donde cada fase tiene una propiedad de patron:

| Codigo | Propiedad | Descripcion |
|--------|-----------|-------------|
| **S** | Secuencial | Claves accedidas en orden: 1, 2, ..., n, 1, 2, ..., n |
| **W** | Working Set | k claves aleatorias seleccionadas y accedidas repetidamente (localidad temporal) |
| **F** | Finger / Localidad Espacial | Caminata aleatoria dentro de radio k de la posicion actual (85% local) |
| **R** | Random | Uniforme aleatorio sobre todas las n claves (sin localidad) |

Los arboles autoajustables aprovechan las propiedades S, W y F para reorganizarse. La propiedad R no ofrece ventaja estructural.

## Metricas

| Metrica | Descripcion |
|---------|-------------|
| **ops_total** | Total de operaciones (travesias de puntero + rotaciones) en toda la traza |
| **Cota IB-1** | Lower bound teorico de Wilber. Numero minimo de cambios de direccion que cualquier BST debe hacer |
| **Ratio ops/IB-1** | `ops_total / interleave_bound`. Que tan cerca del optimo opera cada arbol. Un valor cercano a 1.0 indica operacion casi optima |
| **Costo de Adaptacion** | Diferencia entre el costo promedio por acceso en la fase 2 (patron nuevo) y el baseline estatico para ese mismo patron |
| **Costo de Recuperacion** | Diferencia entre el costo en la fase 3 (retorno al patron original) y la fase 1. Valores bajos indican que el arbol recuerdo su estructura previa |

## Tres Pistas Experimentales

### 1. State Transitions (Core)

**Objetivo:** Medir como los BSTs se adaptan a cambios de patron de acceso.

- **Traces:** 8 pares simples (S->W, S->F, W->S, etc.) para latency de adaptacion + 6 triples de retorno (A->B->A) para memoria estructural + 1 cadena (S->W->F)
- **Tamano:** n = 1023, 8191, 32767 conWorking Set k = 8, 64
- **Generador:** `python tools/generate_traces.py --suite full --out data/traces`
- **Datos:** `data/traces/state_transitions/`
- **Resultados:** `data/results/state_transitions/`
- **Analisis:** `python tools/analyze.py --results data/results --out data/analysis --traces data/traces`

### 2. Paper Replication (Minimal)

**Objetivo:** Validar que nuestras implementaciones coinciden con el paper de referencia (Al-Adhami & Chheda, arXiv:2405.18825).

- **Traces:** sequential sweeps, uniform random, static working set, paper working set (multi-pass)
- **Generador:** `python tools/generate_paper_traces.py`
- **Datos:** `data/traces/paper_replication/`
- **Resultados:** `data/results/paper_replication/`
- **Graficos:** `python tools/plot_paper_comparisons.py`

### 3. Real-World Workloads

**Objetivo:** Validar la adaptacion de BSTs con trazas reales no estacionarias que tienen cambios de fase naturales.

- **Dataset:** HTTP logs del Kennedy Space Center de la NASA (Julio-Agosto 1995, ~3.4M accesos)
- **Fases naturales:** patrones diurnos, lanzamiento de transbordador (STS-70), shutdown por huracan Erin
- **Generador:** `python tools/convert_nasa_logs.py --log-dir <dir> --out-dir data/traces`
- **Datos:** `data/traces/real_world/`
- **Resultados:** `data/results/nasa_http_jul95/`, `data/results/nasa_http_aug95/`
- **Analisis:** `python tools/analyze_real_world.py --results data/results --out data/analysis`
- **Descarga:**
  - `ftp://ita.ee.lbl.gov/traces/NASA_access_log_Jul95.gz`
  - `ftp://ita.ee.lbl.gov/traces/NASA_access_log_Aug95.gz`

## Estructura del Proyecto

```
EDA-Project/
├── src/
│   ├── benchmark.cpp           # Driver del benchmark
│   ├── trees_test.cpp          # Suite de tests de correctitud
│   └── trees/
│       ├── bst.hpp             # Template base de BST
│       ├── splaycount.hpp      # Splay Tree con contador de ops
│       ├── tangocount.hpp      # Tango Tree con contador de ops
│       ├── multisplaycount.hpp # Multi-Splay Tree con contador de ops
│       └── rbtreecount.hpp     # Red-Black Tree (baseline)
│
├── tools/
│   ├── generate_traces.py      # Generador de trazas (state transitions + paper)
│   ├── generate_paper_traces.py # Generador para replicacion del paper
│   ├── convert_nasa_logs.py    # Conversor de logs NASA HTTP
│   ├── analyze.py              # Analisis y graficos de state transitions
│   ├── analyze_real_world.py   # Analisis de workloads reales
│   └── plot_paper_comparisons.py # Graficos de replicacion del paper
│
├── tests/
│   └── test_generate_traces.py # Tests unitarios del generador
│
├── data/
│   ├── traces/                 # Trazas de entrada
│   │   ├── state_transitions/
│   │   ├── paper_replication/
│   │   └── real_world/
│   ├── results/                # Resultados del benchmark (CSVs)
│   │   ├── results_manifest.jsonl
│   │   ├── state_transitions/
│   │   ├── paper_replication/
│   │   ├── nasa_http_jul95/
│   │   └── nasa_http_aug95/
│   └── analysis/               # Graficos y resumen
│       ├── summary.csv
│       └── plots/
│
├── CMakeLists.txt
└── README.md
```

## Herramientas

| Herramienta | Descripcion |
|------------|-------------|
| `generate_traces.py` | Genera trazas reproducibles con patrones S/W/F/R. Soporta `--suite quick` (validacion) y `--suite full` (experimento formal) |
| `generate_paper_traces.py` | Genera trazas para replicar los resultados del paper de referencia |
| `convert_nasa_logs.py` | Convierte logs HTTP del NASA (formato CLF) a trazas enteras con hashing de URLs |
| `analyze.py` | Lee los resultados del benchmark y genera graficos de adaptacion, recovery, y heatmaps |
| `analyze_real_world.py` | Genera graficos especializados para trazas reales (curvas de costo, comparacion de ops) |
| `plot_paper_comparisons.py` | Genera figuras de nivel publicacion para la replicacion del paper |

## Salida del Benchmark

### CSV por acceso

Cada traza genera un CSV con formato:

| Columna | Tipo | Descripcion |
|---------|------|-------------|
| `access_index` | int | Indice 0-based del acceso en la traza |
| `key` | int | Clave 1-based accedida |
| `phase_id` | int | Indice de la fase actual |
| `phase_name` | string | Nombre de la fase (ej. `phase0_S`, `phase1_W`) |
| `ops` | int | Operaciones realizadas para este acceso |
| `cum_ops` | int | Operaciones acumuladas desde el inicio |

### results_manifest.jsonl

Archivo maestro con un JSON por linea por cada (traza, arbol):

```json
{"trace_id":"transition_S_to_W_n1023_seed2026_k64_pl5115",
 "family":"transition_S_to_W",
 "n":1023, "m":51150,
 "tree":"splay",
 "csv_path":"state_transitions/transition_S_to_W_n1023_seed2026_k64_pl5115/splay.csv",
 "ops_total":87654,
 "interleave_bound":3456,
 "ratio_ops_ib1":2.53,
 "avg_ops_per_access":1.71}
```

## Requisitos

- **C++20** + **CMake** (estructuras y benchmark)
- **Python 3.10+** con `pandas`, `matplotlib`, `numpy`, `scipy`, `tqdm`

## Pipeline Completo

```powershell
# 1. Generar trazas (quick para validacion, full para experimento formal)
python tools/generate_traces.py --suite full --out data/traces --seed 2026

# 2. Compilar
cmake -B build
cmake --build build

# 3. Validar correctitud
.\build\trees_test.exe

# 4. Benchmark
.\build\benchmark.exe --traces data/traces --out data/results --trees splay,tango,multisplay

# 5. Analisis
python tools/analyze.py --results data/results --out data/analysis --traces data/traces
```

Para el experimento formal con n grande, usa `--suite full` en el paso 1.

### Paper Replication

```powershell
python tools/generate_paper_traces.py
python tools/plot_paper_comparisons.py
```

### Real-World Workloads (NASA HTTP Logs)

```powershell
# 1. Descargar logs manualmente
#    ftp://ita.ee.lbl.gov/traces/NASA_access_log_Jul95.gz
#    ftp://ita.ee.lbl.gov/traces/NASA_access_log_Aug95.gz

# 2. Convertir y generar trazas
python tools/convert_nasa_logs.py --log-dir <directorio_descarga> --out-dir data/traces

# 3. Benchmark
.\build\benchmark.exe --traces data/traces/real_world --out data/results --trees splay,tango,multisplay

# 4. Analisis
python tools/analyze_real_world.py --results data/results --out data/analysis
```

## Referencias

- **Paper de referencia:** Al-Adhami & Chheda, "Theoretical insights and an experimental comparison of tango trees and multi-splay trees," arXiv:2405.18825, 2024
- **Implementacion de arboles:** vendoreados de [`adhami3310/tango`](https://github.com/adhami3310/tango) (MIT)
- **Dataset NASA:** Kennedy Space Center HTTP logs, July-August 1995 (ftp://ita.ee.lbl.gov/traces/)
