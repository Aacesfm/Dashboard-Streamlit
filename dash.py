"""Benchmark de pensiones AFORE: Banamex frente a otras AFOREs.

Ejecutar:  .venv/bin/streamlit run dash.py
Compatible con Python 3.8.8 (versiones fijadas en requirements.txt).
"""
from __future__ import annotations

import os
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Sequence, Tuple

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

PAGE_TITLE = "Benchmark de pensiones AFORE"
st.set_page_config(page_title=PAGE_TITLE, layout="wide", initial_sidebar_state="expanded")

# =============================================================================
# 1. CONFIGURACIÓN: rutas, columnas, etiquetas, colores y umbrales
# =============================================================================
BASE_DIR = Path(__file__).resolve().parent
DATA_PATH = Path(os.environ.get("AFORES_CSV_PATH", str(BASE_DIR / "Input" / "RESULTADOS_CONSOLIDADOS_7_AFORES.csv")))
CSV_ENCODING = "utf-8-sig"
DEFAULT_BASE_AFORE = "Banamex"
EQUAL_TOLERANCE = 0.005  # diferencias menores a medio centavo (o 0.005 pp) cuentan como iguales
SALARY_STEP = 500

# Paleta Banamex
RED, BLUE, TEXT, GRID = "#FF1B44", "#003746", "#001E22", "#DAE9EE"
FONT_FAMILY = "Helvetica Neue, Helvetica, Arial, sans-serif"

AFORE_ORDER = ["Banamex", "XXI Banorte", "Coppel", "SURA", "Profuturo", "Invercap", "Principal"]
AFORE_COLORS = {
    "Banamex": RED,
    "XXI Banorte": BLUE,
    "Coppel": "#009CC6",
    "SURA": "#B18DFB",
    "Profuturo": "#FA8D5A",
    "Invercap": "#00AD59",
    "Principal": "#601636",
}
EXTRA_COLORS = ["#B77493", "#A0D6E2", "#005162", "#2DDC8E"]  # AFOREs que no estén en AFORE_COLORS

REGIMEN_LABELS = {"IMSS73": "IMSS Ley 73", "IMSS97": "IMSS Ley 97", "ISSSTE": "ISSSTE"}
REGIMEN_ORDER = list(REGIMEN_LABELS)
REGIMEN_COLORS = {"IMSS Ley 73": "#005162", "IMSS Ley 97": "#B77493", "ISSSTE": "#A0D6E2"}

ESCENARIO_LABELS = {
    "IMSS73_PROYECCION": "Ley 73 · Proyección",
    "IMSS73_DERECHO_PENSION": "Ley 73 · Derecho a pensión",
    "IMSS73_GARANTIZADA": "Ley 73 · Pensión garantizada",
    "IMSS73_NEGATIVA_PENSION": "Ley 73 · Negativa de pensión",
    "IMSS97_PROYECCION": "Ley 97 · Proyección",
    "IMSS97_NEGATIVA_PENSION": "Ley 97 · Negativa de pensión",
    "ISSSTE_PROYECCION": "ISSSTE · Proyección",
    "ISSSTE_PENSION_GARANTIZADA": "ISSSTE · Pensión garantizada",
    "ISSSTE_NEGATIVA_PENSION": "ISSSTE · Negativa de pensión",
    "ISSSTE_RECURSOS_PROPIOS": "ISSSTE · Recursos propios",
}
MODALIDAD_LABELS = {
    "RETIRO_PROGRAMADO_HIPOTETICO": "Retiro programado",
    "RENTA_VITALICIA_HIPOTETICA": "Renta vitalicia",
    "PENSION_LEY_73_HIPOTETICA": "Pensión Ley 73",
    "NEGATIVA_HIPOTETICA_NO_DICTAMEN": "Negativa de pensión",
}
GENERO_LABELS = {"H": "Hombre", "M": "Mujer"}

NEGATIVA_SUFFIX = "_NEGATIVA_PENSION"
NEGATIVA_MODALIDAD = "NEGATIVA_HIPOTETICA_NO_DICTAMEN"
RESULT_CON_PENSION, RESULT_NEGATIVA = "Con pensión", "Negativa de pensión"
RESULT_COLORS = {RESULT_CON_PENSION: BLUE, RESULT_NEGATIVA: "#FA8D5A"}

SEMANAS_BINS = [0, 250, 500, 750, 1000, 1250, 1500, float("inf")]
SEMANAS_LABELS = ["0–249", "250–499", "500–749", "750–999", "1,000–1,249", "1,250–1,499", "1,500+"]

SENTIDO_ORDER = ["Mayor que la base", "Igual a la base", "Menor que la base"]
SENTIDO_COLORS = {SENTIDO_ORDER[0]: BLUE, SENTIDO_ORDER[1]: "#A0D6E2", SENTIDO_ORDER[2]: "#FA8D5A"}

# Columna del CSV -> nombre interno. Las qa_* solo alimentan los controles de calidad.
COLUMN_MAP = {
    "AFORE": "afore",
    "REGIMEN": "regimen",
    "id_cliente": "id_cliente",
    "age": "edad",
    "genero": "genero",
    "anios_cotizados": "anios_cot",
    "sem_cot": "semanas_cot",
    "salario_mensual": "salario",
    "saldo_av": "saldo_av",
    "av_mensual": "av_mensual",
    "escenario_estimado": "escenario",
    "Pension_web": "pension",
    "pension_con_av_web": "pension_con_av",
    "pension_edad_mas_1_web": "pension_mas1",
    "pension_edad_mas_2_web": "pension_mas2",
    "edad_retiro_calculo": "edad_retiro",
    "tasa_remplazo_web": "tasa_reemplazo",
    "tasa_rendimiento_web": "tasa_rendimiento",
    "densidad_cot_web": "densidad_cot",
    "saldo_inicial_capturado": "saldo_inicial",
    "saldo_acumulado_web": "saldo_proy",
    "saldo_acumulado_con_av_web": "saldo_proy_con_av",
    "modalidad_web": "modalidad",
    "estado": "estado",
    "saldo_total_web": "qa_saldo_total",
    "saldo_total_con_av_mensual_web": "qa_saldo_total_con_av",
    "disposicion_recursos_web": "qa_disposicion",
}
TEXT_COLS = ["afore", "regimen", "genero", "escenario", "modalidad", "estado"]
NUMERIC_COLS = [
    "edad", "anios_cot", "semanas_cot", "salario", "saldo_av", "av_mensual", "pension", "pension_con_av",
    "pension_mas1", "pension_mas2", "edad_retiro", "tasa_reemplazo", "tasa_rendimiento", "densidad_cot",
    "saldo_inicial", "saldo_proy", "saldo_proy_con_av", "qa_saldo_total", "qa_saldo_total_con_av", "qa_disposicion",
]
MASKED_COLS = ["pension", "pension_con_av", "pension_mas1", "pension_mas2", "tasa_reemplazo"]
PROFILE_COLS = ["regimen", "edad", "genero", "semanas_cot", "salario", "saldo_av", "av_mensual", "escenario"]

# =============================================================================
# 2. FORMATOS, ETIQUETAS Y COLORES
# =============================================================================
CSS = f"""
<style>
h1, h2, h3, h4 {{ color: {BLUE}; }}
[data-testid="stDecoration"] {{ background: {RED}; }}
.brand-bar {{ width: 72px; height: 4px; background: {RED}; border-radius: 2px; margin: 0 0 0.75rem 0; }}
</style>
"""


