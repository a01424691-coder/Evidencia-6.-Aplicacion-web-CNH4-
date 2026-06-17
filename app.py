# -*- coding: utf-8 -*-
"""
CNHMX Fleet Analytics — Version final
Ejecutar:  python app.py   ->  http://127.0.0.1:8050

Archivos necesarios en la misma carpeta:
    app.py
    df_master.csv
    df_limpio_h1.csv
    df_prescripcion.csv
    df_supervivencia.csv
    df_cox.csv
    df_surv.csv
    df_diag_equipo.csv
    df_h7.csv
    df_master_modelos.csv
    df_insights.csv
    assets/style.css
"""

import dash
from dash import Dash, dcc, html, Input, Output, State, ctx, ALL
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd
import numpy as np

# ============================================================================
# PALETA / TEMA
# ============================================================================
C = {
    "bg": "#08090B", "bg2": "#111216", "card": "#1B1C21", "border": "#D4A900",
    "yellow": "#F4C400", "white": "#F5F5F5", "grey": "#A5A5A5",
    "red": "#E32636", "orange": "#F28C28", "green": "#20B26B",
}

PLOTLY_LAYOUT = dict(
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="rgba(0,0,0,0)",
    font=dict(color=C["white"], family="Segoe UI, Roboto, sans-serif", size=12),
    margin=dict(l=45, r=20, t=55, b=45),
    legend=dict(font=dict(color=C["grey"])),
    xaxis=dict(gridcolor="#26272d", zerolinecolor="#26272d", color=C["grey"]),
    yaxis=dict(gridcolor="#26272d", zerolinecolor="#26272d", color=C["grey"]),
    colorway=[C["yellow"], C["red"], C["green"], C["orange"], "#5DADE2", "#AF7AC5", "#48C9B0", "#EC7063"],
)


def tema(fig):
    fig.update_layout(**PLOTLY_LAYOUT)
    fig.update_layout(title_font=dict(color=C["yellow"], size=15))
    return fig


def tema_mapa(fig):
    fig.update_layout(
        paper_bgcolor="rgba(0,0,0,0)",
        font=dict(color=C["white"], family="Segoe UI, Roboto, sans-serif"),
        margin=dict(l=0, r=0, t=55, b=0),
        title_font=dict(color=C["yellow"], size=15),
        legend=dict(font=dict(color=C["white"]), bgcolor="rgba(27,28,33,0.7)"),
    )
    return fig


def fig_vacia(msg="Sin datos para los filtros seleccionados"):
    f = go.Figure()
    f.update_layout(**PLOTLY_LAYOUT)
    f.add_annotation(text=msg, showarrow=False, font=dict(color=C["grey"], size=14))
    f.update_xaxes(visible=False)
    f.update_yaxes(visible=False)
    return f


# ============================================================================
# CARGA Y PREPARACION DE DATOS
# ============================================================================
df = pd.read_csv("df_master.csv", low_memory=False)
df_eq = df.drop_duplicates(subset="no._serie", keep="first").copy()

# Datos de modelos
df_h1     = pd.read_csv("df_limpio_h1.csv", low_memory=False)
df_presc  = pd.read_csv("df_prescripcion.csv", low_memory=False)
df_surv_k = pd.read_csv("df_supervivencia.csv", low_memory=False)
df_cox_   = pd.read_csv("df_cox.csv", low_memory=False)
df_surv_  = pd.read_csv("df_surv.csv", low_memory=False)
df_diag   = pd.read_csv("df_diag_equipo.csv", low_memory=False)
df_h7_    = pd.read_csv("df_h7.csv", low_memory=False)
df_mm     = pd.read_csv("df_master_modelos.csv", low_memory=False)
df_ins    = pd.read_csv("df_insights.csv", low_memory=False)

# Join supervivencia con prescripcion para filtros
df_surv_k = df_surv_k.merge(
    df_presc[["no._serie", "distribuidor", "estado", "Segmento"]].drop_duplicates("no._serie"),
    on="no._serie", how="left"
)

meses = [c for c in df.columns if c.startswith("2024-") or c.startswith("2025-")]
meses_2024 = [c for c in meses if c.startswith("2024-")]
meses_2025 = [c for c in meses if c.startswith("2025-")]

intervalos = ["50", "300", "600", "900", "1200", "1500", "1800", "2100", "2400"]

bins = [0, 50, 300, 600, 900, 1200, 1500, 1800, 2100, 2400, np.inf]
labels_bins = ["0–50", "50–300", "300–600", "600–900", "900–1200",
               "1200–1500", "1500–1800", "1800–2100", "2100–2400", "2400+"]
df_eq["rango_horometro"] = pd.cut(df_eq["horometro"], bins=bins, labels=labels_bins, right=False)

opciones_distribuidor = [{"label": d, "value": d} for d in sorted(df_eq["distribuidor"].dropna().unique())]
opciones_marca        = [{"label": m, "value": m} for m in sorted(df_eq["marca"].dropna().unique())]
opciones_estado       = [{"label": e, "value": e} for e in sorted(df_eq["estado"].dropna().unique())]
opciones_segmento     = [{"label": s, "value": s} for s in ["AGRICOLA", "CONSTRUCCION"]]

HORO_MAX = int(df_eq["horometro"].max())


def _fmt(n):
    return f"{n/1_000_000:.1f}M" if n >= 1_000_000 else (f"{n/1_000:.0f}k" if n >= 10_000 else f"{n:,.0f}")


KG = {
    "equipos":       f"{len(df_eq):,}",
    "distribuidores":f"{df_eq['distribuidor'].nunique():,}",
    "estados":       f"{df_eq['estado'].nunique():,}",
    "marcas":        f"{df_eq['marca'].nunique():,}",
    "horas":         _fmt(float(df_eq["horometro"].sum())),
    "cerrados":      f"{int(pd.to_numeric(df_eq['cerrados'], errors='coerce').sum()):,}",
    "pendientes":    f"{int(pd.to_numeric(df_eq['pendientes'], errors='coerce').sum()):,}",
    "ots":           f"{len(df):,}",
}

# Valores iniciales KPIs indicadores
KPI_IND_DEFAULT = {
    "total":    f"{df_eq['no._serie'].nunique():,}",
    "con_s":    f"{(df_eq['total_servicios'] > 0).sum():,}",
    "sin_s":    f"{(df_eq['total_servicios'] == 0).sum():,}",
    "cerr":     f"{int(pd.to_numeric(df_eq['cerrados'], errors='coerce').sum()):,}",
    "pend":     f"{int(pd.to_numeric(df_eq['pendientes'], errors='coerce').sum()):,}",
    "tasa50":   f"{df_eq['50'].isin(['CERRADA','CERRADAFUERA']).sum() / len(df_eq) * 100:.1f}%",
    "int_prom": f"{sum(df_eq[iv].isin(['CERRADA','CERRADAFUERA']).astype(int) for iv in intervalos if iv in df_eq.columns).mean():.2f}",
}

# Valores iniciales KPIs modelos
_dp0 = df_presc.drop_duplicates("no._serie")
_dh0 = df_h1
_ds0 = df_surv_k

def _calc_ma(dp_uniq):
    intervalos_num = [50, 300, 600, 900, 1200, 1500, 1800, 2100, 2400]
    rec, perd = 0, 0
    for _, row in dp_uniq.iterrows():
        horo = row.get("horometro", 0)
        for iv in intervalos_num:
            col = str(iv)
            if col not in row.index: continue
            if row[col] in ["PENDIENTE", "PORVENCER"]:
                if iv >= horo: rec += iv
                else:          perd += iv
    return rec, perd

_ma_rec0, _ma_perd0 = _calc_ma(_dp0)

KPI_MOD_DEFAULT = {
    "incump": f"{int((_dh0['Probabilidad_Incumplimiento_900hrs'] >= 0.5).sum()):,}" if 'Probabilidad_Incumplimiento_900hrs' in _dh0.columns else "—",
    "fuga":   f"{int(_ds0['Evento_Fuga'].sum()):,}" if 'Evento_Fuga' in _ds0.columns else "—",
    "ots_rec":f"{int(df_presc.nsmallest(max(1,int(len(df_presc)*0.20)),'Rank_Score')['Exito_OT'].sum()):,}" if 'Rank_Score' in df_presc.columns else "—",
    "desfase":f"{int((_dp0['DMU_Actual'] > 30).sum()):,}" if 'DMU_Actual' in _dp0.columns else "—",
    "ma_rec": _fmt(_ma_rec0),
    "ma_perd":_fmt(_ma_perd0),
}


# ============================================================================
# HELPERS UI
# ============================================================================
def ddmulti(id_, options, ph):
    return dcc.Dropdown(id=id_, options=options, multi=True, placeholder=ph, className="cnh-dd")


def chart(graph_id):
    return html.Div(dcc.Graph(id=graph_id, config={"displayModeBar": False}), className="chart-card")


def kpi_static(value, label, accent=C["yellow"]):
    return html.Div(className="kpi-card", style={"borderTop": f"3px solid {accent}"}, children=[
        html.Div(value, className="kpi-value", style={"color": accent}),
        html.Div(label, className="kpi-label"),
    ])


def kpi_dynamic(id_, label, accent=C["yellow"], default="—"):
    return html.Div(className="kpi-card", style={"borderTop": f"3px solid {accent}"}, children=[
        html.Div(default, id=id_, className="kpi-value", style={"color": accent}),
        html.Div(label, className="kpi-label"),
    ])


CFG = {"displayModeBar": False}


# ============================================================================
# GENERADORES DE GRAFICAS EDA
# ============================================================================
def filtra_s1(d, marcas, estados, rango):
    if marcas:  d = d[d["marca"].isin(marcas)]
    if estados: d = d[d["estado"].isin(estados)]
    d = d[(d["horometro"] >= rango[0]) & (d["horometro"] <= rango[1])]
    return d


def g1_marca(d):
    if d.empty: return fig_vacia()
    s = d["marca"].value_counts().reset_index()
    s.columns = ["marca", "equipos"]
    f = px.bar(s, x="marca", y="equipos", title="Distribución de equipos por marca",
               labels={"marca": "Marca", "equipos": "Número de equipos"})
    return tema(f)


def g2_horometro_marca(d):
    if d.empty: return fig_vacia()
    s = d.dropna(subset=["marca"]).groupby("marca")["horometro"].mean().round(0).sort_values()
    f = go.Figure(go.Bar(
        x=s.values, y=s.index, orientation="h",
        marker_color=C["yellow"],
        text=[f"{v:,.0f} hrs" for v in s.values], textposition="outside"))
    f.update_layout(title="Horómetro promedio por marca",
                    xaxis_title="Horómetro promedio (hrs)", yaxis_title="")
    return tema(f)


