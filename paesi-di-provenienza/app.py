"""Streamlit dashboard for the foreign markets of the Belluno destination."""

from __future__ import annotations

import importlib.util
import os
from pathlib import Path

import numpy as np
import pandas as pd
import plotly.express as px
import streamlit as st

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(BASE_DIR)
PROCESSED_FILE = os.path.join(PROJECT_ROOT, "data", "processed", "mercati_esteri.csv")
LEGACY_DIR = os.path.join(BASE_DIR, "dati-paesi-di-provenienza")

_etl_spec = importlib.util.spec_from_file_location(
    "foreign_markets_etl", Path(BASE_DIR) / "etl.py"
)
if _etl_spec is None or _etl_spec.loader is None:
    raise ImportError("Impossibile caricare il modulo ETL dei mercati esteri")
_etl = importlib.util.module_from_spec(_etl_spec)
_etl_spec.loader.exec_module(_etl)
MONTHS = _etl.MONTHS
add_winter_season = _etl.add_winter_season
annual_market_comparison = _etl.annual_market_comparison
load_market_data = _etl.load_market_data
real_markets = _etl.real_markets
winter_market_comparison = _etl.winter_market_comparison

ROSE = "#9B3A62"
ROSE_LIGHT = "#D78396"
GOLD = "#D39A5C"
INK = "#26333D"
GREEN = "#287D66"
RED = "#B94A48"


def format_int(value: float | int) -> str:
    return f"{value:,.0f}".replace(",", ".")


def format_pct(value: float | int) -> str:
    if pd.isna(value):
        return "—"
    return f"{value:+.1f}%".replace(".", ",")


def month_range(months: list[int]) -> str:
    if not months:
        return "—"
    if len(months) == 12:
        return "gennaio–dicembre"
    return f"{MONTHS[min(months) - 1].lower()}–{MONTHS[max(months) - 1].lower()}"


def display_table(frame: pd.DataFrame, formats: dict[str, str]) -> None:
    st.dataframe(
        frame.style.format(formats, na_rep="—"),
        width="stretch",
        hide_index=True,
    )


st.set_page_config(
    page_title="Mercati esteri | Dolomiti Bellunesi",
    page_icon="🌍",
    layout="wide",
)
st.markdown(
    f"""
    <style>
      [data-testid="stAppViewContainer"] {{background: #FBFAF8;}}
      [data-testid="stMetric"] {{background: white; border: 1px solid #E9E4DF;
        padding: 14px 16px; border-radius: 12px;}}
      h1, h2, h3 {{color: {INK};}}
      .market-note {{background:#F6EEF1; border-left:5px solid {ROSE};
        padding:12px 16px; border-radius:8px; margin:8px 0 20px 0;}}
      .scope-pill {{display:inline-block; background:{ROSE}; color:white;
        padding:5px 11px; border-radius:999px; font-size:.82rem; font-weight:600;}}
    </style>
    """,
    unsafe_allow_html=True,
)

st.title("Mercati esteri delle Dolomiti Bellunesi")
st.caption(
    "Presenze turistiche per Paese di provenienza · dati ufficiali Regione Veneto"
)

try:
    data, data_source = load_market_data(PROCESSED_FILE, LEGACY_DIR)
except Exception as exc:
    st.error(f"Impossibile caricare i dati dei mercati esteri: {exc}")
    st.stop()

territories = sorted(data["territorio"].dropna().unique())
preferred = "Provincia di Belluno (DMO)"
default_territory = preferred if preferred in territories else territories[0]
territory = st.selectbox(
    "Ambito territoriale",
    territories,
    index=territories.index(default_territory),
    help="La Provincia di Belluno è ottenuta sommando STL Dolomiti e STL Belluno.",
)

if data_source == "archivio":
    st.warning(
        "La dashboard sta usando l’archivio storico non automatizzato. "
        "L’ambito disponibile è soltanto STL Dolomiti e l’ultimo anno può essere parziale."
    )

