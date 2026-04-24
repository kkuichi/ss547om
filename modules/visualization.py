import pandas as pd
import numpy as np
import plotly.graph_objects as go
from modules.indices import INDEX_THRESHOLDS

# Vstupné komponenty vybraných indexov pre hover tooltip
_INDEX_COMPONENTS = {
    "NLR":              ("Neu abs", "Ly abs"),
    "PLR":              ("PLT",     "Ly abs"),
    "dNLR":             ("Neu abs", "WBC"),
    "SII":              ("PLT",     "Neu abs"),
    "CAR":              ("S-CRP",   "S-Alb"),
    "CLR":              ("S-CRP",   "Ly abs"),
    "Ferritin/Ly":      ("S-FER",   "Ly abs"),
    "FAR":              ("Fib",   "S-Alb"),
    "BUN/Cr":           ("S-Urea",   "S-Kreat"),
    "De Ritis":         ("S-AST",   "S-ALT"),
    "AST/PLT":          ("S-AST",   "PLT"),
    "LDH/Albumin":      ("S-LD",   "S-Alb"),
    "DLR":              ("D-dimér HS",   "Ly abs"),
    "D-Dimér/Albumin":  ("D-dimér HS",   "S-Alb"),
    "Fibrinogen/Ly":    ("Fib",   "Ly abs"),
    "PLT/Fibrinogen":   ("PLT",   "Fib"),
    "BLR":              ("S-PBNP",   "Ly abs"),

}


def plot_patient_index_trend(p_data: pd.DataFrame, index_name: str) -> go.Figure:
    """
    Časový vývoj indexu pre jedného pacienta.
    """
    p_data = p_data.dropna(subset=[index_name]).copy()
    if p_data.empty:
        return go.Figure()

    p_data["Dátum odberu"] = pd.to_datetime(p_data["Dátum odberu"]).dt.date
    p_data = p_data.sort_values("Dátum odberu")

    thresh = INDEX_THRESHOLDS.get(index_name, {})
    low    = thresh.get("low")
    high   = thresh.get("high")
    comp_a, comp_b = _INDEX_COMPONENTS.get(index_name, (None, None))

    fig = go.Figure()

    if low is not None and high is not None:
        y_max = max(p_data[index_name].max() * 1.2, high * 1.5)
        fig.add_hrect(y0=0,    y1=low,  fillcolor="rgba(231,76,60,0.1)",   line_width=0)
        fig.add_hrect(y0=low,  y1=high, fillcolor="rgba(46,204,113,0.2)",  line_width=0)
        fig.add_hrect(y0=high, y1=y_max,fillcolor="rgba(231,76,60,0.1)",   line_width=0)

    colors = []
    for val in p_data[index_name]:
        out = (low is not None and val < low) or (high is not None and val > high)
        colors.append("#c0392b" if out else "#27ae60")

    hover = []
    for _, row in p_data.iterrows():
        datum = pd.to_datetime(row["Dátum odberu"]).strftime("%d.%m.%Y")
        text  = f"<b>{datum}</b><br><b>{index_name}: {row[index_name]:.2f}</b><br>"
        for comp in [comp_a, comp_b]:
            if comp and pd.notna(row.get(comp)):
                text += f"{comp}: {row[comp]:.2f}<br>"
        hover.append(text)

    fig.add_trace(go.Scatter(
        x=p_data["Dátum odberu"].astype(str),
        y=p_data[index_name],
        mode="lines+markers",
        text=hover,
        hoverinfo="text",
        line=dict(color="#2c3e50", width=3),
        marker=dict(size=12, color=colors, line=dict(width=2, color="white")),
    ))

    fig.update_layout(
        title=f"Index {index_name}",
        xaxis=dict(
            title="Dátum odberu",
            type="category",
        ),
        yaxis_title=f"Hodnota {index_name}",
        template="plotly_white",
        height=400,
    )

    if len(p_data) == 1:
        fig.update_traces(mode="markers")

    return fig