def g3_antiguedad(d):
    if d.empty: return fig_vacia()
    s = d["rango_horometro"].value_counts().reindex(labels_bins).reset_index()
    s.columns = ["rango", "equipos"]
    f = px.bar(s, x="rango", y="equipos", title="Antigüedad aproximada por rango de horómetro",
               labels={"rango": "Rango (hrs)", "equipos": "Número de equipos"})
    return tema(f)


def g4_mapa(d):
    md = (d.dropna(subset=["latitud", "longitud", "distribuidor"])
          .groupby("distribuidor")
          .agg(lat=("latitud","mean"), lon=("longitud","mean"), equipos=("no._serie","count"))
          .reset_index())
    if md.empty: return fig_vacia("Sin coordenadas para mostrar en el mapa")
    f = px.scatter_map(md, lat="lat", lon="lon", size="equipos", color="distribuidor",
                       hover_name="distribuidor",
                       hover_data={"equipos": True, "lat": False, "lon": False},
                       title="Distribución geográfica por distribuidor",
                       zoom=4, height=460, map_style="carto-darkmatter")
    return tema_mapa(f)


def g5_cobertura(d):
    rows = []
    for iv in intervalos:
        if iv in d.columns:
            cerrado = d[iv].isin(["CERRADA","CERRADAFUERA"]).sum()
            pend    = d[iv].isin(["PENDIENTE","PORVENCER"]).sum()
            sin     = (d[iv].isna() | (d[iv] == "")).sum()
            rows += [{"intervalo": iv, "estado": "Cerrado",             "equipos": cerrado},
                     {"intervalo": iv, "estado": "Pendiente/Por vencer","equipos": pend},
                     {"intervalo": iv, "estado": "Sin registro",         "equipos": sin}]
    if not rows: return fig_vacia()
    f = px.bar(pd.DataFrame(rows), x="intervalo", y="equipos", color="estado",
               title="Cobertura por intervalo de servicio",
               labels={"intervalo":"Intervalo (hrs)","equipos":"Equipos","estado":"Estado"},
               color_discrete_map={"Cerrado": C["green"],
                                   "Pendiente/Por vencer": C["orange"],
                                   "Sin registro": C["red"]})
    return tema(f)


def g6_completados(d):
    d = d.copy()
    d["intervalos_completados"] = sum(
        d[iv].isin(["CERRADA","CERRADAFUERA"]).astype(int)
        for iv in intervalos if iv in d.columns)
    s = d["intervalos_completados"].value_counts().sort_index().reset_index()
    s.columns = ["intervalos_completados", "equipos"]
    f = px.bar(s, x="intervalos_completados", y="equipos",
               title="Distribución de intervalos completados por equipo",
               labels={"intervalos_completados":"Intervalos completados","equipos":"Equipos"})
    return tema(f)


def g7_prom_dist(d):
    top10 = d["distribuidor"].value_counts().head(10).index.tolist()
    dt = d[d["distribuidor"].isin(top10)]
    if dt.empty: return fig_vacia()
    pr = dt.groupby("distribuidor")[["cerrados","pendientes"]].mean().reset_index()
    pr = pr.melt(id_vars="distribuidor", var_name="tipo", value_name="promedio")
    f = px.bar(pr, x="distribuidor", y="promedio", color="tipo", barmode="group",
               title="Servicios y pendientes promedio — Top 10 distribuidores",
               labels={"distribuidor":"Distribuidor","promedio":"Promedio por equipo","tipo":"Tipo"},
               color_discrete_map={"cerrados": C["green"], "pendientes": C["red"]})
    f.update_xaxes(tickangle=45)
    return tema(f)


def g8_estatus(d_full):
    de = d_full.dropna(subset=["estatus","distribuidor"])
    if de.empty: return fig_vacia()
    s = de.groupby(["distribuidor","estatus"]).size().reset_index(name="count")
    f = px.bar(s, x="distribuidor", y="count", color="estatus",
               title="Estatus de órdenes de trabajo por distribuidor",
               labels={"distribuidor":"Distribuidor","count":"Órdenes","estatus":"Estatus"})
    f.update_xaxes(tickangle=45)
    return tema(f)


def g9_anual(d):
    p24 = d[meses_2024].mean().mean()
    p25 = d[meses_2025].mean().mean()
    da = pd.DataFrame({"año": ["2024","2025"], "horas_promedio": [p24, p25]})
    f = px.bar(da, x="año", y="horas_promedio", title="Horas de uso promedio — 2024 vs 2025",
               labels={"año":"Año","horas_promedio":"Horas promedio mensuales"})
    return tema(f)


def g10_anual_dist(d):
    top5 = d["distribuidor"].value_counts().head(5).index.tolist()
    dt = d[d["distribuidor"].isin(top5)]
    if dt.empty: return fig_vacia()
    rows = []
    for dist in top5:
        sub = dt[dt["distribuidor"] == dist]
        rows += [{"distribuidor": dist, "año": "2024", "horas_promedio": sub[meses_2024].mean().mean()},
                 {"distribuidor": dist, "año": "2025", "horas_promedio": sub[meses_2025].mean().mean()}]
    f = px.bar(pd.DataFrame(rows), x="distribuidor", y="horas_promedio", color="año", barmode="group",
               title="Horas de uso promedio 2024 vs 2025 — Top 5 distribuidores",
               labels={"distribuidor":"Distribuidor","horas_promedio":"Horas promedio","año":"Año"})
    f.update_xaxes(tickangle=45)
    return tema(f)


# ============================================================================
# GENERADORES DE GRAFICAS DE MODELOS (H1–H12)
# ============================================================================

def gm1_cem_intervalo():
    intervalos_std = [50,300,600,900,1200,1500,1800,2100,2400]
    d = df_mm[df_mm["servicio"].isin(intervalos_std) & df_mm["CEM_Porcentaje_Error"].notna()]
    if d.empty: return fig_vacia()
    tabla = d.groupby("servicio")["CEM_Porcentaje_Error"].mean().round(2).reset_index()
    tabla.columns = ["Intervalo","CEM_Promedio"]
    colores = [C["red"] if v > 50 else C["orange"] if v > 10 else C["green"]
               for v in tabla["CEM_Promedio"]]
    f = go.Figure(go.Bar(
        x=tabla["Intervalo"].astype(str), y=tabla["CEM_Promedio"],
        marker_color=colores,
        text=tabla["CEM_Promedio"].apply(lambda x: f"{x:.1f}%"),
        textposition="outside",
        hovertemplate="<b>Servicio %{x} hrs</b><br>Error promedio: %{y:.1f}%<extra></extra>"))
    f.update_layout(title="H1 — Error de cumplimiento por intervalo de servicio",
                    xaxis_title="Intervalo (hrs)", yaxis_title="Error promedio (%)")
    return tema(f)


def gm2_dmu_mes():
    d = df_mm[df_mm["Mes_Servicio"].notna() & df_mm["DMU_Servicio"].notna()]
    if d.empty: return fig_vacia()
    tabla = d.groupby("Mes_Servicio")["DMU_Servicio"].mean().round(2).reset_index()
    tabla.columns = ["Mes","DMU_Promedio"]
    tabla = tabla.sort_values("Mes")
    nombres = ["Ene","Feb","Mar","Abr","May","Jun","Jul","Ago","Sep","Oct","Nov","Dic"]
    tabla["Mes_Nombre"] = tabla["Mes"].apply(lambda m: nombres[int(m)-1] if 1<=int(m)<=12 else str(m))
    colores = [C["red"] if m==6 else C["orange"] if m>=4 else C["yellow"]
               for m in tabla["Mes"].astype(int)]
    f = go.Figure(go.Bar(
        x=tabla["Mes_Nombre"], y=tabla["DMU_Promedio"],
        marker_color=colores,
        text=tabla["DMU_Promedio"].apply(lambda x: f"{x:.0f} hrs"),
        textposition="outside",
        hovertemplate="<b>%{x}</b><br>Desfase promedio: %{y:.1f} hrs<extra></extra>"))
    f.update_layout(title="H2 — Desfase promedio de mantenimiento por mes",
                    xaxis_title="Mes", yaxis_title="Horas promedio de desfase (DMU)")
    return tema(f)


def gm3_doe_segmento():
    d = df_diag[df_diag["Segmento"].isin(["AGRICOLA","CONSTRUCCION"]) &
                df_diag["DOE_Prom_Mensual"].notna()]
    if d.empty: return fig_vacia()
    f = px.box(d, x="Segmento", y="DOE_Prom_Mensual", color="Segmento",
               color_discrete_map={"AGRICOLA": C["yellow"], "CONSTRUCCION": C["orange"]},
               title="H3 — DOE por segmento (Agrícola vs Construcción)",
               labels={"DOE_Prom_Mensual":"Horas operativas promedio/mes","Segmento":""})
    f.update_traces(boxmean=True)
    return tema(f)


def gm4_ma_segmento():
    d = df_diag[df_diag["Segmento"].isin(["AGRICOLA","CONSTRUCCION"]) &
                df_diag["MA_Potencial_Perdido"].notna()]
    if d.empty: return fig_vacia()
    f = px.box(d, x="Segmento", y="MA_Potencial_Perdido", color="Segmento",
               color_discrete_map={"AGRICOLA": C["yellow"], "CONSTRUCCION": C["orange"]},
               title="H4 — MA Potencial Perdido por segmento",
               labels={"MA_Potencial_Perdido":"MA Potencial Perdido (pts)","Segmento":""})
    f.update_traces(boxmean=True)
    return tema(f)


def gm5_dmu_estado():
    from sklearn.preprocessing import MinMaxScaler
    d2 = df_mm.copy()
    d2["estado"] = df["estado"].reindex(d2.index)
    tabla = (d2.groupby("estado")
               .agg(E_DMU=("DMU_Servicio","mean"), Var_DMU=("DMU_Servicio","var"),
                    N=("DMU_Servicio","count"))
               .round(2))
    tabla = tabla[tabla["N"] >= 30].sort_values("E_DMU", ascending=False).head(10)
    if tabla.empty: return fig_vacia()
    scaler = MinMaxScaler()
    df_norm = pd.DataFrame(
        scaler.fit_transform(tabla[["E_DMU","Var_DMU"]]),
        index=tabla.index,
        columns=["Desfase promedio","Variabilidad del desfase"])
    f = go.Figure(go.Heatmap(
        z=df_norm.values, x=df_norm.columns.tolist(), y=df_norm.index.tolist(),
        colorscale="YlOrRd", zmin=0, zmax=1,
        text=[["ALTO" if v>0.66 else "MEDIO" if v>0.33 else "BAJO" for v in row]
              for row in df_norm.values],
        texttemplate="%{text}",
        colorbar=dict(title="Urgencia", tickvals=[0.16,0.5,0.83],
                      ticktext=["Bajo","Medio","Alto"]),
        hovertemplate="<b>%{y}</b><br>%{x}: %{z:.2f}<extra></extra>"))
    f.update_layout(title="H5 — Estados con mayor urgencia de intervención",
                    yaxis=dict(autorange="reversed"))
    return tema(f)