comparison, metadata = annual_market_comparison(data, territory)
latest = int(metadata["latest"])
previous = int(metadata["previous"])
months = list(metadata["months"])
latest_total = int(metadata["latest_total"])
previous_total = int(metadata["previous_total"])
total_delta = int(metadata["total_delta"])
total_change = total_delta / previous_total * 100 if previous_total else np.nan
top7 = comparison.head(7).copy()
concentration = top7[latest].sum() / latest_total * 100 if latest_total else np.nan

st.markdown(
    f'<span class="scope-pill">{territory}</span>', unsafe_allow_html=True
)
st.markdown(
    f"""
    <div class="market-note">
      Confronto omogeneo <b>{month_range(months)} {latest}</b> rispetto allo stesso periodo
      del {previous}. Le aggregazioni “Altri Paesi” sono escluse dalle classifiche.
    </div>
    """,
    unsafe_allow_html=True,
)

k1, k2, k3, k4 = st.columns(4)
k1.metric("Presenze straniere", format_int(latest_total), format_pct(total_change))
k2.metric("Variazione assoluta", f"{total_delta:+,.0f}".replace(",", "."))
k3.metric("Primo mercato", str(top7.iloc[0]["mercato"]))
k4.metric("Quota dei primi 7", f"{concentration:.1f}%".replace(".", ","))

overview_tab, winter_tab, monthly_tab, portfolio_tab, method_tab = st.tabs(
    [
        "Quadro attuale",
        "Focus inverno",
        "Andamento mensile",
        "Portafoglio mercati",
        "Metodo e qualità",
    ]
)

with overview_tab:
    st.subheader("I mercati che contano di più")
    st.write(
        "La graduatoria combina volume, quota e contributo effettivo alla variazione "
        "complessiva delle presenze straniere."
    )

    table = top7[
        ["mercato", previous, latest, "differenza", "variazione_pct", "quota_pct", "contributo_crescita_pct"]
    ].copy()
    table.columns = [
        "Mercato", str(previous), str(latest), "Differenza", "Variazione %",
        "Quota %", "Contributo alla variazione %",
    ]
    display_table(
        table,
        {
            str(previous): "{:,.0f}", str(latest): "{:,.0f}", "Differenza": "{:+,.0f}",
            "Variazione %": "{:+.1f}%", "Quota %": "{:.1f}%",
            "Contributo alla variazione %": "{:+.1f}%",
        },
    )

    chart_data = comparison.head(10).sort_values(latest)
    chart = px.bar(
        chart_data,
        x=latest,
        y="mercato",
        orientation="h",
        color="variazione_pct",
        color_continuous_scale=[RED, "#E8E2DE", GREEN],
        color_continuous_midpoint=0,
        labels={latest: f"Presenze {latest}", "mercato": "", "variazione_pct": "Var. %"},
        text_auto=",.0f",
    )
    chart.update_layout(height=470, coloraxis_colorbar_title="Var. %", margin=dict(l=10, r=10))
    st.plotly_chart(chart, width="stretch")

    st.download_button(
        "Scarica la tabella dei mercati",
        data=comparison.to_csv(index=False).encode("utf-8"),
        file_name=f"mercati_esteri_{latest}_{territory.lower().replace(' ', '_')}.csv",
        mime="text/csv",
    )