def plot_mortality_trend(df: pd.DataFrame) -> go.Figure:
    """
    Kumulatívna krivka exitov a prepustených podľa dĺžky hospitalizácie.
    Hover obsahuje: deň, počet nových udalostí, kumulatív, % z celku, priemerný vek.
    """
    if df.empty:
        fig = go.Figure()
        fig.add_annotation(text="Žiadne dáta", showarrow=False)
        return fig

    df = df.copy()
    df["Dĺžka hospitalizácie"] = pd.to_numeric(df["Dĺžka hospitalizácie"], errors="coerce")
    df["Vek"]                  = pd.to_numeric(df["Vek"], errors="coerce")
    df = df.dropna(subset=["Dĺžka hospitalizácie", "Závažnosť priebehu ochorenia"])

    if df.empty:
        fig = go.Figure()
        fig.add_annotation(text="Žiadne validné dáta pre zobrazenie", showarrow=False)
        return fig

    fig = go.Figure()

    categories = [
        ("Prepustenie", "#2ecc71", "rgba(46,204,113,0.1)", "tozeroy"),
        ("Exitus",      "#e74c3c", None,                   None),
    ]

    for status, color, fill_color, fill_mode in categories:
        subset = df[df["Závažnosť priebehu ochorenia"] == status].copy()
        if subset.empty:
            continue

        daily = (
            subset.groupby("Dĺžka hospitalizácie")
            .agg(count=("ID", "count"), avg_vek=("Vek", "mean"))
            .reset_index()
            .rename(columns={"Dĺžka hospitalizácie": "day"})
        )
        daily["cumulative"] = daily["count"].cumsum()
        total = int(daily["cumulative"].iloc[-1])

        hover = []
        for _, row in daily.iterrows():
            day, cum, cnt = int(row["day"]), int(row["cumulative"]), int(row["count"])
            pct     = cum / total * 100 if total else 0
            akcia   = "Exitus" if status == "Exitus" else "Prepustených"
            vek_str = f"Priemerný vek: {row['avg_vek']:.0f} r." if pd.notna(row["avg_vek"]) else ""
            hover.append(
                f"<b>Deň hospitalizácie: {day}</b><br>"
                f"{akcia} v tento deň: {cnt}<br>"
                f"Kumulatívne: {cum}<br>"
                f"Podiel z celku: {pct:.1f}%<br>{vek_str}"
            )

        fig.add_trace(go.Scatter(
            x=daily["day"].astype(int).values,
            y=daily["cumulative"].values,
            mode="lines+markers",
            name=status,
            line=dict(color=color, width=4, shape="spline"),
            marker=dict(size=8, color=color, line=dict(width=2, color="white")),
            hovertext=hover,
            hoverinfo="text",
            fill=fill_mode,
            fillcolor=fill_color,
        ))

    fig.update_layout(
        title=dict(text="<b>Krivka mortality</b>", font=dict(size=25, color="#1a1a1a")),
        xaxis=dict(title="<b>Dĺžka hospitalizácie (dni)</b>", showgrid=True,
                   gridcolor="rgba(200,200,200,0.2)", zeroline=False, dtick=5),
        yaxis=dict(title="<b>Počet pacientov</b>", showgrid=True,
                   gridcolor="rgba(200,200,200,0.2)", zeroline=False),
        hovermode="x unified",
        template="plotly_white",
        height=500,
        legend=dict(orientation="v", yanchor="top", y=0.99, xanchor="left", x=0.01,
                    bgcolor="rgba(255,255,255,0.85)", bordercolor="rgba(0,0,0,0.15)",
                    borderwidth=1, font=dict(size=12)),
        plot_bgcolor="rgba(245,245,245,0.5)",
        font=dict(family="Arial, sans-serif", size=12, color="#333"),
        margin=dict(l=80, r=20, t=100, b=80),
    )
    return fig


