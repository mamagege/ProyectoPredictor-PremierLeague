# HITO 2: PREDICCIÓN DE RESULTADOS DE FÚTBOL MEDIANTE REDES NEURONALES PROFUNDAS (DEEP MLP)

**Institución:** Escuela Colombiana de Ingeniería Julio Garavito  
**Departamento:** Departamento de Ingeniería de Sistemas  
**Curso:** Principiosy Tecnologías de Inteligencia Artificial (PTIA)  
**Grupo:** Grupo 04  
**Integrantes:**
- Juan Diego Gaitán
- José Alejandro Martínez
- Oscar David Lasso
- Carlos Andrés Sánchez  
**Fecha de Entrega:** Octubre 2026  

---

## Contenido de la Carpeta `hito2`

Esta carpeta contiene los entregables oficiales del Hito 2:

1. **`Proyecto3_Red_Neuronal_Profunda_EPL.ipynb`**  
   Notebook principal interactivo estructurado en 20 secciones pedagógicas: lectura de datos, preprocesamiento sin fuga temporal (*zero data leakage*), arquitectura de red neuronal profunda con regularización (Dropout, BatchNorm, L2), curvas de aprendizaje, matrices de confusión, comparación con modelos de referencia (*baselines*), análisis de calibración y pruebas de predicción.



3. **`prediction_service.py`**  
   Módulo reutilizable en Python que implementa la función `predecir_partido(equipo_local, equipo_visitante, fecha_partido, cuotas)` para realizar inferencia con la red neuronal entrenada.

4. **Carpeta `models/`**  
   Contiene los artefactos serializados listos para inferencia y evaluación:
   - `best_deep_mlp.keras`: Arquitectura y pesos óptimos del modelo de Deep Learning entrenado.
   - `scaler.pkl`: Objeto `StandardScaler` ajustado exclusivamente con el conjunto de entrenamiento.
   - `feature_names.json`: Lista oficial de las 38 características de entrada pre-partido.
   - `training_summary.json`: Registro de métricas finales, matrices de confusión y resultados comparativos.

5. **Carpeta `datasets/`**  
   Contiene las tres fuentes tabulares históricas completas para que la entrega sea 100% autónoma e independiente:
   - `English Premier League Match Data (2000-2025)/` (`epl_final.csv`)
   - `Premier League (1993 - Present)/` (`PremierLeague.csv`)
   - `Club Football Match Data (2000 - 2026)/` (`Matches.csv`, `EloRatings.csv`)

---

## Instrucciones de Ejecución

### 1. Ejecutar el Notebook
Abrir `Proyecto3_Red_Neuronal_Profunda_EPL.ipynb` en VS Code o Jupyter Lab y seleccionar "Run All".

### 2. Ejecutar Pruebas de Predicción
Desde una terminal en esta carpeta o en la raíz:
```bash
python prediction_service.py
```
El script ejecutará casos de estudio emblemáticos (Arsenal vs Chelsea, Man City vs Liverpool, Hull vs Everton) y una prueba de robustez ante equipos desconocidos.