def fmt_mxn(v: float, decimals: int = 0, signed: bool = False) -> str:
    if pd.isna(v):
        return "—"
    sign = "-" if v < 0 else ("+" if signed else "")
    return f"{sign}${abs(v):,.{decimals}f}"


def fmt_pct(v: float, decimals: int = 1, signed: bool = False) -> str:
    if pd.isna(v):
        return "—"
    return f"{v:+,.{decimals}f}%" if signed else f"{v:,.{decimals}f}%"


def fmt_pp(v: float, decimals: int = 1) -> str:
    return "—" if pd.isna(v) else f"{v:+,.{decimals}f} pp"


def fmt_int(v: float) -> str:
    return "—" if pd.isna(v) else f"{int(v):,}"


def order_list(values: Sequence, order: Sequence) -> List:
    """Valores únicos siguiendo `order`; los no previstos van al final, ordenados."""
    present = list(dict.fromkeys(v for v in values if pd.notna(v)))
    return [v for v in order if v in present] + sorted(v for v in present if v not in order)


def regimen_label(code: str) -> str:
    return REGIMEN_LABELS.get(code, code)


def escenario_label(code: str) -> str:
    return ESCENARIO_LABELS.get(code, str(code).replace("_", " ").capitalize())


def genero_label(code: str) -> str:
    return GENERO_LABELS.get(code, code)


def afore_color(name: str) -> str:
    return AFORE_COLORS.get(name) or EXTRA_COLORS[sum(map(ord, str(name))) % len(EXTRA_COLORS)]


def color_map(names: Sequence[str]) -> Dict[str, str]:
    return {n: afore_color(n) for n in names}


def style_fig(fig: go.Figure, title: Optional[str] = None, height: int = 380, legend: bool = True) -> go.Figure:
    fig.update_layout(
        template="plotly_white",
        height=height,
        showlegend=legend,
        title=dict(text=title, x=0, xanchor="left", y=0.98, yanchor="top", yref="container", font=dict(size=15, color=BLUE)) if title else None,
        font=dict(family=FONT_FAMILY, size=12, color=TEXT),
        margin=dict(l=8, r=8, t=(104 if legend else 52) if title else 28, b=8),
        legend=dict(orientation="h", yanchor="bottom", y=1.0, xanchor="left", x=0, title_text=""),
        paper_bgcolor="white",
        plot_bgcolor="white",
    )
    fig.update_xaxes(gridcolor=GRID, linecolor=GRID, zerolinecolor=GRID)
    fig.update_yaxes(gridcolor=GRID, linecolor=GRID, zerolinecolor=GRID)
    return fig


# =============================================================================
# 3. CARGA, VALIDACIÓN Y CONTROLES DE CALIDAD
# =============================================================================
class DataError(ValueError):
    """El CSV no cumple el contrato de datos esperado."""


def _status(ok: bool) -> str:
    return "Correcto" if ok else "Revisar"


def _quality_report(df: pd.DataFrame, invalid_total: int, incoherentes: int) -> List[Dict[str, str]]:
    rows: List[Dict[str, str]] = []

    def add(check: str, result: str, status: str) -> None:
        rows.append({"Verificación": check, "Resultado": result, "Estado": status})

    n_afores = df["afore"].nunique()
    add("Filas, perfiles y AFOREs leídos", f"{len(df):,} filas · {df['id_cliente'].nunique():,} perfiles · {n_afores} AFOREs", "Informativo")
    add("Valores no numéricos convertidos a nulo", f"{invalid_total:,}", _status(invalid_total == 0))
    duplicados = int(df.duplicated(["afore", "id_cliente"]).sum())
    add("Duplicados (AFORE + id_cliente)", f"{duplicados:,}", _status(duplicados == 0))
    por_perfil = df.groupby("id_cliente")["afore"].nunique()
    completos = int((por_perfil == n_afores).sum())
    add("Perfiles presentes en todas las AFOREs", f"{completos:,} de {len(por_perfil):,}", _status(completos == len(por_perfil)))
    distintos = int((df.groupby("id_cliente")[PROFILE_COLS].nunique(dropna=False) > 1).any(axis=1).sum())
    add("Perfiles con datos de entrada distintos entre AFOREs", f"{distintos:,}", _status(distintos == 0))
    add("Negativa de pensión = pensión 0 = modalidad negativa", f"{incoherentes:,} filas incoherentes", _status(incoherentes == 0))
    max_dif = (100 * df["pension"] / df["salario"] - df["tasa_reemplazo"]).abs().max()
    add("Tasa de reemplazo vs 100 × pensión / salario", "—" if pd.isna(max_dif) else f"Diferencia máxima {max_dif:.3f} pp", _status(pd.isna(max_dif) or max_dif <= 0.01))
    una_tasa = bool((df.groupby("afore")["tasa_rendimiento"].nunique() == 1).all())
    add("Tasa de rendimiento por AFORE", "Un solo valor por AFORE" if una_tasa else "Varía dentro de una AFORE", "Informativo")
    iguales = 100 * df["saldo_proy"].eq(df["qa_saldo_total"]).mean()
    iguales_av = 100 * df["saldo_proy_con_av"].eq(df["qa_saldo_total_con_av"]).mean()
    add("saldo_acumulado_web = saldo_total_web", f"{iguales:.1f}% de las filas (se usa saldo_acumulado_web)", "Informativo")
    add("saldo_acumulado_con_av_web = saldo_total_con_av_mensual_web", f"{iguales_av:.1f}% de las filas", "Informativo")
    add("disposicion_recursos_web vacía", f"{100 * df['qa_disposicion'].isna().mean():.1f}% de nulos (no se utiliza)", "Informativo")
    return rows


@st.cache_data(show_spinner="Cargando datos...")
def load_data(path_str: str, mtime: float) -> Tuple[pd.DataFrame, List[Dict[str, str]]]:
    # mtime solo invalida la caché cuando cambia el archivo
    path = Path(path_str)
    header = pd.read_csv(path, nrows=0, encoding=CSV_ENCODING).columns
    missing = [c for c in COLUMN_MAP if c not in header]
    if missing:
        raise DataError("Faltan columnas requeridas en el CSV: " + ", ".join(missing))

    df = pd.read_csv(path, usecols=list(COLUMN_MAP), encoding=CSV_ENCODING, dtype={"id_cliente": str}).rename(columns=COLUMN_MAP)
    if df.empty:
        raise DataError("El CSV no contiene filas.")

    for col in TEXT_COLS:
        df[col] = df[col].str.strip()
    invalid_total = 0
    for col in NUMERIC_COLS:
        nulls_before = int(df[col].isna().sum())
        df[col] = pd.to_numeric(df[col], errors="coerce")
        invalid_total += int(df[col].isna().sum()) - nulls_before

    df["regimen_label"] = df["regimen"].map(REGIMEN_LABELS).fillna(df["regimen"])
    df["escenario_label"] = df["escenario"].map(escenario_label)
    df["modalidad_label"] = df["modalidad"].map(MODALIDAD_LABELS).fillna(df["modalidad"])
    df["genero_label"] = df["genero"].map(GENERO_LABELS).fillna(df["genero"])
    df["es_negativa"] = df["escenario"].fillna("").str.endswith(NEGATIVA_SUFFIX)
    df["resultado"] = np.where(df["es_negativa"], RESULT_NEGATIVA, RESULT_CON_PENSION)
    df["tiene_av"] = (df["saldo_av"] > 0) | (df["av_mensual"] > 0)
    df["rango_semanas"] = pd.cut(df["semanas_cot"], bins=SEMANAS_BINS, labels=SEMANAS_LABELS, right=False).astype(object)

    incoherentes = int(((df["pension"].eq(0) != df["es_negativa"]) | (df["modalidad"].eq(NEGATIVA_MODALIDAD) != df["es_negativa"])).sum())
    # Una negativa no es una pensión de 0 MXN: queda sin valor y fuera de los promedios
    for col in MASKED_COLS:
        df[col] = df[col].mask(df["es_negativa"])

    quality = _quality_report(df, invalid_total, incoherentes)
    return df.drop(columns=[c for c in df.columns if c.startswith("qa_")]), quality