def compute_mortality_stats(df: pd.DataFrame) -> dict:
    """
    Štatistiky pre skupiny Exitus a Prepustenie.
    Vráti dict s kľúčmi 'exitus' a 'prepustenie'.
    """
    df = df.copy()
    df["Dĺžka hospitalizácie"] = pd.to_numeric(df["Dĺžka hospitalizácie"], errors="coerce")
    df["Vek"]                  = pd.to_numeric(df["Vek"], errors="coerce")

    result = {}
    for skupina, label in [("Exitus", "exitus"), ("Prepustenie", "prepustenie")]:
        subset = df[df["Závažnosť priebehu ochorenia"] == skupina]
        if subset.empty:
            result[label] = None
            continue

        hosp = subset["Dĺžka hospitalizácie"].dropna()
        vek  = subset["Vek"].dropna()
        pc   = subset["Pohlavie"].value_counts()
        muz  = int(pc.get("Muž", pc.get("M", 0)))
        zena = int(pc.get("Žena", pc.get("F", pc.get("Ž", 0))))
        total_p = max(muz + zena, len(subset), 1)

        result[label] = {
            "n":           len(subset),
            "hosp_mean":   round(float(hosp.mean()),   1) if len(hosp) else None,
            "hosp_median": round(float(hosp.median()), 1) if len(hosp) else None,
            "hosp_min":    int(hosp.min())               if len(hosp) else None,
            "hosp_max":    int(hosp.max())               if len(hosp) else None,
            "vek_mean":    round(float(vek.mean()),   1) if len(vek) else None,
            "vek_median":  round(float(vek.median()), 1) if len(vek) else None,
            "vek_min":     int(vek.min())               if len(vek) else None,
            "vek_max":     int(vek.max())               if len(vek) else None,
            "muz_n":       muz,
            "zena_n":      zena,
            "muz_pct":     round(muz  / total_p * 100, 1),
            "zena_pct":    round(zena / total_p * 100, 1),
        }
    return result


def compute_index_benchmark(
    wave_df: pd.DataFrame,
    index_name: str,
    pohlavie: str,
    vek: int,
    zavaznost: str,
    index_fn: callable,
    vek_pasmo: int = 5,
) -> dict | None:
    """
    Štatistiky indexu z historických dát pre referenčnú skupinu:
    rovnaké pohlavie, podobný vek (±vek_pasmo), rovnaká závažnosť.
    Vráti None ak je príliš málo dát (< 3 záznamov).
    """
    mask = (
        (wave_df["Pohlavie"] == pohlavie)
        & (wave_df["Vek"].between(vek - vek_pasmo, vek + vek_pasmo))
        & (wave_df["Závažnosť priebehu ochorenia"] == zavaznost)
    )
    filtered = wave_df[mask].copy()
    if filtered.empty:
        return None

    n_skupina = filtered["ID"].nunique() if "ID" in filtered.columns else len(filtered)

    try:
        values = pd.to_numeric(index_fn(filtered), errors="coerce").dropna()
        values = values[np.isfinite(values)]
    except Exception:
        return None

    if len(values) < 3:
        return None

    n_zaznamov  = len(values)
    n_pacientov = filtered.loc[values.index, "ID"].nunique() if "ID" in filtered.columns else n_zaznamov

    return {
        "n":          n_pacientov,
        "n_skupina":  n_skupina,
        "n_zaznamov": n_zaznamov,
        "mean":    round(float(values.mean()),           2),
        "median":  round(float(values.median()),         2),
        "q1":      round(float(values.quantile(0.25)),   2),
        "q3":      round(float(values.quantile(0.75)),   2),
        "min":     round(float(values.min()),            2),
        "max":     round(float(values.max()),            2),
        "vek_od":  vek - vek_pasmo,
        "vek_do":  vek + vek_pasmo,
    }