import pandas as pd
import numpy as np
from scipy import stats
from modules.indices import INDEX_REGISTRY

WAVE_FILES = {
    1: "data/vlna_1.csv",
    2: "data/vlna_2.csv",
    3: "data/vlna_3.csv",
    4: "data/vlna_4.csv",
}
OUTCOME_COL  = "Závažnosť priebehu ochorenia"
EXITUS_LABEL = "Exitus"


# ---------------------------------------------------------------------------
# CLIFF'S DELTA — effect-size metrika
# ---------------------------------------------------------------------------

def compute_cliffs_delta(data1: pd.Series, data2: pd.Series) -> float:
    """
    Vypočíta Cliff's delta [-1, 1].
    Interpretácia: |d| < 0.147 zanedbateľný | 0.147–0.330 malý | 0.330–0.474 stredný | ≥ 0.474 veľký
    """
    n1, n2 = len(data1), len(data2)
    if n1 == 0 or n2 == 0:
        return np.nan
    greater = sum(1 for x in data1 for y in data2 if x > y)
    less    = sum(1 for x in data1 for y in data2 if x < y)
    return float((greater - less) / (n1 * n2))


# ---------------------------------------------------------------------------
# FILTROVANIE OUTLIEROV
# ---------------------------------------------------------------------------

def apply_outlier_filter(
    series: pd.Series,
    method: str,
    iqr_k: float = 1.5,
    zscore_threshold: float = 3.0,
    percentile_low: float = 1.0,
    percentile_high: float = 99.0,
    manual_low: float | None = None,
    manual_high: float | None = None,
) -> pd.Series:
    """
    Filtruje outliery zo série podľa zvolenej metódy.
    Metódy: 'none' | 'iqr' | 'zscore' | 'percentile' | 'manual'
    """
    if method == "none" or series.empty:
        return series
    if method == "iqr":
        q1, q3 = series.quantile(0.25), series.quantile(0.75)
        iqr    = q3 - q1
        return series[(series >= q1 - iqr_k * iqr) & (series <= q3 + iqr_k * iqr)]
    if method == "zscore":
        z = np.abs(stats.zscore(series.dropna()))
        return series[z <= zscore_threshold]
    if method == "percentile":
        lo = series.quantile(percentile_low  / 100)
        hi = series.quantile(percentile_high / 100)
        return series[(series >= lo) & (series <= hi)]
    if method == "manual":
        mask = pd.Series(True, index=series.index)
        if manual_low  is not None: mask &= series >= manual_low
        if manual_high is not None: mask &= series <= manual_high
        return series[mask]
    return series


# ---------------------------------------------------------------------------
# POMOCNÉ FUNKCIE
# ---------------------------------------------------------------------------

def _load_wave(wave_id: int) -> pd.DataFrame:
    path = WAVE_FILES.get(wave_id)
    if not path:
        return pd.DataFrame()
    try:
        return pd.read_csv(path)
    except FileNotFoundError:
        return pd.DataFrame()


def _calc_index(df: pd.DataFrame, index_name: str) -> pd.Series:
    """Vypočíta index a vráti sériu bez NaN a inf."""
    values = pd.to_numeric(INDEX_REGISTRY[index_name](df), errors="coerce")
    return values[np.isfinite(values)].dropna()


def _desc_stats(series: pd.Series, n_pacientov: int | None = None) -> dict:
    return {
        "n":            len(series),
        "n_pacientov":  n_pacientov if n_pacientov is not None else len(series),
        "mean":         float(series.mean()),
        "median":       float(series.median()),
        "q1":           float(series.quantile(0.25)),
        "q3":           float(series.quantile(0.75)),
        "min":          float(series.min()),
        "max":          float(series.max()),
    }


def _last_per_patient(df: pd.DataFrame) -> pd.DataFrame:
    """Vráti posledný záznam (odber) na pacienta."""
    if "Dátum odberu" not in df.columns or "ID" not in df.columns:
        return df
    df = df.copy()
    df["Dátum odberu"] = pd.to_datetime(df["Dátum odberu"], errors="coerce")
    return df.sort_values("Dátum odberu").groupby("ID").tail(1)


def _filter(series: pd.Series, outlier_cfg: dict) -> pd.Series:
    return apply_outlier_filter(series, **outlier_cfg)


def _mann_whitney(data1, data2):
    """Spustí Mann-Whitney U test. Vráti (p_value, cliffs_d) alebo None."""
    if len(data1) < 5 or len(data2) < 5:
        return None
    try:
        _, p = stats.mannwhitneyu(data1, data2, alternative="two-sided")
        return float(p), compute_cliffs_delta(data1, data2)
    except Exception:
        return None


# ---------------------------------------------------------------------------
# TEST — Mann-Whitney medzi vlnami
# ---------------------------------------------------------------------------