# =============================================================================
# 4. FILTROS GLOBALES (barra lateral). Sin selección = todos los valores.
# =============================================================================
AV_OPTIONS = ["Todos", "Con ahorro voluntario", "Sin ahorro voluntario"]
RESULT_OPTIONS = ["Todos", RESULT_CON_PENSION, RESULT_NEGATIVA]
REGIMEN_LABEL_ORDER = [REGIMEN_LABELS[r] for r in REGIMEN_ORDER]


def sidebar_filters(df_all: pd.DataFrame) -> Tuple[pd.DataFrame, List[str]]:
    """Dibuja los filtros y devuelve los datos filtrados con la lista de filtros activos."""
    ss = st.session_state
    version = ss.setdefault("filters_version", 0)  # cambiar la versión recrea los widgets con sus valores iniciales

    def reset_filters() -> None:
        ss["filters_version"] += 1

    afores = order_list(df_all["afore"], AFORE_ORDER)
    regimenes = order_list(df_all["regimen"], REGIMEN_ORDER)
    generos = order_list(df_all["genero"], list(GENERO_LABELS))
    edad_bounds = (int(df_all["edad"].min()), int(df_all["edad"].max()))
    sal_bounds = (
        int(np.floor(df_all["salario"].min() / SALARY_STEP) * SALARY_STEP),
        int(np.ceil(df_all["salario"].max() / SALARY_STEP) * SALARY_STEP),
    )
    pares = df_all[["regimen", "escenario"]].drop_duplicates()

    with st.sidebar:
        st.markdown("### Filtros")
        st.caption("Sin selección se incluyen todos los valores.")
        st.button("Restablecer filtros", on_click=reset_filters, use_container_width=True)
        afore_sel = st.multiselect("AFORE", afores, key=f"f_afore_{version}", placeholder="Todas")
        regimen_sel = st.multiselect("Régimen", regimenes, format_func=regimen_label, key=f"f_regimen_{version}", placeholder="Todos")
        esc_options = order_list(pares.loc[pares["regimen"].isin(regimen_sel or regimenes), "escenario"], list(ESCENARIO_LABELS))
        escenario_sel = st.multiselect(
            "Escenario estimado", esc_options, format_func=escenario_label, key=f"f_escenario_{version}",
            placeholder="Todos", help="Las opciones dependen del régimen seleccionado.",
        )
        edad_sel = st.slider("Edad (años)", edad_bounds[0], edad_bounds[1], value=edad_bounds, key=f"f_edad_{version}")
        salario_sel = st.slider(
            "Salario mensual (MXN)", sal_bounds[0], sal_bounds[1], value=sal_bounds, step=SALARY_STEP,
            format="$%d", key=f"f_salario_{version}",
        )
        genero_sel = st.multiselect("Género", generos, format_func=genero_label, key=f"f_genero_{version}", placeholder="Todos")
        av_sel = st.radio("Ahorro voluntario", AV_OPTIONS, key=f"f_av_{version}", help="Con AV: saldo_av > 0 o av_mensual > 0.")
        resultado_sel = st.radio("Resultado de pensión", RESULT_OPTIONS, key=f"f_resultado_{version}")

    mask = pd.Series(True, index=df_all.index)
    active: List[str] = []
    if afore_sel:
        mask &= df_all["afore"].isin(afore_sel)
        active.append("AFORE: " + ", ".join(afore_sel))
    if regimen_sel:
        mask &= df_all["regimen"].isin(regimen_sel)
        active.append("Régimen: " + ", ".join(regimen_label(r) for r in regimen_sel))
    if escenario_sel:
        mask &= df_all["escenario"].isin(escenario_sel)
        active.append(f"Escenario: {len(escenario_sel)} seleccionados")
    if tuple(edad_sel) != edad_bounds:
        mask &= df_all["edad"].between(*edad_sel)
        active.append(f"Edad: {edad_sel[0]}–{edad_sel[1]}")
    if tuple(salario_sel) != sal_bounds:
        mask &= df_all["salario"].between(*salario_sel)
        active.append(f"Salario: {fmt_mxn(salario_sel[0])}–{fmt_mxn(salario_sel[1])}")
    if genero_sel:
        mask &= df_all["genero"].isin(genero_sel)
        active.append("Género: " + ", ".join(genero_label(g) for g in genero_sel))
    if av_sel != AV_OPTIONS[0]:
        mask &= df_all["tiene_av"] if av_sel == AV_OPTIONS[1] else ~df_all["tiene_av"]
        active.append(av_sel)
    if resultado_sel != RESULT_OPTIONS[0]:
        mask &= df_all["es_negativa"] if resultado_sel == RESULT_NEGATIVA else ~df_all["es_negativa"]
        active.append(resultado_sel)
    return df_all[mask], active


def resolve_base(afores: Sequence[str]) -> str:
    wanted = st.session_state.get("base_afore", DEFAULT_BASE_AFORE)
    return wanted if wanted in afores else afores[0]


# =============================================================================
# 5. MÉTRICAS: comparaciones pareadas contra la AFORE base
# =============================================================================
PAIR_COLS = ["afore", "id_cliente", "regimen", "regimen_label", "escenario", "escenario_label"]


def paired_differences(df: pd.DataFrame, base: str, value_col: str) -> pd.DataFrame:
    """Una fila por (AFORE comparada, perfil): comparada − base. Sin dato en alguna AFORE, la diferencia queda nula."""
    base_df = df.loc[df["afore"] == base, ["id_cliente", value_col]].rename(columns={value_col: "valor_base"})
    others = df.loc[df["afore"] != base, PAIR_COLS + [value_col]].rename(columns={value_col: "valor"})
    try:
        pares = others.merge(base_df, on="id_cliente", how="inner", validate="many_to_one")
    except pd.errors.MergeError:
        raise DataError("La AFORE base tiene perfiles duplicados; revisa la sección de calidad de datos.")
    pares["dif"] = pares["valor"] - pares["valor_base"]
    pares["dif_pct"] = np.where(pares["valor_base"] > 0, pares["dif"] / pares["valor_base"] * 100, np.nan)
    pares["sentido"] = np.select(
        [pares["dif"].abs() < EQUAL_TOLERANCE, pares["dif"] > 0],
        [SENTIDO_ORDER[1], SENTIDO_ORDER[0]],
        default=SENTIDO_ORDER[2],
    )
    pares.loc[pares["dif"].isna(), "sentido"] = np.nan
    return pares