def gm6_or_h6():
    data = {
        "Variable": ["DOE_prom_mensual","dist_horometro_prom","dist_unidades",
                     "horas_24_25_total","dist_doe_prom"],
        "OR": [5.559, 2.293, 1.615, 0.265, 0.453],
    }
    df_or = pd.DataFrame(data).sort_values("OR")
    colores = [C["green"] if v >= 1 else C["red"] for v in df_or["OR"]]
    f = go.Figure(go.Bar(
        x=df_or["OR"], y=df_or["Variable"], orientation="h",
        marker_color=colores,
        text=df_or["OR"].apply(lambda x: f"{x:.3f}"),
        textposition="outside",
        hovertemplate="<b>%{y}</b><br>OR: %{x:.3f}<extra></extra>"))
    f.add_vline(x=1, line_dash="dash", line_color=C["grey"], line_width=1.5,
                annotation_text="OR = 1", annotation_font_color=C["grey"])
    f.update_layout(title="H6 — Odds Ratios: variables que explican el bajo CEM",
                    xaxis_title="Odds Ratio", yaxis_title="",
                    xaxis=dict(range=[0, 6.5]))
    return tema(f)


def gm7_curva_h7():
    d = df_h7_.copy()
    if d.empty: return fig_vacia()
    d = d[d["DMU"] <= d["DMU"].quantile(0.95)].sample(min(2000, len(d)), random_state=42)
    b0, b1, b2 = 3.5, -0.5548, 0.1607
    x_range = np.linspace(d["DMU_log1p"].min(), d["DMU_log1p"].max(), 200)
    y_curva  = b0 + b1 * x_range + b2 * x_range**2
    x_orig   = np.expm1(x_range)
    inflexion = np.expm1(-b1 / (2 * b2))
    f = go.Figure()
    f.add_trace(go.Scatter(
        x=d["DMU"], y=d["mant_registrados"], mode="markers",
        marker=dict(color=C["grey"], size=4, opacity=0.4),
        name="Equipos", hovertemplate="DMU: %{x:.0f} hrs<br>OTs: %{y}<extra></extra>"))
    f.add_trace(go.Scatter(
        x=x_orig, y=y_curva, mode="lines",
        line=dict(color=C["yellow"], width=3), name="Curva cuadrática ajustada"))
    f.add_vline(x=inflexion, line_dash="dash", line_color=C["red"], line_width=2,
                annotation_text=f"Inflexión: {inflexion:.1f} hrs",
                annotation_font_color=C["red"])
    f.update_layout(title="H7 — Relación no lineal entre DMU y frecuencia de OT",
                    xaxis_title="DMU (hrs de desfase)", yaxis_title="OTs registradas")
    return tema(f)


def gm8_or_h8():
    data = {
        "Variable": ["horas_24_25_prom_mensual","desfase_max",
                     "servicios_omitidos_estimados","c.fuera"],
        "OR": [1.0162, 1.0017, 0.91, 0.88],
    }
    df_or = pd.DataFrame(data).sort_values("OR")
    colores = [C["green"] if v >= 1 else C["red"] for v in df_or["OR"]]
    f = go.Figure(go.Bar(
        x=df_or["OR"], y=df_or["Variable"], orientation="h",
        marker_color=colores,
        text=df_or["OR"].apply(lambda x: f"{x:.4f}"),
        textposition="outside",
        hovertemplate="<b>%{y}</b><br>OR: %{x:.4f}<extra></extra>"))
    f.add_vline(x=1, line_dash="dash", line_color=C["grey"], line_width=1.5,
                annotation_text="OR = 1", annotation_font_color=C["grey"])
    f.update_layout(title="H8 — Odds Ratios: variables que predicen riesgo de pérdida",
                    xaxis_title="Odds Ratio", yaxis_title="",
                    xaxis=dict(range=[0.85, 1.04]))
    return tema(f)


def gm9_r2():
    df_r2 = pd.DataFrame({
        "Modelo": ["Base (solo telemetría)", "Extendido (+ distribuidor)"],
        "R²": [0.0143, 0.1000]
    })
    f = px.bar(df_r2, x="Modelo", y="R²",
               text=df_r2["R²"].apply(lambda x: f"{x:.4f}"),
               color="Modelo",
               color_discrete_map={"Base (solo telemetría)": C["grey"],
                                   "Extendido (+ distribuidor)": C["yellow"]},
               title="H9 — Comparación R²: telemetría vs telemetría + distribuidor",
               labels={"R²": "R² del modelo", "Modelo": ""})
    f.update_traces(textposition="outside")
    f.add_hline(y=0.6, line_dash="dash", line_color=C["red"],
                annotation_text="Umbral objetivo 60%",
                annotation_font_color=C["red"])
    return tema(f)


def gm10_prob_incumplimiento():
    d = df_h1[df_h1["Probabilidad_Incumplimiento_900hrs"].notna()]
    if d.empty: return fig_vacia()
    f = px.histogram(d, x="Probabilidad_Incumplimiento_900hrs", nbins=40,
                     title="H10 — Distribución de probabilidad de incumplimiento (600→900 hrs)",
                     labels={"Probabilidad_Incumplimiento_900hrs": "Probabilidad de incumplimiento"},
                     color_discrete_sequence=[C["yellow"]])
    f.add_vline(x=0.5, line_dash="dash", line_color=C["red"],
                annotation_text="Umbral 50%", annotation_font_color=C["red"])
    f.update_layout(yaxis_title="Número de equipos")
    return tema(f)


def gm10b_feat_importance():
    data = {
        "Variable":    ["DOE_Prom_Mensual","X_CEM_Pasado","horometro","DMU_Actual","pendientes"],
        "Importancia": [0.38, 0.27, 0.18, 0.11, 0.06]
    }
    df_fi = pd.DataFrame(data).sort_values("Importancia")
    f = go.Figure(go.Bar(
        x=df_fi["Importancia"], y=df_fi["Variable"], orientation="h",
        marker_color=C["yellow"],
        text=df_fi["Importancia"].apply(lambda x: f"{x:.2f}"),
        textposition="outside"))
    f.update_layout(title="H10 — Feature importance: Random Forest incumplimiento",
                    xaxis_title="Importancia relativa", yaxis_title="")
    return tema(f)


def gm11_km_flota():
    d = df_surv_k[df_surv_k["horometro"] > 0].copy().sort_values("horometro")
    if d.empty: return fig_vacia()
    n, sv, s = len(d), [], 1.0
    for i, e in enumerate(d["Evento_Fuga"].values):
        if e == 1: s *= (1 - 1/(n - i))
        sv.append(s)
    f = go.Figure()
    f.add_trace(go.Scatter(
        x=d["horometro"].values, y=sv, mode="lines",
        line=dict(color=C["yellow"], width=2, shape="hv"),
        name="Toda la flota",
        hovertemplate="Horómetro: %{x:.0f} hrs<br>Supervivencia: %{y:.3f}<extra></extra>"))
    f.add_hline(y=0.5, line_dash="dash", line_color=C["grey"],
                annotation_text="Mediana de supervivencia",
                annotation_font_color=C["grey"])
    f.update_layout(title="H11 — Curva de supervivencia Kaplan-Meier (flota completa)",
                    xaxis_title="Horómetro (hrs)", yaxis_title="Probabilidad de supervivencia",
                    yaxis=dict(range=[0, 1.05]))
    return tema(f)


def gm11b_km_segmento():
    d = df_surv_[df_surv_["duration"] > 0].copy()
    if d.empty or "Segmento" not in d.columns: return fig_vacia()
    f = go.Figure()
    for seg, color in {"AGRICOLA": C["yellow"], "CONSTRUCCION": C["orange"]}.items():
        sub = d[d["Segmento"] == seg].sort_values("duration")
        if sub.empty: continue
        n, sv, s = len(sub), [], 1.0
        for i, e in enumerate(sub["event"].values):
            if e == 1: s *= (1 - 1/(n - i))
            sv.append(s)
        f.add_trace(go.Scatter(
            x=sub["duration"].values, y=sv, mode="lines",
            line=dict(color=color, width=2, shape="hv"), name=seg.capitalize(),
            hovertemplate=f"{seg}<br>Duración: %{{x:.0f}} hrs<br>Supervivencia: %{{y:.3f}}<extra></extra>"))
    f.add_hline(y=0.5, line_dash="dash", line_color=C["grey"])
    f.update_layout(title="H11 — Kaplan-Meier: Agrícola vs Construcción",
                    xaxis_title="Duración (hrs)", yaxis_title="Probabilidad de supervivencia",
                    yaxis=dict(range=[0, 1.05]))
    return tema(f)


def gm11c_cox_hr():
    data = {
        "Variable": ["DOE_Prom_Mensual","CEM_Historico","DMU_Actual"],
        "HR":       [0.9960, 1.0025, 1.0032],
        "Efecto":   ["Protector","Riesgo","Riesgo"]
    }
    df_hr = pd.DataFrame(data).sort_values("HR")
    colores = [C["green"] if e == "Protector" else C["red"] for e in df_hr["Efecto"]]
    f = go.Figure(go.Bar(
        x=df_hr["HR"], y=df_hr["Variable"], orientation="h",
        marker_color=colores,
        text=df_hr["HR"].apply(lambda x: f"{x:.4f}"),
        textposition="outside",
        hovertemplate="<b>%{y}</b><br>HR: %{x:.4f}<extra></extra>"))
    f.add_vline(x=1, line_dash="dash", line_color=C["grey"], line_width=1.5,
                annotation_text="HR = 1", annotation_font_color=C["grey"])
    f.update_layout(title="H11 — Hazard Ratios Cox: efecto de cada variable sobre fuga",
                    xaxis_title="Hazard Ratio", yaxis_title="",
                    xaxis=dict(range=[0.994, 1.006]))
    return tema(f)


def gm12_scatter_score():
    d = df_presc[df_presc["Score_Prioridad"].notna() &
                 df_presc["DMU_Actual"].notna() &
                 df_presc["N_Omisiones_Reales"].notna()].copy()
    if d.empty: return fig_vacia()
    d = d.sample(min(3000, len(d)), random_state=42)
    f = px.scatter(d, x="DMU_Actual", y="Score_Prioridad",
                   color="N_Omisiones_Reales", color_continuous_scale="YlOrRd",
                   title="H12 — Score prescriptivo vs Desfase actual",
                   labels={"DMU_Actual":"Desfase actual (hrs)",
                           "Score_Prioridad":"Score prescriptivo",
                           "N_Omisiones_Reales":"Omisiones"},
                   opacity=0.6)
    return tema(f)


