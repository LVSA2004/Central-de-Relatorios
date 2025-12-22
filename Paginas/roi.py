import os
import pandas as pd
import streamlit as st
import plotly.express as px

from csvLoader import get_csv_path


# =============================
# Leitura + formatação
# =============================
@st.cache_data(show_spinner=False)
def load_roi_csv(path: str) -> pd.DataFrame:
    # ajuste encoding/sep se necessário
    return pd.read_csv(path, sep=";", encoding="latin1")

JOB_COLORS = {
    "JOB_NASA_VA": "#FAA43A",
    "JOB_NASA_CME_NF": "#5DA5DA",
    "JOB_NASA_CME_ST": "#60BD68",
    "JOB_SD_ZVF31_ECP": "#F10C29",
    "JOB_NASA_J3GH": "#B2912F",
    "JOB_SD_J1BFNE_ECP": "#B276B2",
}


def _parse_duration_to_minutes(series: pd.Series) -> pd.Series:
    """
    Converte uma coluna de duração para minutos.
    Aceita:
      - número em segundos (int/float)
      - texto "HH:MM:SS"
      - texto "0 days 00:12:33"
    """
    # tenta numérico (segundos)
    s_num = pd.to_numeric(series, errors="coerce")
    if s_num.notna().any():
        # assume que é segundos
        return (s_num / 60.0)

    # tenta to_timedelta para textos
    td = pd.to_timedelta(series, errors="coerce")
    return td.dt.total_seconds() / 60.0