def summarize_pairs(pares: pd.DataFrame) -> pd.DataFrame:
    valid = pares.dropna(subset=["dif"])
    if valid.empty:
        return pd.DataFrame()
    out = valid.groupby("afore").agg(
        comparaciones=("dif", "size"),
        dif_media=("dif", "mean"),
        dif_pct_media=("dif_pct", "mean"),
        dif_pct_mediana=("dif_pct", "median"),
    )
    shares = pd.crosstab(valid["afore"], valid["sentido"], normalize="index").mul(100).reindex(columns=SENTIDO_ORDER, fill_value=0.0)
    return out.join(shares).reindex(order_list(out.index, AFORE_ORDER)).rename_axis("afore").reset_index()


# =============================================================================
# 6. GRÁFICAS (todas devuelven None cuando no hay datos que mostrar)
# =============================================================================
def grouped_bar(df: pd.DataFrame, value_col: str, title: str, y_title: str, money: bool = True) -> Optional[go.Figure]:
    """Media de `value_col` por régimen y AFORE."""
    g = df.groupby(["regimen_label", "afore"], as_index=False)[value_col].mean().dropna(subset=[value_col])
    if g.empty:
        return None
    fig = px.bar(
        g, x="regimen_label", y=value_col, color="afore", barmode="group", text=g[value_col].map(fmt_mxn if money else fmt_pct),
        color_discrete_map=color_map(g["afore"].unique()),
        category_orders={"afore": order_list(g["afore"], AFORE_ORDER), "regimen_label": REGIMEN_LABEL_ORDER},
        labels={"afore": "AFORE", "regimen_label": "Régimen", value_col: y_title},
    )
    fig.update_traces(textposition="outside", textangle=-90, cliponaxis=False, textfont=dict(size=10))
    fig.update_xaxes(title=None)
    fig.update_yaxes(title=y_title, rangemode="tozero", **(dict(tickprefix="$", tickformat=",.0f") if money else dict(ticksuffix="%")))
    return style_fig(fig, title)


def diff_bar(summary: pd.DataFrame, title: str, y_title: str) -> Optional[go.Figure]:
    if summary.empty:
        return None
    s = summary.dropna(subset=["dif_pct_media"]).sort_values("dif_pct_media", ascending=False)
    if s.empty:
        return None
    fig = px.bar(
        s, x="afore", y="dif_pct_media", color="afore", text=s["dif_pct_media"].map(lambda v: fmt_pct(v, 2, signed=True)),
        color_discrete_map=color_map(s["afore"]), labels={"afore": "AFORE", "dif_pct_media": y_title},
    )
    fig.add_hline(y=0, line_width=1, line_color=TEXT)
    fig.update_traces(textposition="outside", cliponaxis=False)
    fig.update_xaxes(title=None)
    fig.update_yaxes(title=y_title, ticksuffix="%")
    return style_fig(fig, title, legend=False)


def sentido_stack(valid: pd.DataFrame, title: str) -> Optional[go.Figure]:
    if valid.empty:
        return None
    ct = pd.crosstab(valid["afore"], valid["sentido"], normalize="index").mul(100).reindex(columns=SENTIDO_ORDER, fill_value=0.0)
    ct = ct.reindex(order_list(ct.index, AFORE_ORDER))
    fig = go.Figure()
    for sentido in SENTIDO_ORDER:
        fig.add_trace(go.Bar(
            y=list(ct.index), x=ct[sentido], name=sentido, orientation="h", marker_color=SENTIDO_COLORS[sentido],
            text=[f"{v:.0f}%" if v >= 5 else "" for v in ct[sentido]], textposition="inside", insidetextanchor="middle",
            textfont=dict(color="white" if sentido == SENTIDO_ORDER[0] else TEXT),
            hovertemplate="%{y}: %{x:.1f}%<extra>" + sentido + "</extra>",
        ))
    fig.update_layout(barmode="stack")
    fig.update_xaxes(range=[0, 100], ticksuffix="%", title=None)
    fig.update_yaxes(autorange="reversed", title=None)
    return style_fig(fig, title)


def diff_box(valid: pd.DataFrame, title: str, y_title: str) -> Optional[go.Figure]:
    d = valid.dropna(subset=["dif_pct"])
    if d.empty:
        return None
    fig = px.box(
        d, x="afore", y="dif_pct", color="afore", facet_col="regimen_label", color_discrete_map=color_map(d["afore"].unique()),
        category_orders={"afore": order_list(d["afore"], AFORE_ORDER), "regimen_label": REGIMEN_LABEL_ORDER},
        labels={"afore": "AFORE", "dif_pct": y_title},
    )
    fig.for_each_annotation(lambda a: a.update(text=a.text.split("=")[-1]))
    fig.update_xaxes(title=None, tickangle=-35)
    fig.update_yaxes(title=y_title, ticksuffix="%")
    return style_fig(fig, title, legend=False, height=400)


def heatmap(valid: pd.DataFrame, title: str) -> Optional[go.Figure]:
    piv = valid.pivot_table(index="afore", columns="escenario", values="dif_pct", aggfunc="mean")
    piv = piv.reindex(index=order_list(piv.index, AFORE_ORDER), columns=order_list(piv.columns, list(ESCENARIO_LABELS)))
    piv = piv.dropna(how="all").dropna(how="all", axis=1)
    if piv.empty:
        return None
    z = piv.to_numpy(dtype=float)
    limit = float(np.nanmax(np.abs(z))) or 1.0
    fig = go.Figure(go.Heatmap(
        z=z, x=[escenario_label(c) for c in piv.columns], y=list(piv.index),
        text=[[fmt_pct(v, 2, signed=True) for v in row] for row in z], texttemplate="%{text}", zmin=-limit, zmax=limit,
        colorscale=[[0, "#FA8D5A"], [0.5, "#FFFFFF"], [1, "#009CC6"]], hoverongaps=False,
        colorbar=dict(title="Dif. %", ticksuffix="%"),
        hovertemplate="%{y} · %{x}<br>Dif. media: %{z:.2f}%<extra></extra>",
    ))
    fig.update_xaxes(tickangle=-30)
    fig.update_yaxes(autorange="reversed")
    return style_fig(fig, title, legend=False, height=360)


def box_pension(d: pd.DataFrame, title: str) -> Optional[go.Figure]:
    if d.empty:
        return None
    fig = px.box(
        d, x="regimen_label", y="pension", color="afore", color_discrete_map=color_map(d["afore"].unique()), points=False,
        category_orders={"afore": order_list(d["afore"], AFORE_ORDER), "regimen_label": REGIMEN_LABEL_ORDER},
        labels={"afore": "AFORE", "regimen_label": "Régimen", "pension": "Pensión mensual (MXN)"},
    )
    fig.update_xaxes(title=None)
    fig.update_yaxes(title="Pensión mensual (MXN)", tickprefix="$", tickformat=",.0f")
    return style_fig(fig, title, height=420)


