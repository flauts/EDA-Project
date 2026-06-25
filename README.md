# Evaluación Experimental de BSTs Autoajustables bajo Secuencias No Estacionarias

Este repositorio contiene el *framework* de evaluación para comparar el comportamiento dinámico de árboles binarios de búsqueda autoajustables (Splay Trees, Tango Trees y Multi-Splay Trees) frente a secuencias de acceso cambiantes y dinámicas.

## ¿Qué y Cómo Evaluamos?
* **Estructuras:** *Splay Trees*, *Tango Trees* y *Multi-Splay Trees*.
* **Trazas Evaluadas (Experimentos exactos):**
  * **4 Estáticas:** Secuencial (`S`), Aleatorio Uniforme (`R`), Working Set (`W`) y Localidad Espacial (`F`).
  * **8 Transiciones Simples (Pares):** (S$\to$W, S$\to$F, W$\to$S, W$\to$F, W$\to$R, F$\to$S, F$\to$W, R$\to$W) para evaluar la latencia de adaptación.
  * **6 Transiciones de Recuperación (Triples A$\to$B$\to$A):** S$\to$W$\to$S, S$\to$F$\to$S, W$\to$S$\to$W, W$\to$F$\to$W, F$\to$S$\to$F, F$\to$W$\to$F. Miden cuánta memoria estructural conserva el árbol.
  * **1 Transición en Cadena:** S$\to$W$\to$F.
* **Métricas:** Costo de Adaptación (penalidad por cambio de fase) y Costo de Recuperación (memoria estructural retenida). 
* **Línea Base:** Modelo de costo BST tradicional de Wilber medido incrementalmente, comparado contra la cota teórica óptima **IB-1**.

## Estructura del Proyecto

El proyecto está estructurado en 4 módulos principales totalmente funcionales:

1. **M1: Generación de Trazas (Python)**: Produce *workloads* sintéticos estáticos y dinámicos (con transiciones de fase para simular pérdida de *locality*).
2. **M2: Implementación de BSTs (C++)**: Estructuras Splay, Tango y Multi-Splay (vendoreadas y adaptadas) con una interfaz común e instrumentación por acceso.
3. **M3: Benchmark (C++)**: Motor de ejecución que evalúa las estructuras contra las trazas y calcula empíricamente la cota inferior Wilber-1 (IB-1).
4. **M4: Análisis Comparativo (Python)**: Scripts para generar métricas operativas (costo de adaptación, costo de recuperación) y gráficos comparativos.

## Requisitos

*   **C++20** y **CMake** (para compilar las estructuras y el benchmark)
*   **Python 3.10+** con las librerías: `pandas`, `matplotlib`, `numpy`, `tqdm`

## Ejecución del Pipeline Completo (Validación Rápida)

Para correr un flujo end-to-end rápido (con tamaños $n$ pequeños), ejecuta:

```powershell
# 1. Generar trazas de prueba (M1)
python tools/generate_traces.py --suite quick --out data/traces --seed 2026

# 2. Compilar el proyecto (M2 y M3)
cmake -B build
cmake --build build

# (Opcional) Validar la correctitud de los árboles
.\build\trees_test.exe

# 3. Ejecutar el benchmark sobre las trazas generadas
.\build\benchmark.exe --traces data/traces --out data/results --trees splay,tango,multisplay

# 4. Generar análisis, CSVs de resumen y gráficos (M4)
python tools/analyze.py --results data/results --out data/analysis --traces data/traces
```

> **Nota:** Para generar los datos del experimento formal (con árboles de hasta $n=65535$), cambia el flag a `--suite full` en el paso 1.

## Flujo de Trabajo para el Paper (Pipeline Formal)

Hemos comprobado empíricamente que la longitud de fase por defecto (`5n`) es más que suficiente para que todos los árboles converjan a un estado estable antes de la transición. Por tanto, el pipeline formal es de un solo paso:

```powershell
python tools/generate_traces.py --suite full --out data/traces
.\build\benchmark.exe --traces data/traces --out data/results --trees splay,tango,multisplay
python tools/analyze.py --results data/results --out data/analysis --traces data/traces
```

## Recursos del Proyecto
*   **Reporte de Avance:** Archivo LaTeX `avance_proyecto.tex` (contiene la estructura del avance de la investigación).
*   **Diseño:** Archivo `PLAN.md` con las decisiones arquitectónicas.
