# Evaluacion Experimental de BSTs Autoajustables bajo Secuencias No Estacionarias

Framework de evaluacion para comparar el comportamiento dinamico de Splay Trees, Tango Trees y Multi-Splay Trees frente a secuencias de acceso cambiantes. El proyecto mide no solo la complejidad asintotica, sino la **capacidad real de adaptacion** de cada arbol cuando el patron de acceso cambia en el tiempo.

## Objetivo

Los arboles autoajustables (Splay, Tango, Multi-Splay) tienen complejidad asintotica competitiva, pero su rendimiento real depende de como se adaptan a **cambios en el patron de acceso**. Este proyecto evalua:

- **Costo de adaptacion:** penalidad cuando el patron cambia de una fase a otra
- **Memoria estructural:** si el arbol recuerda la estructura previa al volver a un patron visto antes
- **Rendimiento comparativo:** costo amortizado por acceso y costo total de operaciones

## Estructuras Evaluadas

| Arbol | Tipo | Complejidad | Descripcion |
|-------|------|-------------|-------------|
| **Splay Tree** | Autoajustable | O(log n) amortizado | Clasico de Sleator y Tarjan. Reorganiza el arbol en cada acceso via operaciones de rotacion (zig, zig-zig, zig-zag). |
| **Tango Tree** | Competitivo | O(log log n)-competitivo | Implementa el algoritmo de Demaine et al. Usa arboles rojo-negro auxiliares por camino preferido. |
| **Multi-Splay Tree** | Competitivo | O(log log n)-competitivo | Variante de Busa et al. Usa arboles splay auxiliares con direccion de switch (izquierda-derecha). |
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
| **avg_ops_per_access** | Costo amortizado por acceso. Promedio de operaciones elementales por busqueda |
| **Costo de Adaptacion** | Diferencia entre el costo promedio por acceso en la fase 2 (patron nuevo) y el baseline estatico para ese mismo patron |
| **Costo de Recuperacion** | Diferencia entre el costo en la fase 3 (retorno al patron original) y la fase 1. Valores bajos indican que el arbol recuerda su estructura previa |

## Tres Pistas Experimentales

### 1. State Transitions (Core)

**Objetivo:** Medir como los BSTs se adaptan a cambios de patron de acceso.

- **Traces:** 8 pares simples (S->W, S->F, W->S, etc.) para latencia de adaptacion + 6 triples de retorno (A->B->A) para memoria estructural + 6 triples de cadena (A->B->C, las 6 permutaciones de {S, W, F})
- **Tamano:** n = 1023, 8191, 32767 con Working Set k = 8, 64
- **Generador:** `python tools/generate_traces.py --suite full --out data/traces/state_transitions --seed 2026`
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
- **Resultados:** `data/results/real_world/nasa_http_jul95/`, `data/results/real_world/nasa_http_aug95/`
- **Analisis:** `python tools/analyze_real_world.py --results data/results --out data/analysis`
- **Descarga:**
  - `ftp://ita.ee.lbl.gov/traces/NASA_access_log_Jul95.gz`
  - `ftp://ita.ee.lbl.gov/traces/NASA_access_log_Aug95.gz`

<!-- ## Optimizaciones de Alto Rendimiento (Multicore & I/O)

El framework ha sido diseñado para ejecutar simulaciones masivas en paralelo aprovechando al máximo la arquitectura multicore del sistema:

- **Generación Paralela de Trazas (`ProcessPoolExecutor`):** La creación de cientos de trazas sintéticas (`generate_traces.py` y `generate_paper_traces.py`) se distribuye automáticamente entre los núcleos de CPU disponibles, logrando aceleraciones de **>3x**.
- **Orquestación Multicore del Benchmark (`run_benchmarks.py`):** En lugar de ejecutar simulaciones en serie, el orquestador spawnea procesos independientes sobre `benchmark.exe` dividiendo la carga de trabajo de manera conservadora (`cpu_count() - 1`). Evita condiciones de carrera en I/O utilizando archivos temporales con el flag `--manifest-suffix`, los cuales se fusionan automáticamente al finalizar, logrando aceleraciones de **>20x**.
- **Modo Compacto sin I/O Pesado (`--compact`):** Para exploraciones asintóticas masivas donde no se requieren gráficos de costo por acceso (como en *Paper Replication*), el flag `--compact` suprime la escritura de archivos CSV gigantes en el motor C++, reduciendo los tiempos de ejecución de minutos a segundos.
- **Optimización de Caché en C++:** El cálculo del interleave bound en `benchmark.cpp` utiliza un acceso plano a memoria (`std::vector<int8_t>` 1-indexed) que garantiza localidad espacial y $O(1)$ en búsqueda.
- **Análisis Ultra-Rápido en Python:** Los scripts de gráficos (`analyze.py` y `analyze_real_world.py`) implementan carga en memoria con el motor compilado en C (`engine="c"`) y sistemas de caché de DataFrames, reduciendo el tiempo de generación de figuras de minutos a segundos. -->

## Estructura del Proyecto