def gm12_tabla():
    d = df_presc.nsmallest(10, "Rank_Score")[
        ["no._serie","distribuidor","DMU_Actual","N_Omisiones_Reales","Score_Prioridad","Exito_OT"]
    ].copy()
    if d.empty: return fig_vacia()
    d["no._serie"]    = d["no._serie"].astype(str).str[:20]
    d["distribuidor"] = d["distribuidor"].astype(str).str[:15]
    d["Estado"]       = d["Score_Prioridad"].apply(
        lambda s: "CRÍTICO" if s >= 0.85 else "ALTO" if s >= 0.60 else "MEDIO ALTO")
    f = go.Figure(data=[go.Table(
        columnwidth=[180,130,110,100,100,80],
        header=dict(
            values=["<b>Equipo</b>","<b>Distribuidor</b>","<b>Desfase (hrs)</b>",
                    "<b>Omisiones</b>","<b>Score</b>","<b>Estado</b>"],
            fill_color="#1B1C21",
            font=dict(color=C["yellow"], size=12, family="Segoe UI"),
            align="center", height=36),
        cells=dict(
            values=[d["no._serie"], d["distribuidor"],
                    d["DMU_Actual"].apply(lambda x: f"{x:,.0f}"),
                    d["N_Omisiones_Reales"].apply(lambda x: f"{int(x)}"),
                    d["Score_Prioridad"].apply(lambda x: f"{x:.3f}"),
                    d["Estado"]],
            fill_color=[["#1B1C21" if i%2==0 else "#111216" for i in range(10)]]*6,
            font=dict(color=[C["white"]]*5+[C["red"]], size=11),
            align="center", height=32)
    )])
    f.update_layout(title="H12 — Top 10 equipos a intervenir (score prescriptivo)",
                    height=420, paper_bgcolor="rgba(0,0,0,0)",
                    font=dict(color=C["white"], family="Segoe UI"))
    return f


# ============================================================================
# GENERADORES DE GRAFICAS DE INSIGHTS (presentación)
# ============================================================================

def gi1_dmu_mes():
    d = df_ins[df_ins["Mes_Servicio"].notna() & df_ins["DMU_Servicio"].notna()]
    if d.empty: return fig_vacia()
    tabla = d.groupby("Mes_Servicio")["DMU_Servicio"].mean().round(2).reset_index()
    tabla.columns = ["Mes","DMU_Promedio"]
    tabla = tabla.sort_values("Mes")
    nombres = ["Ene","Feb","Mar","Abr","May","Jun","Jul","Ago","Sep","Oct","Nov","Dic"]
    tabla["Mes_Nombre"] = tabla["Mes"].apply(lambda m: nombres[int(m)-1] if 1<=int(m)<=12 else str(m))
    colores = [C["red"] if m==6 else C["orange"] if m>=4 else C["yellow"]
               for m in tabla["Mes"].astype(int)]
    f = go.Figure(go.Bar(
        x=tabla["Mes_Nombre"], y=tabla["DMU_Promedio"],
        marker_color=colores,
        text=tabla["DMU_Promedio"].apply(lambda x: f"{x:.0f} hrs"),
        textposition="outside",
        hovertemplate="<b>%{x}</b><br>Desfase promedio: %{y:.1f} hrs<extra></extra>"))
    f.update_layout(
        title="Desfase promedio de mantenimiento por mes<br><sup>Junio concentra el mayor desfase del año</sup>",
        xaxis_title="Mes", yaxis_title="Horas promedio de desfase (DMU)")
    return tema(f)


def gi2_ma_distribuidor():
    d = (df_ins.sort_values("fecha", ascending=False)
         .drop_duplicates(subset="no._serie", keep="first")
         .groupby("distribuidor")
         .agg(MA_Total=("MA_Potencial_Perdido","sum"),
              Promedio_DMU=("DMU_Actual","mean"),
              N=("no._serie","nunique"))
         .reset_index()
         .dropna(subset=["distribuidor"])
         .nlargest(10,"MA_Total")
         .sort_values("MA_Total"))
    if d.empty: return fig_vacia()
    n = len(d)
    colores = [C["orange"]] * max(n-3, 0) + [C["red"]] * min(3, n)
    f = go.Figure()
    f.add_trace(go.Bar(
        x=d["MA_Total"], y=d["distribuidor"], orientation="h",
        marker=dict(color=colores, line=dict(color="white", width=0.5)),
        text=d["N"].apply(lambda x: f"{x:,} equipos"),
        textposition="inside", insidetextanchor="middle",
        textfont=dict(color="white", size=11),
        customdata=d[["Promedio_DMU","N"]].values,
        hovertemplate="<b>%{y}</b><br>MA Potencial: %{x:,.0f} pts<br>DMU promedio: %{customdata[0]:.1f} hrs<extra></extra>"))
    f.add_trace(go.Scatter(
        x=d["MA_Total"], y=d["distribuidor"], mode="text",
        text=d["MA_Total"].apply(lambda x: f"{x:,.0f} pts"),
        textposition="middle right",
        textfont=dict(size=11, color=C["white"]),
        showlegend=False, hoverinfo="skip"))
    f.update_layout(
        title="MA Potencial No Capturado por Distribuidor<br><sup>Top 3 con mayor monetización perdida</sup>",
        xaxis=dict(title="MA Potencial Total (pts)", tickformat=",",
                   range=[0, d["MA_Total"].max() * 1.3]),
        yaxis_title="Distribuidor",
        margin=dict(l=150, r=160, t=90, b=60))
    return tema(f)


def gi3_pendientes_distribuidor():
    d = (df_ins.sort_values("fecha", ascending=False)
         .drop_duplicates(subset="no._serie", keep="first")
         .groupby("distribuidor")
         .agg(Servicios_Pendientes=("pendientes","sum"),
              Promedio_DMU=("DMU_Actual","mean"),
              N=("no._serie","nunique"))
         .reset_index()
         .dropna(subset=["distribuidor"])
         .nlargest(10,"Servicios_Pendientes")
         .sort_values("Servicios_Pendientes"))
    if d.empty: return fig_vacia()
    f = go.Figure(go.Bar(
        x=d["Servicios_Pendientes"], y=d["distribuidor"], orientation="h",
        marker=dict(color=d["Promedio_DMU"], colorscale="Reds",
                    colorbar=dict(title="DMU Promedio<br>(hrs)"),
                    line=dict(color="white", width=0.5)),
        text=d.apply(lambda r: f"{r['Servicios_Pendientes']:,.0f} | {r['N']:,} equipos", axis=1),
        textposition="outside",
        customdata=d[["Promedio_DMU","N"]].values,
        hovertemplate="<b>%{y}</b><br>Pendientes: %{x:,}<br>DMU: %{customdata[0]:.1f} hrs<extra></extra>"))
    f.update_layout(
        title="Concentración de servicios pendientes por distribuidor<br><sup>Color = urgencia por desfase promedio</sup>",
        xaxis=dict(title="Servicios pendientes", tickformat=","),
        margin=dict(r=200))
    return tema(f)


def gi4_top10_tabla():
    d = df_presc.nsmallest(10, "Rank_Score")[
        ["no._serie","distribuidor","DMU_Actual","N_Omisiones_Reales","Score_Prioridad","Exito_OT"]
    ].copy()
    if d.empty: return fig_vacia()
    d["no._serie"]    = d["no._serie"].astype(str).str[:20]
    d["distribuidor"] = d["distribuidor"].astype(str).str[:15]
    d["Estado"]       = d["Score_Prioridad"].apply(
        lambda s: "CRÍTICO" if s>=0.85 else "ALTO" if s>=0.60 else "MEDIO ALTO")
    f = go.Figure(data=[go.Table(
        columnwidth=[180,130,110,100,100,90],
        header=dict(
            values=["<b>Equipo</b>","<b>Distribuidor</b>","<b>Desfase (hrs)</b>",
                    "<b>Omisiones</b>","<b>Score</b>","<b>Estado</b>"],
            fill_color="#1B1C21",
            font=dict(color=C["yellow"], size=12, family="Segoe UI"),
            align="center", height=36),
        cells=dict(
            values=[d["no._serie"], d["distribuidor"],
                    d["DMU_Actual"].apply(lambda x: f"{x:,.0f}"),
                    d["N_Omisiones_Reales"].apply(lambda x: f"{int(x)}"),
                    d["Score_Prioridad"].apply(lambda x: f"{x:.3f}"),
                    d["Estado"]],
            fill_color=[["#1B1C21" if i%2==0 else "#111216" for i in range(10)]]*6,
            font=dict(color=[C["white"]]*5+[C["red"]], size=11),
            align="center", height=32))])
    f.update_layout(
        title="Top 10 equipos a intervenir HOY — Score prescriptivo (χ²=471.02, p=1.93×10⁻¹⁰⁴)",
        height=420, paper_bgcolor="rgba(0,0,0,0)",
        font=dict(color=C["white"], family="Segoe UI"))
    return f


def gi5_cem_intervalo():
    ivs = [50,300,600,900,1200,1500,1800,2100,2400]
    d = df_ins[df_ins["servicio"].isin(ivs) & df_ins["CEM_Porcentaje_Error"].notna()]
    if d.empty: return fig_vacia()
    tabla = d.groupby("servicio")["CEM_Porcentaje_Error"].mean().round(2).reset_index()
    tabla.columns = ["Intervalo","CEM_Promedio"]
    colores = [C["red"] if v>50 else C["orange"] if v>10 else C["green"]
               for v in tabla["CEM_Promedio"]]
    f = go.Figure(go.Bar(
        x=tabla["Intervalo"].astype(str), y=tabla["CEM_Promedio"],
        marker_color=colores,
        text=tabla["CEM_Promedio"].apply(lambda x: f"{x:.1f}%"),
        textposition="outside",
        hovertemplate="<b>Servicio %{x} hrs</b><br>Error: %{y:.1f}%<extra></extra>"))
    f.update_layout(
        title="Error de cumplimiento por intervalo de servicio<br><sup>El cliente aprende a cumplir conforme el equipo madura</sup>",
        xaxis_title="Intervalo (hrs)", yaxis_title="Error promedio (%)")
    return tema(f)


