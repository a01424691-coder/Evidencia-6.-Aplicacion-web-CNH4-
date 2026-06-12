# Evidencia-6.-Aplicacion-web-CNH4-
# De los Datos a la Acción
**Equipo CNH 4**
- Jezrel Hernández Alvarado - A01340173
- George Patricio Espinosa Pérez - A01712476
- María Fernanda San Román Orozco - A01424691

*Analítica de datos y herramientas de inteligencia artificial Grupo [601]*
**Socio formador:** CNHMX
---

# Problematica
A pesar de su infraestructura, su sistema actual responde preguntas del pasado: cuántos servicios se cerraron, cuántos quedaron pendientes y qué distribuidores tuvieron más volumen. Pero no permite anticipar qué sucederá ni identificar con qué clientes o equipos actuar antes de perder oportunidades.

## Descripción del proyecto

Este proyecto analiza la flota conectada de equipos agrícolas y de construcción de CNHMX con el objetivo de identificar oportunidades de monetización after-market no capturadas. A partir de datos de telemetría y registros de mantenimiento, se construyó un pipeline analítico completo que va desde la exploración de datos hasta un score prescriptivo de priorización de intervención por equipo.

La aplicación web integra tres capas de análisis: exploración descriptiva (EDA), modelado estadístico y de machine learning (H1–H12), e insights accionables con impacto directo en revenue.

---

## Tecnologías utilizadas

### Framework web — Dash
Se eligió **Dash** sobre Streamlit por tres razones concretas. Primero, Dash permite control total sobre el layout con componentes HTML/CSS nativos, lo que fue necesario para replicar la identidad visual de CNH Industrial. Segundo, los callbacks de Dash soportan interactividad multi-componente sin recargar la página, lo que permite que los filtros de distribuidor, marca y estado actualicen simultáneamente KPIs y gráficas. Tercero, el resultado final se comporta como una aplicación web real, no como un notebook convertido, lo que facilita su adopción operativa por parte de CNHMX.

### Visualización — Plotly
**Plotly** es la librería de visualización nativa de Dash y fue la elección natural dado que el equipo ya la usaba en el notebook de análisis. Permite gráficas interactivas (hover, zoom, filtros) sin configuración adicional, y soporta tipos de gráfica avanzados como mapas scatter, heatmaps, curvas de supervivencia y tablas formateadas, todos necesarios para el dashboard.

### Procesamiento de datos — Pandas y NumPy
**Pandas** fue la columna vertebral del pipeline de datos. El dataset maestro (`df_MASTER`) es un dataframe orientado a eventos de servicio resultado del merge entre telemetría a nivel equipo y registros de mantenimiento a nivel evento. La naturaleza del merge (one-to-many) requirió deduplicación cuidadosa por `no._serie` antes de calcular cualquier métrica de flota, lógica que se implementó íntegramente con Pandas. **NumPy** se usó para cálculos vectorizados en la construcción de curvas de supervivencia y transformaciones logarítmicas del modelo H7.

### Modelado estadístico y ML — scikit-learn, scipy, statsmodels
**scikit-learn** se usó para el modelo Random Forest de H10 (predicción de incumplimiento 600→900 hrs) y para la normalización MinMaxScaler del heatmap de urgencia por estado. **scipy** proveyó los tests de Kruskal-Wallis (H1, H2, H5) y Mann-Whitney U (H3, H4). **statsmodels** se usó para las regresiones logísticas (H6, H8) y la regresión cuadrática (H7).

### Análisis de supervivencia — lifelines
**lifelines** se usó para el ajuste de las curvas Kaplan-Meier y el modelo Cox Proportional Hazards de H11, que modelan la probabilidad de fuga del cliente (pérdida de la relación de servicio con la red oficial CNH) en función del horómetro acumulado, segmento y constructos latentes.

---

## Estructura del repositorio

```
CNH4/
├── app.py                        # Aplicación web Dash
├── requirements.txt              # Dependencias
├── README.md                     # Este archivo
├── assets/
│   └── style.css                 # Estilos del dashboard
├── data/
│   ├── df_master.csv             # Dataset maestro (telemetría × mantenimiento)
│   ├── df_limpio_h1.csv          # Dataset H10: predicción incumplimiento
│   ├── df_prescripcion.csv       # Dataset H12: score prescriptivo
│   ├── df_supervivencia.csv      # Dataset H11: análisis de supervivencia
│   ├── df_cox.csv                # Dataset Cox PH
│   ├── df_surv.csv               # Dataset KM por segmento
│   ├── df_diag_equipo.csv        # Dataset diagnóstico por equipo
│   ├── df_h7.csv                 # Dataset regresión cuadrática DMU
│   ├── df_master_modelos.csv     # Variables calculadas para modelos H1–H5
│   └── df_insights.csv           # Variables para página de insights
└── notebook/
    └── Base_modelos_Graficas_Finales.ipynb   # Notebook completo de análisis
```