def scatter_tasa(d: pd.DataFrame, title: str) -> Optional[go.Figure]:
    s = d.dropna(subset=["tasa_reemplazo", "densidad_cot"])
    if s.empty:
        return None
    fig = px.scatter(
        s, x="densidad_cot", y="tasa_reemplazo", color="regimen_label", color_discrete_map=REGIMEN_COLORS,
        category_orders={"regimen_label": REGIMEN_LABEL_ORDER},
        hover_data={"id_cliente": True, "escenario_label": True, "pension": ":,.0f", "regimen_label": False},
        labels={
            "densidad_cot": "Densidad de cotización (%)", "tasa_reemplazo": "Tasa de reemplazo (%)", "regimen_label": "Régimen",
            "id_cliente": "Perfil", "escenario_label": "Escenario", "pension": "Pensión (MXN)",
        },
    )
    fig.update_traces(marker=dict(size=8, opacity=0.85, line=dict(width=0.8, color=BLUE)))
    fig.update_yaxes(ticksuffix="%")
    fig.update_xaxes(ticksuffix="%")
    return style_fig(fig, title, height=420)


def retiro_bars(df: pd.DataFrame, title: str) -> Optional[go.Figure]:
    d = df[df["pension"] > 0]
    frames = [
        pd.DataFrame({"regimen_label": d["regimen_label"], "afore": d["afore"], "horizonte": label, "incremento": (d[col] / d["pension"] - 1) * 100})
        for col, label in (("pension_mas1", "Retiro +1 año"), ("pension_mas2", "Retiro +2 años"))
    ]
    g = pd.concat(frames).groupby(["regimen_label", "afore", "horizonte"], as_index=False)["incremento"].mean().dropna(subset=["incremento"])
    if g.empty:
        return None
    fig = px.bar(
        g, x="regimen_label", y="incremento", color="afore", barmode="group", facet_col="horizonte",
        color_discrete_map=color_map(g["afore"].unique()),
        category_orders={"afore": order_list(g["afore"], AFORE_ORDER), "regimen_label": REGIMEN_LABEL_ORDER},
        labels={"afore": "AFORE", "regimen_label": "Régimen", "incremento": "Incremento de pensión (%)"},
    )
    fig.for_each_annotation(lambda a: a.update(text=a.text.split("=")[-1]))
    fig.update_xaxes(title=None)
    fig.update_yaxes(title="Incremento de pensión (%)", ticksuffix="%", rangemode="tozero")
    return style_fig(fig, title)


def escenarios_mix(perfiles: pd.DataFrame, title: str) -> Optional[go.Figure]:
    g = perfiles.groupby(["escenario", "escenario_label", "resultado"], as_index=False).size().rename(columns={"size": "perfiles"})
    if g.empty:
        return None
    g["pct"] = 100 * g["perfiles"] / g["perfiles"].sum()
    order = [escenario_label(e) for e in order_list(g["escenario"], list(ESCENARIO_LABELS))]
    fig = px.bar(
        g, y="escenario_label", x="perfiles", color="resultado", orientation="h", color_discrete_map=RESULT_COLORS,
        text=[f"{n:,} ({p:.0f}%)" for n, p in zip(g["perfiles"], g["pct"])],
        category_orders={"escenario_label": order, "resultado": list(RESULT_COLORS)},
        labels={"escenario_label": "Escenario", "perfiles": "Perfiles", "resultado": "Resultado"},
    )
    fig.update_traces(textposition="outside", cliponaxis=False)
    fig.update_yaxes(autorange="reversed", title=None)
    fig.update_xaxes(title="Perfiles")
    return style_fig(fig, title)


def negativa_semanas(perfiles: pd.DataFrame, title: str) -> Optional[go.Figure]:
    d = perfiles.dropna(subset=["rango_semanas"])
    g = d.groupby(["regimen_label", "rango_semanas"]).agg(perfiles=("id_cliente", "size"), pct=("es_negativa", "mean")).reset_index()
    if g.empty:
        return None
    g["pct"] *= 100
    fig = px.line(
        g, x="rango_semanas", y="pct", color="regimen_label", markers=True, color_discrete_map=REGIMEN_COLORS,
        category_orders={"rango_semanas": SEMANAS_LABELS, "regimen_label": REGIMEN_LABEL_ORDER}, hover_data={"perfiles": True},
        labels={"rango_semanas": "Semanas cotizadas", "pct": "Negativa de pensión (%)", "regimen_label": "Régimen", "perfiles": "Perfiles"},
    )
    fig.update_traces(marker=dict(size=9, line=dict(width=0.8, color=BLUE)))
    fig.update_yaxes(title="Negativa de pensión (%)", ticksuffix="%", range=[0, 105])
    fig.update_xaxes(title="Semanas cotizadas")
    return style_fig(fig, title)


# =============================================================================
# 7. COMPONENTES DE INTERFAZ
# =============================================================================
FORMATTERS = {
    "money": lambda v: fmt_mxn(v, 0),
    "money2": lambda v: fmt_mxn(v, 2),
    "money_signed": lambda v: fmt_mxn(v, 0, signed=True),
    "money2_signed": lambda v: fmt_mxn(v, 2, signed=True),
    "pct": lambda v: fmt_pct(v, 1),
    "pct2": lambda v: fmt_pct(v, 2),
    "pct_signed": lambda v: fmt_pct(v, 2, signed=True),
    "pp": lambda v: fmt_pp(v, 2),
    "int": fmt_int,
    "factor": lambda v: "—" if pd.isna(v) else f"{v:.2f}×",
}
MEDIDAS = {"Pensión mensual": ("pension", "MXN por mes"), "Saldo proyectado": ("saldo_proy", "MXN")}
NO_DATA = "No hay datos para mostrar con los filtros actuales."


def kpi(col, label: str, value: str, captions: Sequence[str] = (), help_text: Optional[str] = None) -> None:
    with col:
        with st.container(border=True):
            st.metric(label, value, help=help_text)
            for text in captions:
                st.caption(text)


def show_fig(fig: Optional[go.Figure], empty_msg: str = NO_DATA) -> None:
    if fig is None:
        st.info(empty_msg)
    else:
        st.plotly_chart(fig, use_container_width=True, theme=None)


def show_table(df: pd.DataFrame, formats: Dict[str, str], na_overrides: Optional[Dict[str, str]] = None, height: Optional[int] = None) -> None:
    """Tabla con formato numérico visible y valores numéricos reales para ordenar."""
    styler = df.style.format({c: FORMATTERS[k] for c, k in formats.items() if c in df.columns}, na_rep="—")
    for col, text in (na_overrides or {}).items():
        if col in df.columns:
            styler = styler.format(FORMATTERS[formats[col]], subset=[col], na_rep=text)
    st.dataframe(styler, hide_index=True, use_container_width=True, height=height)


def sort_regimen_afore(df: pd.DataFrame) -> pd.DataFrame:
    r_rank = {label: i for i, label in enumerate(REGIMEN_LABEL_ORDER)}
    a_rank = {afore: i for i, afore in enumerate(AFORE_ORDER)}
    keyed = df.assign(_r=df["regimen_label"].map(r_rank).fillna(99), _a=df["afore"].map(a_rank).fillna(99))
    return keyed.sort_values(["_r", "_a"]).drop(columns=["_r", "_a"])