def formatacao_csv(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()

    # Datas
    # Tenta com formato fixo; se falhar, cai no parse genérico
    if "Data Início" in df.columns:
        df["Data Início"] = pd.to_datetime(df["Data Início"], format="%d/%m/%Y %H:%M", errors="coerce")
        # fallback
        df["Data Início"] = df["Data Início"].fillna(pd.to_datetime(df["Data Início"], errors="coerce", dayfirst=True))

    if "Data Fim" in df.columns:
        df["Data Fim"] = pd.to_datetime(df["Data Fim"], format="%d/%m/%Y %H:%M", errors="coerce")
        df["Data Fim"] = df["Data Fim"].fillna(pd.to_datetime(df["Data Fim"], errors="coerce", dayfirst=True))

    # Duração
    # Preferência: Total (s) (se existir) -> Duracao_min
    if "Total (s)" in df.columns:
        df["Duracao_min"] = _parse_duration_to_minutes(df["Total (s)"])
    elif "Duração" in df.columns:
        df["Duracao_min"] = _parse_duration_to_minutes(df["Duração"])
    else:
        # se tiver começo/fim, calcula
        if "Data Início" in df.columns and "Data Fim" in df.columns:
            df["Duracao_min"] = (df["Data Fim"] - df["Data Início"]).dt.total_seconds() / 60.0
        else:
            df["Duracao_min"] = pd.NA

    # Hora do dia (para heatmap/hist)
    if "Data Início" in df.columns:
        df["Hora"] = df["Data Início"].dt.hour

    return df

def volume_exec(df: pd.DataFrame) -> pd.DataFrame:
    top_jobs = (
        df["Job"]
        .value_counts()
        .rename_axis("Job")          # <- garante o nome da 1ª coluna
        .reset_index(name="Execuções")  # <- garante o nome da contagem
        .head(10)
    )
    return top_jobs


def tempo_medio_exec(df: pd.DataFrame, top_n: int = 10) -> pd.DataFrame:
    if "Job" not in df.columns or "Duracao_min" not in df.columns:
        return pd.DataFrame(columns=["Job", "Tempo médio (min)"])
    out = (
        df.groupby("Job", as_index=False)["Duracao_min"]
        .mean()
        .rename(columns={"Duracao_min": "Tempo médio (min)"})
        .sort_values("Tempo médio (min)", ascending=False)
        .head(top_n)
    )
    return out


def carga_node(df: pd.DataFrame) -> pd.DataFrame:
    # tenta achar uma coluna de ID/registro para contagem
    count_col = "Código" if "Código" in df.columns else None
    if "Node" not in df.columns or "Duracao_min" not in df.columns:
        return pd.DataFrame(columns=["Node", "Execucoes", "Tempo_Total_min", "Tempo_Medio_min"])

    if count_col is None:
        # se não houver "Código", conta linhas
        out = (
            df.groupby("Node", as_index=False)
            .agg(
                Execucoes=("Duracao_min", "count"),
                Tempo_Total_min=("Duracao_min", "sum"),
                Tempo_Medio_min=("Duracao_min", "mean"),
            )
        )
    else:
        out = (
            df.groupby("Node", as_index=False)
            .agg(
                Execucoes=(count_col, "count"),
                Tempo_Total_min=("Duracao_min", "sum"),
                Tempo_Medio_min=("Duracao_min", "mean"),
            )
        )

    return out.sort_values("Execucoes", ascending=False)


def heatmap_execs_por_hora(df: pd.DataFrame) -> pd.DataFrame:
    # na prática é “volume por hora”
    if "Hora" not in df.columns:
        return pd.DataFrame(columns=["Hora", "Execuções"])
    base_col = "Código" if "Código" in df.columns else None
    if base_col:
        out = df.groupby("Hora")[base_col].count().reset_index(name="Execuções")
    else:
        out = df.groupby("Hora").size().reset_index(name="Execuções")
    return out.sort_values("Hora")


def variancia_jobs(df: pd.DataFrame, top_n: int = 10) -> pd.DataFrame:
    if "Job" not in df.columns or "Duracao_min" not in df.columns:
        return pd.DataFrame(columns=["Job", "Desvio padrão (min)"])
    out = (
        df.groupby("Job", as_index=False)["Duracao_min"]
        .std()
        .rename(columns={"Duracao_min": "Desvio padrão (min)"})
        .sort_values("Desvio padrão (min)", ascending=False)
        .head(top_n)
    )
    return out


def exec_ambiente(df: pd.DataFrame) -> pd.DataFrame:
    col = "Cenário" if "Cenário" in df.columns else ("Cenario" if "Cenario" in df.columns else None)
    if col is None:
        return pd.DataFrame(columns=["Cenário", "Execuções"])
    return (
        df[col]
        .value_counts()
        .reset_index()
        .rename(columns={"index": "Cenário", col: "Execuções"})
    )


def jobs_long(df: pd.DataFrame, q: float = 0.99) -> pd.DataFrame:
    if "Duracao_min" not in df.columns:
        return pd.DataFrame()
    thr = df["Duracao_min"].quantile(q)
    return df[df["Duracao_min"] > thr].copy()

def contar_por(df: pd.DataFrame, col: str, nome_contagem: str = "Execuções", top: int = 10) -> pd.DataFrame:
    """
    Retorna um DF com colunas:
      - col (ex.: "Job" ou "Cenário")
      - nome_contagem (ex.: "Execuções" ou "Ocorrências")
    """
    out = (
        df[col]
        .astype(str)
        .str.strip()
        .value_counts(dropna=False)
        .head(top)
        .rename_axis(col)              # garante o nome da coluna de categoria
        .reset_index(name=nome_contagem)  # garante o nome da contagem
    )
    return out
# =============================
# Página Streamlit
# =============================
def exibirROI():
    path = get_csv_path()

    if not os.path.exists(path):
        st.error(f"❌ CSV não encontrado em: {path}")
        st.stop()

    df_raw = load_roi_csv(path)
    df = formatacao_csv(df_raw)

    st.title("ROI — Análises de Execução")
    st.caption(f"Fonte: {os.path.basename(path)}")

    # KPIs rápidos
    c1, c2, c3 = st.columns(3)
    c1.metric("Registros", f"{len(df):,}".replace(",", "."))
    if "Duracao_min" in df.columns:
        c2.metric("Tempo total (min)", f"{df['Duracao_min'].fillna(0).sum():.1f}")
        c3.metric("Tempo médio (min)", f"{df['Duracao_min'].dropna().mean():.2f}" if df["Duracao_min"].dropna().size else "—")

    tab1, tab2, tab3, tab4 = st.tabs(["📈 Volume", "⏱️ Tempos", "🖥️ Nodes", "🚨 Outliers"])

    with tab1:
        top_jobs = contar_por(df, "Job", nome_contagem="Execuções", top=10)
        st.subheader("Top 10 Jobs por volume de execuções")
        st.dataframe(top_jobs, use_container_width=True, hide_index=True)

        if not top_jobs.empty:
            fig = px.bar(
                top_jobs,
                x="Job",
                y="Execuções",
                color="Job",
                title="Execuções por Job (Top 10)",
                color_discrete_map=JOB_COLORS
            )

            fig.update_layout(showlegend=False)
            st.plotly_chart(fig, use_container_width=True)

        heat = heatmap_execs_por_hora(df)
        if not heat.empty:
            st.subheader("Execuções por hora do dia")
            figh = px.bar(heat, x="Hora", y="Execuções", title="Execuções por Hora")
            st.plotly_chart(figh, use_container_width=True)

    with tab2:
        tm = tempo_medio_exec(df, top_n=10)
        st.subheader("Top 10 Jobs por tempo médio (min)")
        st.dataframe(tm, use_container_width=True, hide_index=True)

        if not tm.empty:
            fig2 = px.bar(
                tm,
                x="Tempo médio (min)",
                y="Job",
                orientation="h",
                color="Job",
                title="Tempo médio por Job (Top 10)",
                color_discrete_map=JOB_COLORS
            )

            fig2.update_layout(showlegend=False)
            st.plotly_chart(fig2, use_container_width=True)

        var = variancia_jobs(df, top_n=10)
        st.subheader("Top 10 Jobs por instabilidade (desvio padrão)")
        st.dataframe(var, use_container_width=True, hide_index=True)

    with tab3:
        ns = carga_node(df)
        st.subheader("Carga por Node")
        st.dataframe(ns, use_container_width=True, hide_index=True)

        if not ns.empty:
            fig3 = px.bar(ns, x="Node", y="Execucoes", title="Execuções por Node")
            st.plotly_chart(fig3, use_container_width=True)

        amb = contar_por(df, "Cenário", nome_contagem="Execuções", top=50)  # top alto pra não “sumir”

        if not amb.empty:
            st.subheader("Execuções por Cenário")
            fig4 = px.pie(amb, names="Cenário", values="Execuções", title="Distribuição por Cenário")
            st.plotly_chart(fig4, use_container_width=True)

    with tab4:
        outliers = df[df["Duracao_min"] > df["Duracao_min"].quantile(0.99)]
        st.subheader("Outliers (top 1% em duração)")
        st.dataframe(outliers, use_container_width=True, height=420)

        if not outliers.empty and "Job" in outliers.columns:
            top_out = contar_por(outliers, "Job", nome_contagem="Ocorrências", top=10)
            fig5 = px.bar(
                top_out,
                x="Job",
                y="Ocorrências",
                color="Job",
                title="Jobs mais frequentes nos outliers (Top 10)",
                color_discrete_map=JOB_COLORS
            )
            st.plotly_chart(fig5, use_container_width=True)