def gi6_captura_50():
    d = (df_ins.sort_values("fecha", ascending=False)
         .drop_duplicates(subset="no._serie", keep="first").copy())
    d["tiene_50"] = d["50"].isin(["CERRADA","CERRADAFUERA"])
    dc = (d.groupby("distribuidor")
          .agg(Total=("no._serie","nunique"), Con_50=("tiene_50","sum"))
          .reset_index().dropna(subset=["distribuidor"]))
    dc["Tasa"] = (dc["Con_50"] / dc["Total"] * 100).round(1)
    dc = (dc[dc["Total"] >= 30]
          .sort_values("Tasa", ascending=False)
          .tail(10).sort_values("Tasa", ascending=True))
    if dc.empty: return fig_vacia()
    f = go.Figure(go.Bar(
        x=dc["Tasa"], y=dc["distribuidor"], orientation="h",
        marker=dict(color=[C["red"] if v<80 else C["green"] for v in dc["Tasa"]],
                    line=dict(color="white", width=0.5)),
        text=dc["Tasa"].apply(lambda v: f"{v:.1f}%"),
        textposition="outside",
        customdata=dc[["Con_50","Total"]].values,
        hovertemplate="<b>%{y}</b><br>Captura: %{x:.1f}%<br>%{customdata[0]:,} de %{customdata[1]:,} equipos<extra></extra>"))
    f.add_vline(x=80, line_dash="dot", line_color=C["green"], line_width=2,
                annotation_text="Meta: 80%", annotation_font_color=C["green"],
                annotation_position="top right")
    f.update_layout(
        title="10 distribuidores con menor captura del primer servicio<br><sup>Los que más necesitan la cláusula de garantía</sup>",
        xaxis=dict(title="% equipos con 50 hrs completado", range=[0,110], ticksuffix="%"),
        margin=dict(r=80))
    return tema(f)


def gi7_doe_segmento():
    d = (df_ins.sort_values("fecha", ascending=False)
         .drop_duplicates(subset="no._serie", keep="first")
         .query("Segmento != 'OTRO'")
         [["no._serie","Segmento","DOE_Prom_Mensual","MA_Potencial_Perdido"]]
         .dropna())
    if d.empty: return fig_vacia()
    resumen = d.groupby("Segmento").agg(
        DOE_Med=("DOE_Prom_Mensual","median"),
        MA_Med=("MA_Potencial_Perdido","mean")).reset_index()
    agro  = resumen[resumen["Segmento"]=="AGRICOLA"].iloc[0]
    const = resumen[resumen["Segmento"]=="CONSTRUCCION"].iloc[0]
    pct   = (const["DOE_Med"] - agro["DOE_Med"]) / agro["DOE_Med"] * 100
    f = go.Figure(go.Bar(
        x=["Agrícola","Construcción"],
        y=[agro["DOE_Med"], const["DOE_Med"]],
        marker_color=[C["yellow"], C["orange"]],
        text=[f"{agro['DOE_Med']:.1f} hrs/mes\n⚡ Alerta: 500 hrs",
              f"{const['DOE_Med']:.1f} hrs/mes\n⚡ Alerta: 250 hrs"],
        textposition="outside", width=0.4))
    f.add_annotation(x=1, y=const["DOE_Med"]*0.5,
        text=f"+{pct:.0f}%<br>más uso mensual", showarrow=False,
        font=dict(color=C["orange"], size=13),
        bgcolor="rgba(27,28,33,0.8)", bordercolor=C["orange"], borderwidth=1.5)
    f.update_layout(
        title="Construcción opera más horas por mes que Agrícola<br><sup>Su umbral de alerta debe ser menor</sup>",
        yaxis=dict(title="Horas operativas por mes (mediana)",
                   range=[0, const["DOE_Med"]*1.5]))
    return tema(f)


def gi8_ma_segmento():
    d = (df_ins.sort_values("fecha", ascending=False)
         .drop_duplicates(subset="no._serie", keep="first")
         .query("Segmento != 'OTRO'")
         [["no._serie","Segmento","MA_Potencial_Perdido"]]
         .dropna())
    if d.empty: return fig_vacia()
    resumen = d.groupby("Segmento")["MA_Potencial_Perdido"].mean().reset_index()
    agro  = resumen[resumen["Segmento"]=="AGRICOLA"]["MA_Potencial_Perdido"].values[0]
    const = resumen[resumen["Segmento"]=="CONSTRUCCION"]["MA_Potencial_Perdido"].values[0]
    pct   = (const - agro) / agro * 100
    f = go.Figure(go.Bar(
        x=["Agrícola","Construcción"], y=[agro, const],
        marker_color=[C["yellow"], C["orange"]],
        text=[f"{agro:,.0f} pts", f"{const:,.0f} pts"],
        textposition="outside", width=0.4))
    f.add_annotation(x=1, y=const*0.5,
        text=f"+{pct:.0f}%<br>más potencial perdido<br>por equipo", showarrow=False,
        font=dict(color=C["orange"], size=13),
        bgcolor="rgba(27,28,33,0.8)", bordercolor=C["orange"], borderwidth=1.5)
    f.update_layout(
        title="Construcción pierde más monetización por equipo<br><sup>Mayor uso → mayor MA no capturado</sup>",
        yaxis=dict(title="MA Potencial promedio por equipo (pts)", range=[0, const*1.5]))
    return tema(f)


def gi9_dmu_agricola():
    d = (df_ins.sort_values("fecha", ascending=False)
         .drop_duplicates(subset="no._serie", keep="first")
         .query("Segmento == 'AGRICOLA' and DMU_Actual > 0")
         ["DMU_Actual"].dropna())
    if d.empty: return fig_vacia()
    n_riesgo = (d > 500).sum()
    pct = n_riesgo / len(d) * 100
    f = go.Figure(go.Histogram(
        x=d.clip(upper=1500), marker_color=C["yellow"], opacity=0.85, nbinsx=35,
        hovertemplate="Desfase: %{x:.0f} hrs<br>Equipos: %{y:,}<extra></extra>"))
    f.add_vline(x=500, line_dash="dash", line_color=C["red"], line_width=2.5)
    f.add_annotation(x=500, y=1, xref="x", yref="paper",
        text=f"<b>{pct:.1f}% en riesgo<br>({n_riesgo:,} equipos)</b>",
        showarrow=False, font=dict(color=C["red"], size=12),
        bgcolor="rgba(27,28,33,0.8)", bordercolor=C["red"], borderwidth=1.5,
        xanchor="left", yanchor="top")
    f.update_layout(
        title="Agrícola: equipos que superaron umbral de alerta (500 hrs)<br><sup>Todo a la derecha debe ser contactado hoy</sup>",
        xaxis_title="Desfase actual (hrs) — valores >1,500 agrupados",
        yaxis_title="Número de equipos")
    return tema(f)


def gi10_dmu_construccion():
    d = (df_ins.sort_values("fecha", ascending=False)
         .drop_duplicates(subset="no._serie", keep="first")
         .query("Segmento == 'CONSTRUCCION' and DMU_Actual > 0")
         ["DMU_Actual"].dropna())
    if d.empty: return fig_vacia()
    n_riesgo = (d > 250).sum()
    pct = n_riesgo / len(d) * 100
    f = go.Figure(go.Histogram(
        x=d.clip(upper=1500), marker_color=C["orange"], opacity=0.85, nbinsx=35,
        hovertemplate="Desfase: %{x:.0f} hrs<br>Equipos: %{y:,}<extra></extra>"))
    f.add_vline(x=250, line_dash="dash", line_color=C["red"], line_width=2.5)
    f.add_annotation(x=250, y=1, xref="x", yref="paper",
        text=f"<b>{pct:.1f}% en riesgo<br>({n_riesgo:,} equipos)</b>",
        showarrow=False, font=dict(color=C["red"], size=12),
        bgcolor="rgba(27,28,33,0.8)", bordercolor=C["red"], borderwidth=1.5,
        xanchor="left", yanchor="top")
    f.update_layout(
        title="Construcción: equipos que superaron umbral de alerta (250 hrs)<br><sup>Ventana de riesgo llega antes — mismo desfase, mayor urgencia</sup>",
        xaxis_title="Desfase actual (hrs) — valores >1,500 agrupados",
        yaxis_title="Número de equipos")
    return tema(f)


def gi11_heatmap_estados():
    from sklearn.preprocessing import MinMaxScaler
    d = (df_ins.sort_values("fecha", ascending=False)
         .groupby("no._serie").last().reset_index())
    d = d[d["DMU_Actual"].notna() & (d["DOE_Prom_Mensual"] > 0)].copy()
    if d.empty or "estado" not in d.columns: return fig_vacia()
    tabla = (d.groupby("estado")
              .agg(E_DOE=("DOE_Prom_Mensual","mean"),
                   E_DMU=("DMU_Actual","mean"),
                   Var_DMU=("DMU_Actual","var"),
                   N=("DMU_Actual","count"))
              .round(2))
    tabla = tabla[tabla["N"] >= 30].sort_values("E_DMU", ascending=False)
    if tabla.empty: return fig_vacia()
    scaler = MinMaxScaler()
    df_norm = pd.DataFrame(
        scaler.fit_transform(tabla[["E_DOE","E_DMU","Var_DMU"]]),
        index=tabla.index,
        columns=["Exigencia operativa","Desfase promedio","Variabilidad del desfase"])
    top5 = df_norm.index[:5].tolist()
    f = go.Figure(go.Heatmap(
        z=df_norm.values, x=df_norm.columns.tolist(), y=df_norm.index.tolist(),
        colorscale="YlOrRd", zmin=0, zmax=1,
        text=[["ALTO" if v>0.66 else "MEDIO" if v>0.33 else "BAJO" for v in row]
              for row in df_norm.values],
        texttemplate="%{text}",
        colorbar=dict(title="Urgencia", tickvals=[0.16,0.5,0.83],
                      ticktext=["Bajo","Medio","Alto"]),
        hovertemplate="<b>%{y}</b><br>%{x}: %{z:.2f}<extra></extra>"))
    for i, est in enumerate(df_norm.index):
        if est in top5:
            f.add_shape(type="rect", x0=-0.5, x1=2.5, y0=i-0.5, y1=i+0.5,
                        line=dict(color=C["red"], width=3), fillcolor="rgba(0,0,0,0)")
    f.update_layout(
        title="¿En qué estados es más urgente actuar?<br><sup>Top 5 (borde rojo) = reasignar fuerza de ventas y taller</sup>",
        height=max(500, len(df_norm)*35),
        yaxis=dict(autorange="reversed"))
    return tema(f)


# ============================================================================
# FIGURAS ESTATICAS
# ============================================================================
FIG_FLOTA = g1_marca(df_eq)
FIG_MANT  = g5_cobertura(df_eq)
FIG_TELE  = g9_anual(df_eq)
FIG_DIST  = g8_estatus(df)