def vs_caption(pares: Dict[str, pd.DataFrame], col: str, base: str, as_pp: bool = False) -> List[str]:
    valid = pares[col].dropna(subset=["dif"]) if col in pares else pd.DataFrame()
    if valid.empty:
        return []
    text = fmt_pp(valid["dif"].mean(), 2) if as_pp else fmt_pct(valid["dif_pct"].mean(), 2, signed=True)
    return [f"Otras AFOREs vs {base}: {text}"]


def _set_base() -> None:
    st.session_state["base_afore"] = st.session_state["base_select"]


# =============================================================================
# 8. PESTAÑAS
# =============================================================================
def tab_resumen(df: pd.DataFrame, base: str, afores: List[str]) -> None:
    st.caption("¿Cómo luce el universo filtrado y cómo se ubica la AFORE base frente a las demás?")
    rows = df[df["afore"] == base]
    negativas = int(rows["es_negativa"].sum())
    pares = {c: paired_differences(df, base, c) for c in ("pension", "tasa_reemplazo", "saldo_proy")} if len(afores) > 1 else {}

    st.markdown(f"**Indicadores de la AFORE base: {base}**")
    cols = st.columns(5)
    kpi(cols[0], "Perfiles analizados", fmt_int(rows["id_cliente"].nunique()), [f"{len(df):,} resultados en {len(afores)} AFOREs"])
    kpi(
        cols[1], "Negativa de pensión", fmt_pct(100 * negativas / len(rows)), [f"{negativas:,} de {len(rows):,} perfiles ({base})"],
        "Perfiles cuyo escenario es una negativa de pensión: no tienen pensión y no entran en los promedios.",
    )
    kpi(
        cols[2], "Pensión media", fmt_mxn(rows["pension"].mean()),
        [f"{int(rows['pension'].notna().sum()):,} perfiles con pensión"] + vs_caption(pares, "pension", base),
        "MXN por mes, solo perfiles con pensión.",
    )
    kpi(
        cols[3], "Tasa de reemplazo", fmt_pct(rows["tasa_reemplazo"].mean()), vs_caption(pares, "tasa_reemplazo", base, as_pp=True),
        "100 × pensión mensual / salario mensual, solo perfiles con pensión.",
    )
    kpi(
        cols[4], "Saldo proyectado", fmt_mxn(rows["saldo_proy"].mean()), vs_caption(pares, "saldo_proy", base),
        "saldo_acumulado_web en MXN; incluye perfiles con negativa de pensión.",
    )

    left, right = st.columns(2)
    with left:
        show_fig(grouped_bar(df, "pension", "Pensión mensual media por régimen y AFORE", "MXN por mes"), "No hay perfiles con pensión con los filtros actuales.")
    with right:
        if len(afores) > 1:
            show_fig(diff_bar(summarize_pairs(pares["pension"]), f"Diferencia media de pensión vs {base}", "Diferencia (%)"), "No hay comparaciones de pensión válidas con los filtros actuales.")
        else:
            st.info("Selecciona al menos dos AFOREs en el filtro para ver la comparación.")
    st.caption("Promedios de perfiles con pensión. La diferencia compara cada AFORE con la base sobre los mismos perfiles (AFORE − base); positivo = la AFORE paga más.")


def tab_comparativo(df: pd.DataFrame, base: str, afores: List[str]) -> None:
    st.caption("¿En qué perfiles, regímenes y escenarios difiere cada AFORE de la base? Diferencia = AFORE comparada − AFORE base (positivo: la comparada es mayor).")
    if len(afores) < 2:
        st.info("Selecciona al menos dos AFOREs en el filtro para comparar.")
        return
    c1, c2, _ = st.columns([1, 1.6, 2])
    with c1:
        st.selectbox("AFORE base", afores, index=afores.index(base), key="base_select", on_change=_set_base)
    with c2:
        medida = st.radio("Medida de comparación", list(MEDIDAS), horizontal=True, key="medida_comparacion")
    col, unidad = MEDIDAS[medida]

    pares = paired_differences(df, base, col)
    valid = pares.dropna(subset=["dif"])
    if valid.empty:
        st.info(f"No hay comparaciones válidas de {medida.lower()} con los filtros actuales.")
        return
    summary = summarize_pairs(pares)
    decimals = 2 if col == "pension" else 0

    k = st.columns(4)
    kpi(k[0], "Perfiles en la base", fmt_int(df.loc[df["afore"] == base, "id_cliente"].nunique()), [f"AFORE base: {base}"])
    kpi(k[1], "Comparaciones válidas", fmt_int(len(valid)), [f"{len(pares) - len(valid):,} excluidas por no tener {medida.lower()} en alguna de las dos AFOREs"])
    kpi(k[2], "Diferencia media (%)", fmt_pct(valid["dif_pct"].mean(), 2, signed=True), ["Promedio de las diferencias % por perfil"])
    kpi(k[3], f"Diferencia media ({unidad})", fmt_mxn(valid["dif"].mean(), decimals, signed=True), ["Promedio de las diferencias absolutas por perfil"])

    left, right = st.columns(2)
    with left:
        show_fig(diff_bar(summary, f"Diferencia media de {medida.lower()} vs {base}", "Diferencia (%)"))
    with right:
        show_fig(sentido_stack(valid, f"Perfiles según {medida.lower()} frente a {base}"))
    show_fig(diff_box(valid, f"Distribución de las diferencias por perfil · {medida.lower()}", "Diferencia (%)"))
    show_fig(heatmap(valid, f"Diferencia media (%) por AFORE y escenario · {medida.lower()}"))

    st.subheader("Resumen por AFORE")
    table = summary.rename(columns={
        "afore": "AFORE", "comparaciones": "Comparaciones", "dif_media": f"Dif. media ({unidad})", "dif_pct_media": "Dif. media (%)",
        "dif_pct_mediana": "Dif. mediana (%)", **{s: f"{s} (%)" for s in SENTIDO_ORDER},
    })
    formats = {"Comparaciones": "int", f"Dif. media ({unidad})": "money2_signed" if col == "pension" else "money_signed", "Dif. media (%)": "pct_signed", "Dif. mediana (%)": "pct_signed"}
    formats.update({f"{s} (%)": "pct" for s in SENTIDO_ORDER})
    if col == "pension":
        tasa = paired_differences(df, base, "tasa_reemplazo").dropna(subset=["dif"]).groupby("afore")["dif"].mean()
        table["Dif. tasa de reemplazo (pp)"] = table["AFORE"].map(tasa)
        formats["Dif. tasa de reemplazo (pp)"] = "pp"
    show_table(table, formats)
    st.caption("Mayor/Igual/Menor se refiere a la AFORE comparada frente a la base en cada perfil. Pares sin pensión en alguna AFORE se excluyen.")