def perform_mann_whitney_test(
    df1: pd.DataFrame, df2: pd.DataFrame, index_name: str, outlier_cfg: dict
) -> dict | None:
    """Porovná index medzi dvoma vlnami (všetky záznamy)."""
    if index_name not in INDEX_REGISTRY:
        return None

    raw1, raw2 = _calc_index(df1, index_name), _calc_index(df2, index_name)
    d1,   d2   = _filter(raw1, outlier_cfg),    _filter(raw2, outlier_cfg)

    result = _mann_whitney(d1, d2)
    if result is None:
        return None

    np1 = df1.loc[raw1.index, "ID"].nunique() if "ID" in df1.columns else len(raw1)
    np2 = df2.loc[raw2.index, "ID"].nunique() if "ID" in df2.columns else len(raw2)

    s1, s2 = _desc_stats(d1, np1), _desc_stats(d2, np2)

    p_value, cliffs_d = result
    return {
        "index":           index_name,
        "n_wave1":         s1["n"],        "n_pac_wave1":  s1["n_pacientov"],
        "mean_wave1":      s1["mean"],     "median_wave1": s1["median"],
        "q1_wave1":        s1["q1"],       "q3_wave1":     s1["q3"],
        "min_wave1":       s1["min"],      "max_wave1":    s1["max"],
        "n_wave2":         s2["n"],        "n_pac_wave2":  s2["n_pacientov"],
        "mean_wave2":      s2["mean"],     "median_wave2": s2["median"],
        "q1_wave2":        s2["q1"],       "q3_wave2":     s2["q3"],
        "min_wave2":       s2["min"],      "max_wave2":    s2["max"],
        "p_value":         p_value,
        "cliffs_d":        cliffs_d,
        "significant":     bool(p_value < 0.05),
        "raw_data_wave1":  raw1,  "raw_data_wave2":  raw2,
        "test_data_wave1": d1,    "test_data_wave2": d2,
    }


def perform_mortality_between_waves(
    df1: pd.DataFrame, df2: pd.DataFrame, index_name: str, outlier_cfg: dict,
    skupina1: str = EXITUS_LABEL, skupina2: str = EXITUS_LABEL,
) -> dict | None:
    """Porovná index medzi skupinami (Exitus/Prepustenie) z dvoch vĺn."""
    if index_name not in INDEX_REGISTRY:
        return None

    last1 = _last_per_patient(df1)
    last2 = _last_per_patient(df2)

    grp1 = last1[last1[OUTCOME_COL] == skupina1] if OUTCOME_COL in last1.columns else pd.DataFrame()
    grp2 = last2[last2[OUTCOME_COL] == skupina2] if OUTCOME_COL in last2.columns else pd.DataFrame()

    if grp1.empty or grp2.empty:
        return None

    raw1, raw2 = _calc_index(grp1, index_name), _calc_index(grp2, index_name)
    d1,   d2   = _filter(raw1, outlier_cfg),    _filter(raw2, outlier_cfg)

    result = _mann_whitney(d1, d2)
    if result is None:
        return None

    np1 = grp1.loc[raw1.index, "ID"].nunique() if "ID" in grp1.columns else len(raw1)
    np2 = grp2.loc[raw2.index, "ID"].nunique() if "ID" in grp2.columns else len(raw2)

    p_value, cliffs_d = result
    return {
        "index":           index_name,
        "skupina1":        skupina1,              "skupina2":    skupina2,
        "stats_wave1":     _desc_stats(d1, np1),  "stats_wave2": _desc_stats(d2, np2),
        "p_value":         p_value,         "cliffs_d":        cliffs_d,
        "significant":     bool(p_value < 0.05),
        "raw_data_wave1":  raw1,  "raw_data_wave2":  raw2,
        "test_data_wave1": d1,    "test_data_wave2": d2,
    }


# ---------------------------------------------------------------------------
# ORCHESTRAČNÉ FUNKCIE
# ---------------------------------------------------------------------------

def run_statistical_analysis(
    wave1_id: int, wave2_id: int, selected_indices: list, outlier_cfg: dict
) -> tuple[pd.DataFrame, list, dict]:
    """
    Porovnanie indexov medzi dvoma vlnami (všetky záznamy).
    Vráti (DataFrame výsledkov, zoznam neúspešných indexov, dict dát pre boxploty).
    """
    df1, df2 = _load_wave(wave1_id), _load_wave(wave2_id)
    if df1.empty or df2.empty:
        return pd.DataFrame(), selected_indices, {}

    results, failed, plot_data = [], [], {}

    for idx in selected_indices:
        res = perform_mann_whitney_test(df1, df2, idx, outlier_cfg)
        if res:
            plot_data[idx] = {
                "raw_data_wave1":  res.pop("raw_data_wave1"),
                "raw_data_wave2":  res.pop("raw_data_wave2"),
                "test_data_wave1": res.pop("test_data_wave1"),
                "test_data_wave2": res.pop("test_data_wave2"),
            }
            results.append(res)
        else:
            failed.append(idx)

    return pd.DataFrame(results), failed, plot_data


def run_mortality_between_waves(
    wave1_id: int, wave2_id: int, selected_indices: list, outlier_cfg: dict,
    skupina1: str = EXITUS_LABEL, skupina2: str = EXITUS_LABEL,
) -> tuple[list, list]:
    """
    Porovnanie skupín (Exitus/Prepustenie) medzi dvoma vlnami.
    Vráti (zoznam výsledkov, zoznam neúspešných indexov).
    """
    df1, df2 = _load_wave(wave1_id), _load_wave(wave2_id)
    if df1.empty or df2.empty:
        return [], selected_indices

    results, failed = [], []
    for idx in selected_indices:
        res = perform_mortality_between_waves(df1, df2, idx, outlier_cfg, skupina1, skupina2)
        if res:
            results.append(res)
        else:
            failed.append(idx)

    return results, failed