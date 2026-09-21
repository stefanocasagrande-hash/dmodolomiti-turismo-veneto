"""Calcolo della classifica annuale delle presenze nei Comuni."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

import pandas as pd


MONTH_ORDER = ["Gen", "Feb", "Mar", "Apr", "Mag", "Giu", "Lug", "Ago", "Set", "Ott", "Nov", "Dic"]


@dataclass(frozen=True)
class ComuniRanking:
    """Risultato e metadati del confronto tra due anni consecutivi."""

    data: pd.DataFrame
    target_year: int
    comparison_year: int
    months: list[str]
    eligible_municipalities: int
    excluded_municipalities: int


def build_comuni_ranking(
    data: pd.DataFrame,
    target_year: int,
    selected_months: Iterable[str] | None = None,
) -> ComuniRanking:
    """Confronta le presenze del target con lo stesso periodo dell'anno prima.

    Sono ammessi in classifica solo i Comuni con tutti i mesi richiesti presenti
    in entrambi gli anni. Questo evita che un mese mancante venga interpretato
    come uno zero e alteri la variazione percentuale.
    """

    comparison_year = int(target_year) - 1
    requested_months = set(selected_months if selected_months is not None else MONTH_ORDER)

    target_months = set(
        data.loc[data["anno"].eq(target_year), "mese"].dropna().astype(str)
    )
    months = [
        month
        for month in MONTH_ORDER
        if month in requested_months and month in target_months
    ]

    empty_columns = [
        "comune",
        "previous_value",
        "current_value",
        "difference",
        "variation_pct",
    ]
    if not months:
        return ComuniRanking(
            data=pd.DataFrame(columns=empty_columns),
            target_year=int(target_year),
            comparison_year=comparison_year,
            months=[],
            eligible_municipalities=0,
            excluded_municipalities=0,
        )

    comparison = data[
        data["anno"].isin([comparison_year, target_year])
        & data["mese"].isin(months)
    ].copy()

    target_municipalities = set(
        comparison.loc[comparison["anno"].eq(target_year), "comune"]
    )
    completeness = (
        comparison.groupby(["comune", "anno"])["mese"]
        .nunique()
        .unstack("anno", fill_value=0)
        .reindex(columns=[comparison_year, target_year], fill_value=0)
    )
    eligible = completeness[
        completeness[comparison_year].eq(len(months))
        & completeness[target_year].eq(len(months))
    ].index

    totals = (
        comparison[comparison["comune"].isin(eligible)]
        .groupby(["comune", "anno"])["presenze"]
        .sum()
        .unstack("anno")
        .reindex(columns=[comparison_year, target_year])
    )
    totals = totals[totals[comparison_year].gt(0)].copy()

    ranking = pd.DataFrame(
        {
            "comune": totals.index,
            "previous_value": totals[comparison_year].astype(int),
            "current_value": totals[target_year].astype(int),
        }
    ).reset_index(drop=True)
    ranking["difference"] = ranking["current_value"] - ranking["previous_value"]
    ranking["variation_pct"] = (
        ranking["difference"] / ranking["previous_value"] * 100
    )
    ranking = ranking.sort_values(
        ["variation_pct", "difference", "comune"],
        ascending=[False, False, True],
        kind="stable",
    ).reset_index(drop=True)

    eligible_count = len(ranking)
    return ComuniRanking(
        data=ranking,
        target_year=int(target_year),
        comparison_year=comparison_year,
        months=months,
        eligible_municipalities=eligible_count,
        excluded_municipalities=max(len(target_municipalities) - eligible_count, 0),
    )
