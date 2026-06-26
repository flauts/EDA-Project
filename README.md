# Evaluacion Experimental de BSTs Autoajustables bajo Secuencias No Estacionarias

Framework de evaluacion para comparar el comportamiento dinamico de Splay Trees, Tango Trees y Multi-Splay Trees frente a secuencias de acceso cambiantes.

## Estructuras Evaluadas
- **Splay Trees** -- autoajustables clasicos
- **Tango Trees** -- O(log log n)-competitivos vs la cota IB-1
- **Multi-Splay Trees** -- referencia adicional del paper

## Cuatro Pistas Experimentales

| Pista | Proposito | Generador |
|-------|-----------|-----------|
| **State Transitions** (core) | Costo de adaptacion bajo cambios de patron | `generate_traces.py` |
| **Paper Replication** (minimal) | Validacion contra paper de referencia | `generate_paper_traces.py` + `plot_paper_comparisons.py` |
| **Superiority Frontier** | Donde arboles autoajustables superan a estaticos | `generate_superiority_traces.py` |
| **YCSB Cloud** | Cargas realistas estilo cloud (Zipfian) | `generate_zipfian_traces.py` |

Ver [`SCOPE.md`](SCOPE.md) para detalles de cada pista.

## Metricas

- **Costo de Adaptacion:** penalidad por cambio de fase
- **Costo de Recuperacion:** memoria estructural retenida (A->B->A)
- **Cota IB-1:** lower bound teorico de Wilber
- **Ratio ops/IB-1:** que tan cerca del optimo opera cada arbol

## Requisitos

- **C++20** + **CMake** (estructuras y benchmark)
- **Python 3.10+** con `pandas`, `matplotlib`, `numpy`, `scipy`, `tqdm`

## Pipeline Completo

```powershell
# 1. Generar trazas (quick para validacion, full para experimento formal)
python tools/generate_traces.py --suite quick --out data/traces --seed 2026

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

## Pistas Adicionales

```powershell
# Paper replication (1-2 slides de presentacion)
python tools/generate_paper_traces.py
python tools/plot_paper_comparisons.py

# Superiority frontier (comparacion vs arboles estaticos)
python tools/generate_superiority_traces.py

# YCSB cloud workloads
python tools/generate_zipfian_traces.py
```

## Recursos

- **Diseno:** [`SCOPE.md`](SCOPE.md) con las cuatro pistas experimentales
- **Implementacion:** arboles vendoreados de [`adhami3310/tango`](https://github.com/adhami3310/tango) (MIT)
- **Referencia:** Al-Adhami & Chheda, "Theoretical insights and an experimental comparison of tango trees and multi-splay trees," arXiv:2405.18825, 2024