FIG_M = {
    "h1":   gm1_cem_intervalo(),
    "h2":   gm2_dmu_mes(),
    "h3":   gm3_doe_segmento(),
    "h4":   gm4_ma_segmento(),
    "h5":   gm5_dmu_estado(),
    "h6":   gm6_or_h6(),
    "h7":   gm7_curva_h7(),
    "h8":   gm8_or_h8(),
    "h9":   gm9_r2(),
    "h10a": gm10_prob_incumplimiento(),
    "h10b": gm10b_feat_importance(),
    "h11a": gm11_km_flota(),
    "h11b": gm11b_km_segmento(),
    "h11c": gm11c_cox_hr(),
    "h12a": gm12_scatter_score(),
    "h12b": gm12_tabla(),
}

FIG_I = {
    "i1":  gi1_dmu_mes(),
    "i2":  gi2_ma_distribuidor(),
    "i3":  gi3_pendientes_distribuidor(),
    "i4":  gi4_top10_tabla(),
    "i5":  gi5_cem_intervalo(),
    "i6":  gi6_captura_50(),
    "i7":  gi7_doe_segmento(),
    "i8":  gi8_ma_segmento(),
    "i9":  gi9_dmu_agricola(),
    "i10": gi10_dmu_construccion(),
    "i11": gi11_heatmap_estados(),
}


# ============================================================================
# APP
# ============================================================================
app = Dash(__name__, suppress_callback_exceptions=True, title="CNHMX Fleet Analytics")
server = app.server

NAV = [("Inicio", "/"), ("Indicadores", "/indicadores"), ("Dashboard", "/dashboard"),
       ("Modelos", "/modelos"), ("Insights", "/insights"), ("Contacto", "/contacto")]


def nav_link(label, path, key=None, cta=False):
    cls = "nav-link nav-cta" if cta else "nav-link"
    return dcc.Link(label, href=path, id={"type": "navlink", "index": key or path}, className=cls)


navbar = html.Div(className="navbar", children=[
    html.Div(className="nav-inner", children=[
        dcc.Link(className="nav-brand", href="/", children=[
            html.Span("CNHMX Fleet Analytics", className="brand-title"),
            html.Span("Case IH · New Holland · CNH Industrial", className="brand-sub"),
        ]),
        html.Div(className="nav-links", children=[
            *[nav_link(lbl, path) for lbl, path in NAV],
            nav_link("Ver dashboard", "/dashboard", key="cta", cta=True),
        ]),
    ])
])


# ---------- HERO ----------
hero_mock = html.Div(className="hero-mock", children=[
    html.Div(className="mock-head", children=[
        html.Span("CNHMX · Dashboard", className="mock-title"),
        html.Span("● ● ●", className="mock-dots"),
    ]),
    html.Div(className="mock-kpis", children=[
        html.Div(className="mock-kpi", children=[html.B(KG["equipos"]),       html.Span("Equipos")]),
        html.Div(className="mock-kpi", children=[html.B(KG["distribuidores"]),html.Span("Distribuidores")]),
        html.Div(className="mock-kpi", children=[html.B(KG["horas"]),         html.Span("Horas")]),
    ]),
    html.Div(className="mock-bars", children=[
        html.Div(className="mbar", style={"height": f"{h}%"}) for h in [40, 70, 55, 90, 60, 80, 50]
    ]),
    html.Div(className="mock-legend", children=[
        html.Span("● Cerrado",     style={"color": C["green"]}),
        html.Span("● Por vencer",  style={"color": C["orange"]}),
        html.Span("● Sin registro",style={"color": C["red"]}),
    ]),
])

hero = html.Section(className="section hero", children=[
    html.Div(className="hero-grid", children=[
        html.Div(className="hero-left", children=[
            html.Div("CNH Industrial · Case IH · New Holland", className="eyebrow"),
            html.H1("Análisis inteligente de la flota CNHMX"),
            html.P("Exploración de datos operativos de equipos agrícolas: estado de la flota, "
                   "comportamiento de mantenimiento y tendencia histórica de uso, sobre más de "
                   f"{KG['equipos']} equipos monitoreados.", className="lead"),
            html.Div(className="hero-btns", children=[
                dcc.Link("Explorar dashboard", href="/dashboard", className="btn btn-primary"),
                dcc.Link("Ver indicadores",    href="/indicadores", className="btn btn-ghost"),
            ]),
        ]),
        html.Div(className="hero-right", children=[hero_mock]),
    ])
])


# ---------- INDICADORES ----------
VALORES = [
    ("Mejor seguimiento",       "Visibilidad completa de la flota activa y su estado operativo."),
    ("Reducción de desfases",   "Menor cantidad de mantenimientos fuera de tiempo y servicios omitidos."),
    ("Priorización eficiente",  "Identificación de distribuidores y equipos con mayor rezago."),
    ("Mayor captura aftermarket","Conversión de pendientes en órdenes de trabajo dentro de la red CNH."),
]

indicadores = html.Section(className="section", children=[
    html.H2("Indicadores clave"),
    html.P("Métricas reales calculadas sobre toda la flota.", className="subtitle"),
    html.Div(className="filtros-bar", children=[
        html.Div(className="filtro", children=[
            html.Label("Marca"),
            ddmulti("f_marca_ind", opciones_marca, "Todas las marcas")]),
        html.Div(className="filtro", children=[
            html.Label("Estado"),
            ddmulti("f_estado_ind", opciones_estado, "Todos los estados")]),
        html.Div(className="filtro", style={"flex": "1 1 320px"}, children=[
            html.Label("Rango de horómetro (hrs)"),
            dcc.RangeSlider(id="f_horo_ind", min=0, max=HORO_MAX, step=500,
                            value=[0, HORO_MAX],
                            marks={0:"0", 25000:"25k", 50000:"50k", 75000:"75k", HORO_MAX:"Max"},
                            tooltip={"placement":"bottom","always_visible":False})]),
    ]),
    html.H3("Histórico", style={"marginTop": "24px", "color": C["grey"]}),
    html.Div(className="cards-grid-6", children=[
        kpi_dynamic("kpi-total-eq",   "Equipos monitoreados",       C["yellow"], KPI_IND_DEFAULT["total"]),
        kpi_dynamic("kpi-con-serv",   "Equipos con servicios",      C["green"],  KPI_IND_DEFAULT["con_s"]),
        kpi_dynamic("kpi-sin-serv",   "Equipos sin servicios",      C["red"],    KPI_IND_DEFAULT["sin_s"]),
        kpi_dynamic("kpi-cerradas",   "OTs cerradas",               C["green"],  KPI_IND_DEFAULT["cerr"]),
        kpi_dynamic("kpi-pendientes", "OTs pendientes",             C["red"],    KPI_IND_DEFAULT["pend"]),
        kpi_dynamic("kpi-tasa50",     "Tasa captura 1er servicio",  C["orange"], KPI_IND_DEFAULT["tasa50"]),
    ]),
    html.Div(className="cards-grid-6", style={"marginTop": "12px"}, children=[
        kpi_dynamic("kpi-int-prom",   "Intervalos completados prom",C["yellow"], KPI_IND_DEFAULT["int_prom"]),
        kpi_static(KG["distribuidores"],"Distribuidores",            C["orange"]),
        kpi_static(KG["estados"],       "Estados con presencia",     C["green"]),
        kpi_static(KG["horas"],         "Horómetro acumulado (hrs)", C["yellow"]),
        kpi_static(KG["marcas"],        "Marcas",                    C["grey"]),
        kpi_static(KG["ots"],           "Eventos totales en dataset",C["grey"]),
    ]),
    html.H2("Valor estratégico para CNH Industrial", style={"marginTop": "44px"}),
    html.Div(className="cards-grid-4", children=[
        html.Div(className="valor-card", children=[html.H3(t), html.P(s)]) for t, s in VALORES
    ]),
    html.Div(className="valor-highlight", children=[
        html.P("Una unidad con alto uso representa valor solo si ese uso se convierte en mantenimiento, "
               "servicio y refacciones dentro de la red CNH. El análisis ayuda a detectar señales "
               "tempranas y ordenar prioridades antes de perder continuidad con el servicio oficial.")
    ]),
])


# ---------- DASHBOARD EDA ----------
dashboard = html.Section(className="section dashboard-sec", children=[
    html.H2("Dashboard EDA — CNHMX Fleet Analytics"),
    html.P("Herramienta interactiva de análisis de la flota.", className="subtitle"),

    html.Div(className="dash-section", children=[
        html.H2("1. Estado de la flota"),
        html.Div(className="filtros-bar", children=[
            html.Div(className="filtro", children=[html.Label("Marca"),
                     ddmulti("f_marca_s1", opciones_marca, "Todas las marcas")]),
            html.Div(className="filtro", children=[html.Label("Estado"),
                     ddmulti("f_estado_s1", opciones_estado, "Todos los estados")]),
            html.Div(className="filtro", children=[html.Label("Distribuidor"),
                     ddmulti("f_dist_s1", opciones_distribuidor, "Todos los distribuidores")]),
            html.Div(className="filtro", style={"flex": "1 1 320px"}, children=[
                html.Label("Rango de horómetro (hrs)"),
                dcc.RangeSlider(id="f_horo_s1", min=0, max=HORO_MAX, step=500, value=[0, HORO_MAX],
                                marks={0:"0",25000:"25k",50000:"50k",75000:"75k",HORO_MAX:"Max"},
                                tooltip={"placement":"bottom","always_visible":False})]),
        ]),
        html.H3("KPIs operativos", style={"marginTop": "24px", "color": C["grey"]}),
        html.Div(className="cards-grid-6", children=[
            kpi_dynamic("dash-kpi-total",    "Total equipos en cartera",         C["yellow"]),
            kpi_dynamic("dash-kpi-con-serv", "Equipos con servicios",            C["green"]),
            kpi_dynamic("dash-kpi-sin-serv", "Equipos sin servicios",            C["red"]),
            kpi_dynamic("dash-kpi-ot-cerr",  "OTs cerradas",                     C["green"]),
            kpi_dynamic("dash-kpi-ot-pend",  "OTs pendientes",                   C["red"]),
            kpi_dynamic("dash-kpi-ma-perd",  "MA potencial perdido (selección)", C["red"]),
        ]),
        html.Div(className="cards-grid-6", style={"marginTop": "12px"}, children=[
            kpi_dynamic("dash-kpi-tasa50",   "Tasa captura servicio 50 hrs",     C["orange"]),
            kpi_dynamic("dash-kpi-dmu30",    "Equipos con desfase crítico DMU>30",C["orange"]),
            kpi_dynamic("dash-kpi-int-prom", "Intervalos completados por equipo",C["yellow"]),
        ]),
        html.Div(className="charts-row", children=[chart("fig1"), chart("fig2")]),
        html.Div(className="charts-row", children=[chart("fig3"), chart("fig4")]),
    ]),

    html.Div(className="dash-section", children=[
        html.H2("2. Comportamiento de mantenimiento"),
        html.Div(className="filtros-bar", children=[
            html.Div(className="filtro", children=[html.Label("Distribuidor"),
                     ddmulti("f_dist_s2", opciones_distribuidor, "Todos los distribuidores")]),
            html.Div(className="filtro", children=[html.Label("Estado"),
                     ddmulti("f_estado_s2", opciones_estado, "Todos los estados")]),
        ]),
        html.Div(className="charts-row", children=[chart("fig5"), chart("fig6")]),
        html.Div(className="charts-row", children=[chart("fig7"), chart("fig8")]),
    ]),

    html.Div(className="dash-section", children=[
        html.H2("3. Tendencia histórica de uso"),
        html.Div(className="filtros-bar", children=[
            html.Div(className="filtro", children=[html.Label("Distribuidor"),
                     ddmulti("f_dist_s3", opciones_distribuidor, "Todos los distribuidores")]),
            html.Div(className="filtro", children=[html.Label("Marca"),
                     ddmulti("f_marca_s3", opciones_marca, "Todas las marcas")]),
        ]),
        html.Div(className="charts-row", children=[chart("fig9"), chart("fig10")]),
    ]),
])