with winter_tab:
    st.subheader("Gli ultimi tre inverni completi")
    st.caption("Inverno = dicembre dell’anno iniziale + gennaio, febbraio e marzo dell’anno successivo.")
    try:
        winter_table, winter_totals, seasons = winter_market_comparison(
            data, territory, seasons_count=3, top_n=7
        )
        latest_winter, previous_winter = seasons[-1], seasons[-2]
        winter_delta = int(winter_totals[latest_winter] - winter_totals[previous_winter])
        winter_change = (
            winter_delta / winter_totals[previous_winter] * 100
            if winter_totals[previous_winter]
            else np.nan
        )
        winter_concentration = (
            winter_table[latest_winter].sum() / winter_totals[latest_winter] * 100
        )

        w1, w2, w3 = st.columns(3)
        w1.metric(
            f"Presenze estere inverno {latest_winter}",
            format_int(winter_totals[latest_winter]),
            format_pct(winter_change),
        )
        w2.metric("Primo mercato invernale", winter_table.iloc[0]["mercato"])
        w3.metric("Quota dei primi 7", f"{winter_concentration:.1f}%".replace(".", ","))

        winter_long = winter_table[["mercato", *seasons]].melt(
            id_vars="mercato", var_name="Inverno", value_name="Presenze"
        )
        winter_chart = px.bar(
            winter_long,
            x="mercato",
            y="Presenze",
            color="Inverno",
            barmode="group",
            color_discrete_sequence=["#CAB9C0", ROSE_LIGHT, ROSE],
            labels={"mercato": "", "Presenze": "Presenze"},
        )
        winter_chart.update_layout(height=470, legend_title_text="Inverno")
        st.plotly_chart(winter_chart, width="stretch")

        winter_display = winter_table[
            ["mercato", *seasons, "differenza", "variazione_pct", "quota_pct", "contributo_crescita_pct"]
        ].copy()
        winter_display.columns = [
            "Mercato", *seasons, "Differenza ultimo inverno", "Variazione %",
            "Quota %", "Contributo alla variazione %",
        ]
        display_table(
            winter_display,
            {
                **{season: "{:,.0f}" for season in seasons},
                "Differenza ultimo inverno": "{:+,.0f}", "Variazione %": "{:+.1f}%",
                "Quota %": "{:.1f}%", "Contributo alla variazione %": "{:+.1f}%",
            },
        )

        latest_markets = winter_table["mercato"].tolist()
        winter_rows = add_winter_season(real_markets(data))
        profile = (
            winter_rows[
                (winter_rows["territorio"] == territory)
                & (winter_rows["stagione"] == latest_winter)
                & (winter_rows["mercato"].isin(latest_markets))
            ]
            .groupby(["mese_num", "mese"], observed=True)["presenze"]
            .sum()
            .reset_index()
            .sort_values("mese_num", key=lambda values: values.map({12: 0, 1: 1, 2: 2, 3: 3}))
        )
        profile_chart = px.line(
            profile,
            x="mese",
            y="presenze",
            markers=True,
            labels={"mese": "", "presenze": "Presenze dei primi 7 mercati"},
        )
        profile_chart.update_traces(line_color=GOLD, line_width=4, marker_size=9)
        profile_chart.update_layout(height=320)
        st.plotly_chart(profile_chart, width="stretch")
    except ValueError as exc:
        st.info(str(exc))

with monthly_tab:
    st.subheader("Andamento mensile per mercato")
    actual = real_markets(data)
    market_options = sorted(actual.loc[actual["territorio"] == territory, "mercato"].unique())
    default_markets = [market for market in comparison.head(5)["mercato"] if market in market_options]
    selected_markets = st.multiselect("Mercati", market_options, default=default_markets)

    available_years = sorted(int(year) for year in data["anno"].unique())
    default_years = available_years[-3:]
    selected_years = st.multiselect("Anni", available_years, default=default_years)
    monthly = actual[
        (actual["territorio"] == territory)
        & (actual["mercato"].isin(selected_markets))
        & (actual["anno"].isin(selected_years))
    ]
    if monthly.empty:
        st.info("Seleziona almeno un mercato e un anno.")
    else:
        monthly_chart = px.line(
            monthly,
            x="mese",
            y="presenze",
            color="mercato",
            line_dash="anno",
            markers=True,
            category_orders={"mese": MONTHS},
            labels={"mese": "", "presenze": "Presenze", "mercato": "Mercato", "anno": "Anno"},
        )
        monthly_chart.update_layout(height=520)
        st.plotly_chart(monthly_chart, width="stretch")