```
EDA-Project/
├── src/
│   ├── benchmark.cpp            # Driver del benchmark C++
│   ├── trees_test.cpp           # Suite de tests de correctitud unitarios
│   └── trees/
│       ├── bst.hpp              # Template base de BST
│       ├── splaycount.hpp       # Splay Tree con contador de ops
│       ├── tangocount.hpp       # Tango Tree con contador de ops
│       ├── multisplaycount.hpp  # Multi-Splay Tree con contador de ops
│       └── rbtreecount.hpp      # Red-Black Tree (baseline)
│
├── tools/
│   ├── run_benchmarks.py        # Orquestador multicore para ejecución masiva en paralelo
│   ├── generate_traces.py       # Generador de trazas en paralelo (state transitions)
│   ├── generate_paper_traces.py # Generador en paralelo para replicación del paper
│   ├── convert_nasa_logs.py     # Conversor de logs NASA HTTP
│   ├── analyze.py               # Análisis normalizado y gráficos de state transitions
│   ├── analyze_real_world.py    # Análisis normalizado de workloads reales
│   └── plot_paper_comparisons.py# Gráficos normalizados de replicación del paper
│
├── tests/
│   └── test_generate_traces.py  # Tests unitarios del generador
│
├── data/
│   ├── traces/                  # Trazas de entrada generadas
│   │   ├── state_transitions/
│   │   ├── paper_replication/
│   │   └── real_world/
│   ├── results/                 # Resultados de los benchmarks
│   │   ├── results_manifest.jsonl
│   │   ├── state_transitions/
│   │   ├── paper_replication/
│   │   └── real_world/
│   └── analysis/                # Salida normalizada de análisis y reportes
│       ├── README.md
│       ├── summary_state_transitions.csv
│       └── plots/
│           ├── state_transitions/   # 25 figuras de transiciones y adaptación
│           ├── paper_replication/   # 4 figuras de escalamiento asintótico (Figs 3-6)
│           └── real_world/          # 5 figuras de evaluación de servidores NASA
│
├── CMakeLists.txt
└── README.md
```

## Herramientas

| Herramienta | Descripcion |
|------------|-------------|
| `run_benchmarks.py` | Orquestador multicore que distribuye la ejecución del binario C++ entre los núcleos del sistema en paralelo, gestionando la concurrencia y la consolidación de manifiestos |
| `generate_traces.py` | Genera trazas reproducibles en paralelo con patrones S/W/F/R. Soporta `--suite quick` (validación) y `--suite full` (experimento formal) |
| `generate_paper_traces.py` | Genera trazas asintóticas en paralelo para replicar los resultados del paper de referencia |
| `convert_nasa_logs.py` | Convierte logs HTTP de la NASA (formato CLF) a trazas enteras con hashing de URLs |
| `analyze.py` | Lee resultados del benchmark y genera gráficos normalizados de adaptación, recovery y heatmaps en `data/analysis/plots/state_transitions/` |
| `analyze_real_world.py` | Genera gráficos normalizados para trazas reales en `data/analysis/plots/real_world/` |
| `plot_paper_comparisons.py` | Genera figuras de nivel publicación para el paper en `data/analysis/plots/paper_replication/` |

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
 "avg_ops_per_access":1.71}
```

## Requisitos

- **C++20** + **CMake** (estructuras y benchmark)
- **Python 3.10+** con `pandas`, `matplotlib`, `numpy`, `scipy`, `tqdm`

## Setup

### 1. Instalar dependencias Python
```powershell
pip install pandas matplotlib numpy scipy tqdm
```

### 2. Compilar binarios C++
```powershell
cmake -B build
cmake --build build --config Release
```

### 3. Validar correctitud
```powershell
# Linux/Mac:
./build/trees_test
# Windows:
.\build\trees_test.exe
```

## Pipeline Completo

> **Nota:** El directorio `data/` está en `.gitignore`. Debes generar las trazas y resultados localmente.

### 1. Track Principal: State Transitions (Adaptación Dinámica)

```powershell
# 1. Generar trazas sintéticas en paralelo (quick para validación, full para experimento formal)
python tools/generate_traces.py --suite full --out data/traces/state_transitions --seed 2026

# 2. Ejecutar simulaciones masivas en paralelo (multicore)
python tools/run_benchmarks.py --traces data/traces/state_transitions --out data/results/state_transitions --exe build/benchmark.exe

# 3. Generar reportes CSV y figuras normalizadas (usa defaults)
python tools/analyze.py
```

### 2. Track Asintótico: Replicación del Paper MIT

```powershell
# 1. Generar trazas de escalamiento asintótico en paralelo (hasta n=1,048,576)
python tools/generate_paper_traces.py

# 2. Ejecutar benchmark en paralelo (--compact: omite CSVs gigantes para acelerar)
python tools/run_benchmarks.py --traces data/traces/paper_replication --out data/results/paper_replication --exe build/benchmark.exe --compact

# 3. Generar figuras de replicación de publicación (Figuras 3, 4, 5 y 6)
python tools/plot_paper_comparisons.py --results data/results/paper_replication --out data/analysis
```

### 3. Track Real-World: Servidores NASA HTTP Logs

```powershell
# 1. Descargar logs manualmente desde los espejos oficiales
#    ftp://ita.ee.lbl.gov/traces/NASA_access_log_Jul95.gz
#    ftp://ita.ee.lbl.gov/traces/NASA_access_log_Aug95.gz

# 2. Convertir logs al formato de trazas del framework
#    Los archivos .gz deben estar en <path/to/downloads>
python tools/convert_nasa_logs.py --log-dir <path/to/downloads> --out-dir data/traces

# 3. Ejecutar benchmark masivo sobre las 3.4M operaciones en paralelo
python tools/run_benchmarks.py --traces data/traces/real_world --out data/results/real_world --exe build/benchmark.exe

# 4. Generar curvas de costo real y distribuciones de operaciones
python tools/analyze_real_world.py --results data/results/real_world --out data/analysis
```

## Referencias

- **Paper de referencia:** Al-Adhami & Chheda, "Theoretical insights and an experimental comparison of tango trees and multi-splay trees," arXiv:2405.18825, 2024
- **Implementacion de arboles:** vendoreados de [`adhami3310/tango`](https://github.com/adhami3310/tango) (MIT)
- **Dataset NASA:** Kennedy Space Center HTTP logs, July-August 1995 (ftp://ita.ee.lbl.gov/traces/)