def tab_pension(df: pd.DataFrame, base: str, afores: List[str]) -> None:
    st.caption("¿Qué pensión y tasa de reemplazo se obtienen, y cómo se distribuyen por AFORE y régimen? Solo perfiles con pensión.")
    d = df[df["pension"].notna()]
    if d.empty:
        st.info("No hay perfiles con pensión con los filtros actuales (todos son negativa de pensión).")
        return
    show_fig(box_pension(d, "Distribución de la pensión mensual por régimen y AFORE"))

    st.subheader("Resumen por régimen y AFORE")
    resumen = d.groupby(["regimen_label", "afore"]).agg(
        perfiles=("id_cliente", "nunique"), media=("pension", "mean"), mediana=("pension", "median"),
        p25=("pension", lambda s: s.quantile(0.25)), p75=("pension", lambda s: s.quantile(0.75)), tasa=("tasa_reemplazo", "mean"),
    ).reset_index()
    resumen = sort_regimen_afore(resumen).rename(columns={
        "regimen_label": "Régimen", "afore": "AFORE", "perfiles": "Perfiles con pensión", "media": "Pensión media", "mediana": "Pensión mediana",
        "p25": "Percentil 25", "p75": "Percentil 75", "tasa": "Tasa de reemplazo media",
    })
    show_table(resumen, {
        "Perfiles con pensión": "int", "Pensión media": "money", "Pensión mediana": "money", "Percentil 25": "money", "Percentil 75": "money",
        "Tasa de reemplazo media": "pct",
    })

    st.subheader("Tasa de reemplazo y densidad de cotización")
    afore_sel = st.selectbox("AFORE a graficar", afores, index=afores.index(base), key="afore_scatter")
    show_fig(scatter_tasa(d[d["afore"] == afore_sel], f"Tasa de reemplazo vs densidad de cotización · {afore_sel}"), "Esa AFORE no tiene perfiles con pensión con los filtros actuales.")
    st.caption("Tasa de reemplazo = 100 × pensión mensual / salario mensual. Densidad = 100 × semanas cotizadas / semanas desde el año de afiliación.")


def tab_saldos(df: pd.DataFrame) -> None:
    st.caption("¿Cómo crece el saldo y qué cambia si se retrasa el retiro o hay aportaciones voluntarias?")
    left, right = st.columns(2)
    with left:
        show_fig(grouped_bar(df, "saldo_proy", "Saldo proyectado medio por régimen y AFORE", "MXN"))
        st.caption("Incluye perfiles con negativa de pensión: el saldo se proyecta aunque no haya pensión.")
    with right:
        show_fig(retiro_bars(df, "Incremento de la pensión al retrasar el retiro"), "No hay perfiles con pensión con los filtros actuales.")
        st.caption("Perfiles con pensión. Los escenarios +1 y +2 años suponen continuidad de cotización.")

    st.subheader("Efecto del ahorro voluntario (AV)")
    av = df[df["tiene_av"] & df["pension"].notna()].assign(efecto_pension=lambda x: x["pension_con_av"] - x["pension"])
    show_fig(
        grouped_bar(av, "efecto_pension", "Efecto del AV en la pensión mensual (perfiles con AV y pensión)", "MXN por mes"),
        "No hay perfiles con ahorro voluntario y pensión con los filtros actuales.",
    )
    if not av.empty:
        efecto = df[df["tiene_av"]].assign(
            efecto_pension=lambda x: x["pension_con_av"] - x["pension"], efecto_saldo=lambda x: x["saldo_proy_con_av"] - x["saldo_proy"],
        ).groupby(["regimen_label", "afore"]).agg(
            perfiles=("id_cliente", "nunique"), con_efecto=("efecto_pension", lambda s: int((s > 0).sum())),
            efecto_pension=("efecto_pension", "mean"), efecto_saldo=("efecto_saldo", "mean"),
        ).reset_index()
        efecto = sort_regimen_afore(efecto).rename(columns={
            "regimen_label": "Régimen", "afore": "AFORE", "perfiles": "Perfiles con AV", "con_efecto": "Con aumento de pensión",
            "efecto_pension": "Efecto medio en pensión (MXN/mes)", "efecto_saldo": "Efecto medio en saldo (MXN)",
        })
        show_table(efecto, {
            "Perfiles con AV": "int", "Con aumento de pensión": "int", "Efecto medio en pensión (MXN/mes)": "money2", "Efecto medio en saldo (MXN)": "money",
        })
    st.caption("Efecto = pensión (o saldo) con AV menos sin AV. En Ley 73 el AV mensual no eleva automáticamente la pensión.")

    st.subheader("Saldo inicial y proyectado")
    saldos = df.groupby(["regimen_label", "afore"]).agg(inicial=("saldo_inicial", "mean"), proy=("saldo_proy", "mean")).reset_index()
    saldos["factor"] = saldos["proy"] / saldos["inicial"]
    saldos = sort_regimen_afore(saldos).rename(columns={
        "regimen_label": "Régimen", "afore": "AFORE", "inicial": "Saldo inicial medio", "proy": "Saldo proyectado medio", "factor": "Múltiplo",
    })
    show_table(saldos, {"Saldo inicial medio": "money", "Saldo proyectado medio": "money", "Múltiplo": "factor"})
    st.caption("Saldo inicial = RCV + ahorro solidario + bono (excluye AV y vivienda). Múltiplo = saldo proyectado / saldo inicial.")


def tab_escenarios(df: pd.DataFrame, base: str) -> None:
    st.caption("¿Qué escenarios predominan y en qué perfiles se niega la pensión?")
    perfiles = df[df["afore"] == base]
    left, right = st.columns(2)
    with left:
        show_fig(grouped_bar(df.assign(pct_negativa=df["es_negativa"] * 100.0), "pct_negativa", "Negativa de pensión por régimen y AFORE", "% de perfiles", money=False))
    with right:
        show_fig(escenarios_mix(perfiles, f"Perfiles por escenario · {base}"))
    st.caption(f"El escenario es una característica del perfil; se muestra una fila por perfil con los resultados de {base}.")
    show_fig(negativa_semanas(perfiles, f"Negativa de pensión según semanas cotizadas · {base}"))

    st.subheader("Resumen por escenario")
    tabla = perfiles.groupby(["escenario", "escenario_label", "regimen_label"], as_index=False).agg(
        perfiles=("id_cliente", "nunique"), modalidad=("modalidad_label", "first"), pension=("pension", "mean"), tasa=("tasa_reemplazo", "mean"),
    )
    tabla["pct"] = 100 * tabla["perfiles"] / tabla["perfiles"].sum()
    tabla = tabla.set_index("escenario").reindex(order_list(tabla["escenario"], list(ESCENARIO_LABELS))).reset_index()
    tabla = tabla[["escenario_label", "regimen_label", "perfiles", "pct", "modalidad", "pension", "tasa"]].rename(columns={
        "escenario_label": "Escenario", "regimen_label": "Régimen", "perfiles": "Perfiles", "pct": "% de los perfiles", "modalidad": "Modalidad",
        "pension": "Pensión media", "tasa": "Tasa de reemplazo media",
    })
    show_table(tabla, {"Perfiles": "int", "% de los perfiles": "pct", "Pensión media": "money", "Tasa de reemplazo media": "pct"}, na_overrides={"Pensión media": RESULT_NEGATIVA, "Tasa de reemplazo media": RESULT_NEGATIVA})