---

## Instrucciones para correr la aplicación

### 1. Clonar el repositorio

```bash
git clone https://github.com/CNH4/cnhmx-fleet-analytics.git
cd cnhmx-fleet-analytics
```

### 2. Instalar dependencias

```bash
pip install -r requirements.txt
```

### 3. Colocar los archivos de datos

Asegúrate de que todos los archivos `.csv` listados en la sección anterior estén en la misma carpeta que `app.py`. Si partes del notebook, exporta los datasets con:

```python
df_MASTER.to_csv("df_master.csv", index=False)
df_limpio_h1.to_csv("df_limpio_h1.csv", index=False)
df_prescripcion.to_csv("df_prescripcion.csv", index=False)
df_supervivencia.to_csv("df_supervivencia.csv", index=False)
df_cox.to_csv("df_cox.csv", index=False)
df_surv.to_csv("df_surv.csv", index=False)
df_diag_equipo.to_csv("df_diag_equipo.csv", index=False)
df_h7.to_csv("df_h7.csv", index=False)

df_MASTER[['no._serie','distribuidor','estado','Segmento','fecha',
           'Mes_Servicio','DMU_Servicio','DMU_Actual','DOE_Prom_Mensual',
           'MA_Potencial_Perdido','CEM_Porcentaje_Error','servicio',
           'pendientes','estatus','combustible',
           '50','300','600','900','1200','1500','1800','2100','2400']
].to_csv("df_insights.csv", index=False)

df_MASTER[['Mes_Servicio','DMU_Servicio','CEM_Porcentaje_Error','servicio',
           'DOE_Prom_Mensual','MA_Potencial_Perdido','Segmento']
].to_csv("df_master_modelos.csv", index=False)
```

### 4. Correr la aplicación

```bash
python app.py
```

Abre tu navegador en `http://127.0.0.1:8050`

---

## requirements.txt

```
dash>=2.14.0
plotly>=5.18.0
pandas>=2.0.0
numpy>=1.24.0
scikit-learn>=1.3.0
scipy>=1.11.0
statsmodels>=0.14.0
lifelines>=0.27.0
```

---

## Justificación del enfoque de predicción

El pipeline analítico se organizó en torno a seis constructos latentes derivados de la literatura de marketing relacional y mantenimiento predictivo: **DOE** (Demanda Operativa del Equipo), **CAD** (Características de Adopción del Distribuidor), **CEM** (Cumplimiento Estándar de Mantenimiento), **DMU** (Desfase de Mantenimiento Urgente), **RP** (Resultado de Predicción) y **MA** (Monetización Aftermarket). DOE y CAD funcionan como variables exógenas, CEM y DMU como mediadores, y RP y MA como outputs.

El enfoque combina tres capas de modelado con objetivos distintos.

La primera capa es **diagnóstica**, con tests no paramétricos (Kruskal-Wallis y Mann-Whitney U) para validar diferencias significativas en CEM y DMU entre grupos de interés — intervalos de servicio, meses del año, estados y segmentos. Esto establece la base empírica de los insights accionables sin asumir normalidad en los datos, lo que es apropiado dado que las distribuciones de horómetro y desfase son asimétricas.

La segunda capa es **predictiva**, con dos modelos complementarios. El primero es un Random Forest para clasificar equipos con alta probabilidad de incumplir el servicio de 900 hrs dado que ya pasaron el de 600 hrs (H10). Se eligió Random Forest sobre regresión logística porque captura interacciones no lineales entre DOE, CEM histórico y DMU sin requerir supuestos distribucionales. El segundo es un modelo de supervivencia Cox Proportional Hazards (H11) para estimar la tasa de hazard de fuga del cliente en función del tiempo operativo. El análisis de supervivencia es el enfoque correcto aquí porque la variable de interés es el tiempo hasta el evento (pérdida de la relación de servicio), no una clasificación binaria en un punto fijo del tiempo.

La tercera capa es **prescriptiva**, con un score compuesto (H12) que pondera DMU normalizado y número de omisiones reales para rankear equipos por urgencia de intervención. El score fue validado con chi-cuadrado (χ²=471.02, p=1.93×10⁻¹⁰⁴), confirmando que la distribución de éxito de OT no es aleatoria respecto al ranking, lo que sustenta su uso operativo para priorizar llamadas de campo y asignación de recursos de taller.

---

*Proyecto académico profesional — Tecnológico de Monterrey × CNHMX — 2026*
