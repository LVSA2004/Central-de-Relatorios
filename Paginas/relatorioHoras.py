import os
import streamlit as st
import plotly.express as px
import datetime as dt
from planilhaLoader import *

BASE_DIR = get_base_dir()
FILE_PATH = get_excel_path()
ICON_LOGO = os.path.join(BASE_DIR, "Logos", "mills_logo_branca.png")
LOGO_PATH = os.path.join(BASE_DIR, "Logos", "mills_logo_branca.svg")

MONTH_MAP = {
    "janeiro": 1, "fevereiro": 2, "março": 3, "abril": 4,
    "maio": 5, "junho": 6, "julho": 7, "agosto": 8,
    "setembro": 9, "outubro": 10, "novembro": 11, "dezembro": 12
}


def get_month_number(sheet_name: str) -> int | None:
    return MONTH_MAP.get(sheet_name.strip().lower())


def hhmmss_to_minutes(x: str) -> float:
    if not isinstance(x, str) or ":" not in x:
        return 0.0
    h, m, s = x.split(":")
    return int(h) * 60 + int(m) + int(s) / 60

def hhmmss_to_hours(x: str) -> float:
    """Converte HH:MM:SS para horas (float)"""
    if not isinstance(x, str) or ":" not in x:
        return 0.0
    h, m, s = x.split(":")
    return int(h) + int(m) / 60 + int(s) / 3600


def relatorio():
    if not os.path.exists(FILE_PATH):
        st.error("❌ Arquivo não encontrado: Planilhas/Controle de Horas Mills.xlsx")
        st.stop()
    sheet_names = list_sheets(FILE_PATH)
    sheet_selected = st.selectbox("📄 Worksheet", sheet_names, index=max(0, len(sheet_names) - 1))
    df = load_sheet(FILE_PATH, sheet_selected)
    df = recortar_planilha(df)                   
    df = fix_duration_column(df, "Total - Monitoramento")
    df = fix_duration_column(df, "Total - Desenvolvimento")
    df = fix_duration_column(df, "Total")
    st.subheader(f"📌 {sheet_selected}")
    st.dataframe(df, use_container_width=True, height=650)
    return df, sheet_selected


def graficoBarras(df):
    if df is None or df.empty:
        st.info("Sem dados para gerar gráficos.")
        return

    df_plot = df[
        df["Dia"].astype(str).str.strip().str.lower() != "soma"
    ].copy()

    if df_plot.empty:
        st.warning("Dados insuficientes para análise (apenas linha de soma).")
        return

    # Conversões para análise
    df_plot["Monit_min"] = df_plot["Total - Monitoramento"].map(hhmmss_to_minutes)
    df_plot["Dev_min"] = df_plot["Total - Desenvolvimento"].map(hhmmss_to_minutes)

    df_long = df_plot.melt(
        id_vars=["Dia"],
        value_vars=["Monit_min", "Dev_min"],
        var_name="Tipo",
        value_name="Minutos"
    )

    df_long["Tipo"] = df_long["Tipo"].map({
        "Monit_min": "Monitoramento",
        "Dev_min": "Desenvolvimento"
    })

    fig = px.bar(
        df_long,
        x="Dia",
        y="Minutos",
        color="Tipo",
        title="Minutos por dia — Monitoramento x Desenvolvimento",
        labels={"Minutos": "Minutos", "Dia": "Dia"},
    )

    st.plotly_chart(fig, use_container_width=True)
    return df_plot

def graficoPizza(df_plot):
    total_monit = df_plot["Monit_min"].sum()
    total_dev = df_plot["Dev_min"].sum()

    df_pie = pd.DataFrame({
        "Tipo": ["Monitoramento", "Desenvolvimento"],
        "Minutos": [total_monit, total_dev]
    })

    fig2 = px.pie(
        df_pie,
        names="Tipo",
        values="Minutos",
        title="Distribuição do tempo total"
    )

    st.plotly_chart(fig2, use_container_width=True)

def graficoBurnUp(df_plot):
    df_plot["Total_min"] = df_plot["Total"].map(hhmmss_to_minutes)
    df_plot = df_plot.sort_values("Dia")

    df_plot["Acumulado"] = df_plot["Total_min"].cumsum()

    fig3 = px.line(
        df_plot,
        x="Dia",
        y="Acumulado",
        title="Horas acumuladas no mês",
        labels={"Acumulado": "Minutos acumulados"}
    )

    st.plotly_chart(fig3, use_container_width=True)

def boxplot(df_plot):
    fig4 = px.box(
        df_plot,
        y="Total_min",
        title="Variabilidade do tempo diário",
        labels={"Total_min": "Minutos por dia"},
        points="outliers"
    )
    st.plotly_chart(fig4, use_container_width=True)

def heatmap_monitoramento(df: pd.DataFrame,sheet_selected: str,year: int = 2025):
    if df is None or df.empty:
        st.info("Sem dados para gerar heatmap.")
        return

    # 🔹 ignora linha "Soma"
    df_plot = df[df["Dia"].astype(str).str.strip().str.lower() != "soma"].copy()
    if df_plot.empty:
        st.warning("Planilha contém apenas a linha de soma.")
        return

    # 🔹 resolve o mês pelo nome da worksheet
    month = MONTH_MAP.get(sheet_selected.strip().lower())
    if not month:
        st.error(f"Não foi possível identificar o mês da aba '{sheet_selected}'.")
        return

    # 🔹 dia do mês
    df_plot["Dia"] = pd.to_numeric(df_plot["Dia"], errors="coerce")
    df_plot = df_plot.dropna(subset=["Dia"])
    df_plot["Dia"] = df_plot["Dia"].astype(int)

    # 🔹 cria data real
    df_plot["Data"] = df_plot["Dia"].apply(
        lambda d: dt.date(year, month, d)
    )

    # 🔹 dia da semana (Seg..Dom)
    dow_labels = ["Seg", "Ter", "Qua", "Qui", "Sex", "Sáb", "Dom"]
    df_plot["DiaSemana"] = df_plot["Data"].apply(lambda d: dow_labels[d.weekday()])

    # 🔹 semana do mês
    first_day = dt.date(year, month, 1)
    df_plot["SemanaMes"] = (
        (df_plot["Dia"] + first_day.weekday() - 1) // 7
    ) + 1

    # 🔹 horas de monitoramento
    df_plot["HorasMonit"] = df_plot["Total - Monitoramento"].map(hhmmss_to_hours)

    # 🔹 pivot para heatmap
    grid = df_plot.pivot_table(
        index="SemanaMes",
        columns="DiaSemana",
        values="HorasMonit",
        aggfunc="sum"
    ).reindex(columns=dow_labels)

    # 🔹 plot
    fig = px.imshow(
        grid,
        aspect="auto",
        title=f"Heatmap de Monitoramento — {sheet_selected}",
        labels=dict(
            x="Dia da semana",
            y="Semana do mês",
            color="Horas"
        ),
        color_continuous_scale="YlOrRd"
    )

    fig.update_layout(
        margin=dict(l=10, r=10, t=60, b=10),
        yaxis=dict(tickmode="linear")
    )

    st.plotly_chart(fig, use_container_width=True)



def exibir():
    df, sheet_selected = relatorio()
    df_plot = graficoBarras(df)
    graficoPizza(df_plot)
    graficoBurnUp(df_plot)
    boxplot(df_plot)
    heatmap_monitoramento(df, sheet_selected)