# ---------- MODELOS ----------
def seccion_modelos(titulo, subtitulo, graficas):
    children = []
    if titulo:    children.append(html.H2(titulo))
    if subtitulo: children.append(html.P(subtitulo, className="subtitle"))
    children.append(
        html.Div(className="charts-row",
                 children=[html.Div(dcc.Graph(figure=g, config=CFG), className="chart-card")
                            for g in graficas]))
    return html.Div(className="dash-section", children=children)


modelos = html.Section(className="section dashboard-sec", children=[
    html.H2("Modelos estadísticos y de ML — H1 a H12"),
    html.P("Visualizaciones de todos los modelos del pipeline analítico.", className="subtitle"),
    html.Div(className="filtros-bar", children=[
        html.Div(className="filtro", children=[
            html.Label("Distribuidor"),
            ddmulti("f_dist_mod", opciones_distribuidor, "Todos los distribuidores")]),
        html.Div(className="filtro", children=[
            html.Label("Estado"),
            ddmulti("f_estado_mod", opciones_estado, "Todos los estados")]),
        html.Div(className="filtro", children=[
            html.Label("Segmento"),
            ddmulti("f_seg_mod", opciones_segmento, "Todos los segmentos")]),
    ]),
    html.H3("Proyecciones del modelo", style={"marginTop": "24px", "color": C["grey"]}),
    html.Div(className="cards-grid-6", children=[
        kpi_dynamic("kpi-riesgo-incump","Equipos en riesgo incumplimiento 600→900 hrs",C["red"],    KPI_MOD_DEFAULT["incump"]),
        kpi_dynamic("kpi-riesgo-fuga",  "Equipos en riesgo de fuga",                   C["red"],    KPI_MOD_DEFAULT["fuga"]),
        kpi_dynamic("kpi-ots-rec",      "OTs recuperables (top 20% score)",            C["green"],  KPI_MOD_DEFAULT["ots_rec"]),
        kpi_dynamic("kpi-desfase-crit", "Equipos con desfase crítico >30 hrs",         C["orange"], KPI_MOD_DEFAULT["desfase"]),
        kpi_dynamic("kpi-ma-rec",       "MA Recuperable (pts)",                        C["green"],  KPI_MOD_DEFAULT["ma_rec"]),
        kpi_dynamic("kpi-ma-perd",      "MA Ya perdido (pts)",                         C["red"],    KPI_MOD_DEFAULT["ma_perd"]),
    ]),
    seccion_modelos("Grupo A — Tests de distribución (H1–H5)",
                    "Kruskal-Wallis y Mann-Whitney U sobre los constructos latentes.",
                    [FIG_M["h1"], FIG_M["h2"]]),
    seccion_modelos("", "", [FIG_M["h3"], FIG_M["h4"]]),
    html.Div(className="dash-section", children=[
        html.Div(className="charts-row", children=[
            html.Div(dcc.Graph(figure=FIG_M["h5"], config=CFG),
                     className="chart-card", style={"flex": "1 1 100%"})])]),
    seccion_modelos("Grupo B — Modelos diagnósticos (H6–H9)",
                    "Regresión logística y lineal para explicar CEM y riesgo de pérdida.",
                    [FIG_M["h6"], FIG_M["h7"]]),
    seccion_modelos("", "", [FIG_M["h8"], FIG_M["h9"]]),
    seccion_modelos("Grupo C — Modelos predictivos (H10–H11)",
                    "Random Forest y análisis de supervivencia para anticipar incumplimiento y fuga.",
                    [FIG_M["h10a"], FIG_M["h10b"]]),
    seccion_modelos("", "", [FIG_M["h11a"], FIG_M["h11b"]]),
    html.Div(className="dash-section", children=[
        html.Div(className="charts-row", children=[
            html.Div(dcc.Graph(figure=FIG_M["h11c"], config=CFG),
                     className="chart-card", style={"flex": "1 1 60%"})])]),
    seccion_modelos("Modelo prescriptivo (H12)",
                    "Score de priorización: DMU + omisiones. Validado con χ²=471.02, p=1.93×10⁻¹⁰⁴.",
                    [FIG_M["h12a"], FIG_M["h12b"]]),
])


# ---------- INSIGHTS ----------
def insight_card(titulo, accion, contenido_html):
    return html.Div(className="dash-section", children=[
        html.Div(className="insight-header", children=[
            html.H2(titulo),
            html.Div(className="insight-accion", children=[
                html.Span("Acción clave: ", style={"color": C["yellow"], "fontWeight": "bold"}),
                html.Span(accion, style={"color": C["grey"]}),
            ]),
        ]),
        contenido_html,
    ])


insights = html.Section(className="section dashboard-sec", children=[
    html.H2("Insights accionables — Presentación CNHMX"),
    html.P("Tres hallazgos validados estadísticamente con impacto directo en monetización after-market.",
           className="subtitle"),

    insight_card(
        "Insight A — Concentración de riesgo en distribuidores específicos",
        "Dashboard semanal para TRACSAGRAL, ATN y MADISAGRAL con equipos en ventana crítica. +3% margen en refacciones por OT generada desde alerta predictiva.",
        html.Div(children=[
            html.Div(className="charts-row", children=[
                html.Div(dcc.Graph(figure=FIG_I["i1"], config=CFG), className="chart-card"),
                html.Div(dcc.Graph(figure=FIG_I["i2"], config=CFG), className="chart-card"),
            ]),
            html.Div(className="charts-row", children=[
                html.Div(dcc.Graph(figure=FIG_I["i3"], config=CFG), className="chart-card"),
                html.Div(dcc.Graph(figure=FIG_I["i4"], config=CFG), className="chart-card"),
            ]),
        ])
    ),

    insight_card(
        "Insight B — El primer servicio es un filtro de abandono, no una señal de riesgo",
        "Cláusula en contrato de garantía: servicio de 50 hrs dentro de los 60 días post-venta. Automatización de OT a los 30 días en Telematrix. Incentivo de $500 MXN al vendedor.",
        html.Div(children=[
            html.Div(className="charts-row", children=[
                html.Div(dcc.Graph(figure=FIG_I["i5"], config=CFG), className="chart-card"),
                html.Div(dcc.Graph(figure=FIG_I["i6"], config=CFG), className="chart-card"),
            ]),
        ])
    ),

    insight_card(
        "Insight C — DOE como segmentador: umbrales diferenciados por tipo de equipo",
        "Configurar en Telematrix: alerta a 250 hrs para construcción y 500 hrs para agrícola. 35.8% de equipos de construcción y 9.1% de agrícolas ya superaron su umbral.",
        html.Div(children=[
            html.Div(className="charts-row", children=[
                html.Div(dcc.Graph(figure=FIG_I["i7"], config=CFG), className="chart-card"),
                html.Div(dcc.Graph(figure=FIG_I["i8"], config=CFG), className="chart-card"),
            ]),
            html.Div(className="charts-row", children=[
                html.Div(dcc.Graph(figure=FIG_I["i9"], config=CFG), className="chart-card"),
                html.Div(dcc.Graph(figure=FIG_I["i10"], config=CFG), className="chart-card"),
            ]),
        ])
    ),

    html.Div(className="dash-section", children=[
        html.H2("Urgencia geográfica — todos los estados"),
        html.P("Priorización por estado combinando exigencia operativa, desfase promedio y variabilidad.",
               className="subtitle"),
        html.Div(className="charts-row", children=[
            html.Div(dcc.Graph(figure=FIG_I["i11"], config=CFG),
                     className="chart-card", style={"flex": "1 1 100%"})
        ]),
    ]),
])


# ---------- CONTACTO ----------
cta = html.Section(className="section cta-final", children=[
    html.H2("Transformando datos operativos en decisiones estratégicas para CNH Industrial"),
    html.P("Una propuesta analítica para priorizar equipos, anticipar riesgos y fortalecer la "
           "monetización aftermarket.", className="subtitle"),
    html.Div(className="hero-btns center", children=[
        dcc.Link("Ver dashboard",    href="/dashboard",   className="btn btn-primary"),
        dcc.Link("Ver indicadores",  href="/indicadores", className="btn btn-ghost"),
        dcc.Link("Inicio",           href="/",            className="btn btn-ghost"),
    ]),
])


# ---------- FOOTER ----------
footer = html.Footer(className="footer", children=[
    html.Div(className="footer-grid", children=[
        html.Div([html.H4("CNH Industrial"), html.P("Case IH"), html.P("New Holland")]),
        html.Div([html.H4("Proyecto"), html.P("CNHMX Fleet Analytics"),
                  html.P("Proyecto académico profesional"),
                  html.P("Análisis EDA de la flota agrícola")]),
        html.Div([html.H4("Alcance"),
                  html.P("Estado de la flota, mantenimiento y tendencia histórica de uso")]),
        html.Div([html.H4("Equipo CNH 4"),
                  html.P("Jezrel Hernandez Alvarado"),
                  html.P("George Patricio Espinosa Perez"),
                  html.P("Maria Fernanda San Roman Orozco")]),
    ]),
    html.Hr(),
    html.Div(className="footer-bottom", children=[
        html.Span("© 2026 CNHMX Fleet Analytics · CNH Industrial · Case IH · New Holland"),
        html.Span("Proyecto académico profesional"),
    ]),
])