with portfolio_tab:
    st.subheader("Volume e dinamica dei mercati")
    st.write(
        "La posizione mostra contemporaneamente il peso del mercato e la sua variazione. "
        "Sono etichettati i primi 15 mercati per volume."
    )
    portfolio = comparison.head(15).copy()
    portfolio["presenze_correnti"] = portfolio[latest]
    portfolio["presenze_precedenti"] = portfolio[previous]
    portfolio["dimensione"] = np.sqrt(portfolio[latest].clip(lower=1))
    scatter = px.scatter(
        portfolio,
        x="quota_pct",
        y="variazione_pct",
        size="dimensione",
        color="differenza",
        text="mercato",
        color_continuous_scale=[RED, "#E8E2DE", GREEN],
        color_continuous_midpoint=0,
        labels={
            "quota_pct": f"Quota sulle presenze straniere {latest} (%)",
            "variazione_pct": f"Variazione {previous}–{latest} (%)",
            "differenza": "Differenza",
            "presenze_correnti": f"Presenze {latest}",
            "presenze_precedenti": f"Presenze {previous}",
        },
        hover_data={
            "presenze_correnti": ":,.0f",
            "presenze_precedenti": ":,.0f",
            "dimensione": False,
        },
    )
    scatter.add_hline(y=0, line_dash="dot", line_color="#888")
    scatter.update_traces(textposition="top center")
    scatter.update_layout(height=600, showlegend=False)
    st.plotly_chart(scatter, width="stretch")

    threshold = latest_total * 0.005
    expanding = comparison[
        (comparison[latest] >= threshold) & (comparison["variazione_pct"] > 0)
    ].sort_values("differenza", ascending=False).head(10)
    st.markdown("#### Mercati in espansione con massa critica")
    st.caption("Sono inclusi i mercati con almeno lo 0,5% delle presenze straniere del periodo.")
    expanding_display = expanding[["mercato", latest, "differenza", "variazione_pct", "quota_pct"]].copy()
    expanding_display.columns = ["Mercato", str(latest), "Differenza", "Variazione %", "Quota %"]
    display_table(
        expanding_display,
        {str(latest): "{:,.0f}", "Differenza": "{:+,.0f}", "Variazione %": "{:+.1f}%", "Quota %": "{:.1f}%"},
    )

with method_tab:
    st.subheader("Metodo, perimetro e qualità")
    st.markdown(
        """
        - **Fonte:** Regione del Veneto – U.O. Sistema Statistico Regionale, dati Istat.
        - **Indicatore:** presenze, cioè pernottamenti nelle strutture ricettive.
        - **Provincia di Belluno (DMO):** somma delle serie ufficiali di STL Dolomiti e STL Belluno.
        - **Mercati reali:** le classifiche escludono “Totale stranieri” e le aggregazioni “Altri Paesi”.
        - **Confronti annuali:** l’anno più recente è confrontato con l’anno precedente sugli stessi mesi disponibili.
        - **Inverno:** dicembre–marzo; sono considerate soltanto stagioni con tutti e quattro i mesi disponibili.
        - **Contributo alla variazione:** differenza del singolo mercato divisa per la variazione complessiva delle presenze straniere.
        - **Stato dei dati:** l’anno corrente è provvisorio; gli anni precedenti sono definitivi secondo la fonte.
        """
    )
    latest_month = int(data.loc[data["anno"] == data["anno"].max(), "mese_num"].max())
    st.info(
        f"Ultimo periodo disponibile nel dataset: {MONTHS[latest_month - 1]} "
        f"{int(data['anno'].max())}. Modalità di alimentazione: {data_source}."
    )

st.markdown("---")
st.caption("Fondazione DMO Dolomiti Bellunesi · Dashboard interna")
