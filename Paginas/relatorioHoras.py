import os
import streamlit as st
import plotly.express as px
import datetime as dt
from planilhaLoader import *
import plotly.graph_objects as go

BASE_DIR = get_base_dir()
FILE_PATH = get_excel_path()
ICON_LOGO = os.path.join(BASE_DIR, "Logos", "mills_logo_branca.png")
LOGO_PATH = os.path.join(BASE_DIR, "Logos", "mills_logo_branca.svg")

MONTH_MAP = {
    "janeiro": 1, "fevereiro": 2, "março": 3, "abril": 4,
    "maio": 5, "junho": 6, "julho": 7, "agosto": 8,
    "setembro": 9, "outubro": 10, "novembro": 11, "dezembro": 12
}

DOW_ORDER = ["Seg", "Ter", "Qua", "Qui", "Sex", "Sáb", "Dom"]
DOW_MAP = {0: "Seg", 1: "Ter", 2: "Qua", 3: "Qui", 4: "Sex", 5: "Sáb", 6: "Dom"}


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


def mapa_dia_mes_08_17(df: pd.DataFrame, titulo="Mapa de horas (08:00–17:00)"):
    if df is None or df.empty:
        st.info("Sem dados para gerar o mapa.")
        return

    # ✅ ignora "Soma"
    df_plot = df[df["Dia"].astype(str).str.strip().str.lower() != "soma"].copy()
    if df_plot.empty:
        st.warning("Sem dados (apenas linha de soma).")
        return

    # mantém só o que interessa e ordena por dia (tenta ordenar pelo número no começo)
    df_plot["DiaLabel"] = df_plot["Dia"].astype(str).str.strip()

    # tenta extrair número do dia (serve pra "01/12" e "1")
    df_plot["DiaNum"] = pd.to_numeric(df_plot["DiaLabel"].str.extract(r"(\d+)")[0], errors="coerce")
    df_plot = df_plot.sort_values(["DiaNum", "DiaLabel"], na_position="last")

    # converte tempos para horas
    df_plot["Monit_h"] = df_plot["Total - Monitoramento"].map(hhmmss_to_hours)
    df_plot["Dev_h"]   = df_plot["Total - Desenvolvimento"].map(hhmmss_to_hours)

    # opcional: limitar a janela 08-17 (9h) para caber no eixo
    # se quiser mostrar tudo, remova o clip (mas aí pode “passar” de 17:00)
    df_plot["Monit_h"] = df_plot["Monit_h"].clip(lower=0, upper=9)
    df_plot["Dev_h"]   = df_plot["Dev_h"].clip(lower=0, upper=9)

    start_hour = 8
    end_hour = 17
    max_window = end_hour - start_hour  # 9 horas

    # se quiser que a soma não passe de 9h, ajusta proporcionalmente
    total = df_plot["Monit_h"] + df_plot["Dev_h"]
    scale = (max_window / total).where(total > max_window, 1.0)
    df_plot["Monit_h"] = df_plot["Monit_h"] * scale
    df_plot["Dev_h"]   = df_plot["Dev_h"] * scale

    y = df_plot["DiaLabel"]

    fig = go.Figure()

    # 1) Monitoramento (começa em 08:00)
    fig.add_trace(go.Bar(
        y=y,
        x=df_plot["Monit_h"],
        base=start_hour,
        orientation="h",
        name="Monitoramento",
        marker=dict(color="#FAA43A"),
        hovertemplate="Dia: %{y}<br>Monitoramento: %{x:.2f}h<extra></extra>",
    ))

    # 2) Desenvolvimento 
    fig.add_trace(go.Bar(
        y=y,
        x=df_plot["Dev_h"],
        base=start_hour + df_plot["Monit_h"],
        orientation="h",
        name="Desenvolvimento",
        marker=dict(color="#5DA5DA"),
        hovertemplate="Dia: %{y}<br>Desenvolvimento: %{x:.2f}h<extra></extra>",
    ))

    tickvals = list(range(start_hour, end_hour + 1))
    ticktext = [f"{h:02d}:00" for h in tickvals]

    fig.update_layout(
        template="simple_white",
        title=titulo,
        barmode="overlay", 
        xaxis=dict(
            range=[start_hour, end_hour],
            tickmode="array",
            tickvals=tickvals,
            ticktext=ticktext,
            side="top",
            title="",
        ),
        yaxis=dict(
            title="Dia",
            autorange="reversed"
        ),
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1
        ),
        margin=dict(l=60, r=30, t=80, b=30),
        height=max(420, 22 * len(df_plot))
    )
    st.plotly_chart(fig, use_container_width=True)
    return df_plot

def graficoPizza(df_plot):
    if df_plot is None or df_plot.empty:
        st.info("Sem dados para gerar o gráfico de pizza.")
        return
    total_monit_h = df_plot["Monit_h"].sum()
    total_dev_h   = df_plot["Dev_h"].sum()
    if total_monit_h == 0 and total_dev_h == 0:
        st.warning("Tempo total zerado — não há dados para exibir.")
        return
    df_pie = pd.DataFrame({
        "Tipo": ["Monitoramento", "Desenvolvimento"],
        "Horas": [total_monit_h, total_dev_h]
    })
    fig = px.pie(
        df_pie,
        names="Tipo",
        values="Horas",
        title="Distribuição do tempo total",
        hole=0.35,  # donut (mais profissional)
        color="Tipo",
        color_discrete_map={
            "Monitoramento": "#FAA43A",
            "Desenvolvimento": "#5DA5DA",
        }
    )
    fig.update_traces(
        textinfo="percent+label",
        marker=dict(line=dict(color="#000000", width=1))
    )
    fig.update_layout(
        template="simple_white",
        showlegend=True
    )
    st.plotly_chart(fig, use_container_width=True)


def exibir():
    df, sheet_selected = relatorio()
    df_plot = mapa_dia_mes_08_17(df, sheet_selected)
    graficoPizza(df_plot)