DETALLE_COLS = {
    "afore": "AFORE", "id_cliente": "Perfil", "regimen_label": "Régimen", "escenario_label": "Escenario", "resultado": "Resultado",
    "edad": "Edad", "genero_label": "Género", "salario": "Salario mensual", "pension": "Pensión mensual", "pension_con_av": "Pensión con AV",
    "tasa_reemplazo": "Tasa de reemplazo", "saldo_proy": "Saldo proyectado", "saldo_proy_con_av": "Saldo proyectado con AV", "modalidad_label": "Modalidad",
}
DETALLE_FORMATS = {
    "Salario mensual": "money2", "Pensión mensual": "money2", "Pensión con AV": "money2", "Tasa de reemplazo": "pct",
    "Saldo proyectado": "money", "Saldo proyectado con AV": "money",
}
METHODOLOGY_SIMULATED = """
**Datos simulados.** Las columnas `*_web` (incluida `Pension_web`) son salidas ficticias de una fórmula de prueba (`estado = SIMULADO_NO_CONSULTADO`): no se consultó ninguna calculadora pública y no equivalen a una oferta, pronóstico, derecho pensionario ni dato financiero real. Las diferencias entre AFOREs reflejan únicamente la tasa de rendimiento hipotética asignada a cada una (tabla inferior) y no miden ni clasifican AFOREs. En IMSS Ley 73 la pensión usa una razón salarial hipotética y no depende del saldo, por eso es igual entre AFOREs.
"""
METHODOLOGY = """
**Fuente y alcance.** Una fila por AFORE y perfil. Un mismo `id_cliente` representa el mismo perfil hipotético en todas las AFOREs (no implica multiafiliación real). No se cargan nombre, CURP, NSS ni correo.

**Indicadores**
- *Pensión mensual*: `Pension_web`, MXN por mes en poder adquisitivo de 2026. Solo perfiles con pensión.
- *Negativa de pensión*: escenarios `*_NEGATIVA_PENSION`. Es un resultado, no una pensión de 0 MXN: se muestra como «Negativa de pensión» y no entra en los promedios de pensión ni de tasa de reemplazo.
- *Tasa de reemplazo*: 100 × pensión mensual / salario mensual (`tasa_remplazo_web`, escala 0–100).
- *Saldo proyectado*: `saldo_acumulado_web`, incluye perfiles con negativa. Con AV: `saldo_acumulado_con_av_web`, que añade las aportaciones voluntarias mensuales futuras.
- *Perfil con ahorro voluntario (AV)*: `saldo_av > 0` o `av_mensual > 0`.
- *Retiro +1 / +2 años*: `pension_edad_mas_1_web` y `pension_edad_mas_2_web`; suponen continuidad de cotización.

**Comparaciones.** Se emparejan por `id_cliente` contra la AFORE base. Diferencia = AFORE comparada − base; diferencia % = (comparada / base − 1) × 100. Las tasas de reemplazo se comparan en puntos porcentuales (pp). Si alguna de las dos AFOREs no tiene pensión, el par se excluye. «Igual» significa una diferencia absoluta menor a 0.005.

**Lectura.** Mayor pensión, saldo y tasa de reemplazo son más favorables para el afiliado; un mayor % de negativas lo es menos. Esto no implica desempeño real de ninguna AFORE.
"""


def tab_detalle(df: pd.DataFrame, df_all: pd.DataFrame, quality: List[Dict[str, str]], is_simulated: bool) -> None:
    st.caption("¿Qué hay detrás de las cifras y qué tan confiables son los datos?")
    st.subheader("Registros filtrados")
    a_rank = {afore: i for i, afore in enumerate(AFORE_ORDER)}
    ordered = df.assign(_a=df["afore"].map(a_rank).fillna(99)).sort_values(["id_cliente", "_a"])
    detalle = ordered[list(DETALLE_COLS)].rename(columns=DETALLE_COLS)
    show_table(detalle, DETALLE_FORMATS, na_overrides={"Pensión mensual": RESULT_NEGATIVA, "Pensión con AV": RESULT_NEGATIVA}, height=420)
    st.download_button(
        "Descargar CSV filtrado", data=detalle.to_csv(index=False).encode("utf-8-sig"), file_name="pensiones_filtrado.csv", mime="text/csv", type="primary",
    )
    st.caption(f"La descarga contiene los {len(detalle):,} registros filtrados y las columnas mostradas; en negativas de pensión la pensión queda vacía.")

    with st.expander("Metodología y definiciones", expanded=False):
        if is_simulated:
            st.markdown(METHODOLOGY_SIMULATED)
        st.markdown(METHODOLOGY)
        tasas = df_all.groupby("afore")["tasa_rendimiento"].first().reindex(order_list(df_all["afore"], AFORE_ORDER)).reset_index()
        st.markdown("**Tasa de rendimiento anual por AFORE** (`tasa_rendimiento_web`)")
        show_table(tasas.rename(columns={"afore": "AFORE", "tasa_rendimiento": "Tasa anual"}), {"Tasa anual": "pct2"})

    st.subheader("Calidad de datos")
    st.caption("Controles sobre el archivo completo, sin aplicar filtros.")
    st.dataframe(pd.DataFrame(quality), hide_index=True, use_container_width=True)


# =============================================================================
# 9. APLICACIÓN
# =============================================================================
def main() -> None:
    st.markdown(CSS, unsafe_allow_html=True)
    st.title(PAGE_TITLE)
    st.markdown('<div class="brand-bar"></div>', unsafe_allow_html=True)

    try:
        mtime = DATA_PATH.stat().st_mtime
        df_all, quality = load_data(str(DATA_PATH), mtime)
    except FileNotFoundError:
        st.error(f"No se encontró el archivo de datos: {DATA_PATH}")
        st.stop()
    except ValueError as exc:
        st.error(f"No se pudo cargar el CSV: {exc}")
        st.stop()

    df, active = sidebar_filters(df_all)
    estados = sorted(df_all["estado"].dropna().unique())
    is_simulated = any("SIMULADO" in e for e in estados)
    st.caption("Pensión mensual estimada y saldo proyectado por AFORE, perfil, régimen y escenario, con una AFORE base de comparación.")
    if is_simulated:
        st.warning(
            "**Datos sintéticos** (estado: " + ", ".join(estados) + "). Las salidas `*_web` son simulaciones de prueba, no resultados de calculadoras "
            "ni datos oficiales; las diferencias entre AFOREs reflejan solo la tasa de rendimiento hipotética de cada una (ver Metodología)."
        )
    st.caption(
        f"Universo filtrado: {len(df):,} de {len(df_all):,} resultados · {df['id_cliente'].nunique():,} perfiles · {df['afore'].nunique()} AFOREs"
        f"  |  Datos: {DATA_PATH.name}, archivo modificado el {datetime.fromtimestamp(mtime):%d/%m/%Y %H:%M}"
    )
    if active:
        st.caption("Filtros activos: " + " · ".join(active))
    if df.empty:
        st.warning("Los filtros actuales no devuelven resultados. Ajusta los filtros o usa «Restablecer filtros» en la barra lateral.")
        st.stop()

    afores = order_list(df["afore"], AFORE_ORDER)
    base = resolve_base(afores)
    tabs = st.tabs(["Resumen", "Comparativo vs base", "Pensión y tasa de reemplazo", "Saldos y proyección", "Escenarios y negativas", "Detalle y metodología"])
    try:
        with tabs[0]:
            tab_resumen(df, base, afores)
        with tabs[1]:
            tab_comparativo(df, base, afores)
        with tabs[2]:
            tab_pension(df, base, afores)
        with tabs[3]:
            tab_saldos(df)
        with tabs[4]:
            tab_escenarios(df, base)
        with tabs[5]:
            tab_detalle(df, df_all, quality, is_simulated)
    except DataError as exc:
        st.error(str(exc))


if __name__ == "__main__":
    main()