# ---------- PAGINAS ----------
PAGINAS = {
    "/":           html.Div(className="page", children=[hero]),
    "/indicadores":html.Div(className="page", children=[indicadores]),
    "/dashboard":  html.Div(className="page", children=[dashboard]),
    "/modelos":    html.Div(className="page", children=[modelos]),
    "/insights":   html.Div(className="page", children=[insights]),
    "/contacto":   html.Div(className="page", children=[cta]),
}

app.layout = html.Div(className="root", children=[
    dcc.Location(id="url", refresh=False),
    navbar,
    html.Div(id="page-content"),
    footer,
])


# ============================================================================
# CALLBACKS
# ============================================================================
@app.callback(Output("page-content", "children"), Input("url", "pathname"))
def router(pathname):
    return PAGINAS.get(pathname, PAGINAS["/"])


@app.callback(
    Output({"type": "navlink", "index": ALL}, "className"),
    Input("url", "pathname"),
    State({"type": "navlink", "index": ALL}, "id"),
)
def nav_activo(pathname, ids):
    out = []
    for d in ids:
        idx  = d["index"]
        base = "nav-link nav-cta" if idx == "cta" else "nav-link"
        if idx == pathname or (idx == "cta" and pathname == "/dashboard"):
            base += " nav-active"
        out.append(base)
    return out


@app.callback(
    Output("fig1","figure"), Output("fig2","figure"),
    Output("fig3","figure"), Output("fig4","figure"),
    Input("f_marca_s1","value"),
    Input("f_estado_s1","value"),
    Input("f_dist_s1","value"),
    Input("f_horo_s1","value"),
)
def upd_s1(marcas, estados, distribuidores, rango):
    d = filtra_s1(df_eq.copy(), marcas, estados, rango)
    if distribuidores:
        d = d[d["distribuidor"].isin(distribuidores)]
    return g1_marca(d), g2_horometro_marca(d), g3_antiguedad(d), g4_mapa(d)


@app.callback(
    Output("dash-kpi-total",    "children"),
    Output("dash-kpi-con-serv", "children"),
    Output("dash-kpi-sin-serv", "children"),
    Output("dash-kpi-ot-cerr",  "children"),
    Output("dash-kpi-ot-pend",  "children"),
    Output("dash-kpi-ma-perd",  "children"),
    Output("dash-kpi-tasa50",   "children"),
    Output("dash-kpi-dmu30",    "children"),
    Output("dash-kpi-int-prom", "children"),
    Input("f_marca_s1", "value"),
    Input("f_estado_s1", "value"),
    Input("f_dist_s1", "value"),
    Input("f_horo_s1", "value"),
)
def upd_dashboard_kpis(marcas, estados, distribuidores, rango):
    if rango is None:
        rango = [0, HORO_MAX]
    d = filtra_s1(df_eq.copy(), marcas, estados, rango)
    if distribuidores:
        d = d[d["distribuidor"].isin(distribuidores)]
    if d.empty:
        return ["—"] * 9
    total    = d["no._serie"].nunique()
    con_serv = int((pd.to_numeric(d["total_servicios"], errors="coerce").fillna(0) > 0).sum())
    sin_serv = int((pd.to_numeric(d["total_servicios"], errors="coerce").fillna(0) == 0).sum())
    ot_cerr  = int(pd.to_numeric(d["cerrados"],  errors="coerce").fillna(0).sum())
    ot_pend  = int(pd.to_numeric(d["pendientes"],errors="coerce").fillna(0).sum())
    equipos_sel = set(d["no._serie"].dropna().astype(str))
    dp = df_presc[df_presc["no._serie"].astype(str).isin(equipos_sel)].drop_duplicates("no._serie")
    ma_perd  = pd.to_numeric(dp["MA_Potencial_Perdido"], errors="coerce").fillna(0).sum() if "MA_Potencial_Perdido" in dp.columns else 0
    dmu_crit = int((pd.to_numeric(dp["DMU_Actual"], errors="coerce") > 30).sum()) if "DMU_Actual" in dp.columns else 0
    tasa50   = d["50"].isin(["CERRADA","CERRADAFUERA"]).mean() * 100
    ivs      = [iv for iv in intervalos if iv in d.columns]
    int_prom = sum(d[iv].isin(["CERRADA","CERRADAFUERA"]).astype(int) for iv in ivs).mean() if len(d) else 0
    return (f"{total:,}", f"{con_serv:,}", f"{sin_serv:,}", f"{ot_cerr:,}", f"{ot_pend:,}",
            _fmt(float(ma_perd)), f"{tasa50:.1f}%", f"{dmu_crit:,}", f"{int_prom:.2f}")


@app.callback(
    Output("fig5","figure"), Output("fig6","figure"),
    Output("fig7","figure"), Output("fig8","figure"),
    Input("f_dist_s2","value"), Input("f_estado_s2","value"),
)
def upd_s2(distribuidores, estados):
    d_eq   = df_eq.copy()
    d_full = df.copy()
    if distribuidores:
        d_eq   = d_eq[d_eq["distribuidor"].isin(distribuidores)]
        d_full = d_full[d_full["distribuidor"].isin(distribuidores)]
    if estados:
        d_eq   = d_eq[d_eq["estado"].isin(estados)]
        d_full = d_full[d_full["estado"].isin(estados)]
    return g5_cobertura(d_eq), g6_completados(d_eq), g7_prom_dist(d_eq), g8_estatus(d_full)


@app.callback(
    Output("fig9","figure"), Output("fig10","figure"),
    Input("f_dist_s3","value"), Input("f_marca_s3","value"),
)
def upd_s3(distribuidores, marcas):
    d = df_eq.copy()
    if distribuidores: d = d[d["distribuidor"].isin(distribuidores)]
    if marcas:         d = d[d["marca"].isin(marcas)]
    return g9_anual(d), g10_anual_dist(d)


@app.callback(
    Output("kpi-total-eq",   "children"),
    Output("kpi-con-serv",   "children"),
    Output("kpi-sin-serv",   "children"),
    Output("kpi-cerradas",   "children"),
    Output("kpi-pendientes", "children"),
    Output("kpi-tasa50",     "children"),
    Output("kpi-int-prom",   "children"),
    Input("url", "pathname"),
    Input("f_marca_ind",  "value"),
    Input("f_estado_ind", "value"),
    Input("f_horo_ind",   "value"),
)
def upd_kpis_ind(pathname, marcas, estados, rango):
    if rango is None:
        rango = [0, HORO_MAX]
    d = df_eq.copy()
    if marcas:  d = d[d["marca"].isin(marcas)]
    if estados: d = d[d["estado"].isin(estados)]
    d = d[(d["horometro"] >= rango[0]) & (d["horometro"] <= rango[1])]
    if d.empty: return ["—"] * 7
    total    = f"{d['no._serie'].nunique():,}"
    con_s    = f"{(d['total_servicios'] > 0).sum():,}"
    sin_s    = f"{(d['total_servicios'] == 0).sum():,}"
    cerr     = f"{int(pd.to_numeric(d['cerrados'], errors='coerce').sum()):,}"
    pend     = f"{int(pd.to_numeric(d['pendientes'], errors='coerce').sum()):,}"
    tasa50   = f"{d['50'].isin(['CERRADA','CERRADAFUERA']).sum() / len(d) * 100:.1f}%"
    int_ivs  = [iv for iv in intervalos if iv in d.columns]
    int_prom = f"{sum(d[iv].isin(['CERRADA','CERRADAFUERA']).astype(int) for iv in int_ivs).mean():.2f}"
    return total, con_s, sin_s, cerr, pend, tasa50, int_prom


@app.callback(
    Output("kpi-riesgo-incump","children"),
    Output("kpi-riesgo-fuga",  "children"),
    Output("kpi-ots-rec",      "children"),
    Output("kpi-desfase-crit", "children"),
    Output("kpi-ma-rec",       "children"),
    Output("kpi-ma-perd",      "children"),
    Input("url", "pathname"),
    Input("f_dist_mod",  "value"),
    Input("f_estado_mod","value"),
    Input("f_seg_mod",   "value"),
)
def upd_kpis_mod(pathname, distribuidores, estados, segmentos):
    dp = df_presc.copy()
    if distribuidores: dp = dp[dp["distribuidor"].isin(distribuidores)]
    if estados:        dp = dp[dp["estado"].isin(estados)]
    if segmentos:      dp = dp[dp["Segmento"].isin(segmentos)]
    dh = df_h1.copy()
    if distribuidores: dh = dh[dh["distribuidor"].isin(distribuidores)]
    if estados:        dh = dh[dh["estado"].isin(estados)]
    if segmentos:      dh = dh[dh["Segmento"].isin(segmentos)]
    ds = df_surv_k.copy()
    if distribuidores: ds = ds[ds["distribuidor"].isin(distribuidores)]
    if estados:        ds = ds[ds["estado"].isin(estados)]
    if segmentos:      ds = ds[ds["Segmento"].isin(segmentos)]
    if dp.empty: return ["—"] * 6
    riesgo_inc  = (f"{int((dh['Probabilidad_Incumplimiento_900hrs'] >= 0.5).sum()):,}"
                   if not dh.empty and "Probabilidad_Incumplimiento_900hrs" in dh.columns else "—")
    riesgo_fuga = f"{int(ds['Evento_Fuga'].sum()):,}" if not ds.empty else "—"
    n_top       = max(1, int(len(dp) * 0.20))
    ots_rec     = (f"{int(dp.nsmallest(n_top,'Rank_Score')['Exito_OT'].sum()):,}"
                   if "Rank_Score" in dp.columns else "—")
    dp_uniq     = dp.drop_duplicates("no._serie")
    desfase     = (f"{int((dp_uniq['DMU_Actual'] > 30).sum()):,}"
                   if "DMU_Actual" in dp_uniq.columns else "—")
    intervalos_num = [50,300,600,900,1200,1500,1800,2100,2400]
    rec, perd = 0, 0
    for _, row in dp_uniq.iterrows():
        horo = row.get("horometro", 0)
        for iv in intervalos_num:
            col = str(iv)
            if col not in row.index: continue
            if row[col] in ["PENDIENTE","PORVENCER"]:
                if iv >= horo: rec  += iv
                else:          perd += iv
    def fmt(n):
        return (f"{n/1_000_000:.1f}M" if n >= 1_000_000 else
                f"{n/1_000:.0f}k"     if n >= 10_000    else f"{n:,}")
    return riesgo_inc, riesgo_fuga, ots_rec, desfase, fmt(rec), fmt(perd)


if __name__ == "__main__":
    app.run(debug=True)
