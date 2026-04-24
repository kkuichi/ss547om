import streamlit as st
import pandas as pd
from modules.indices import INDEX_REGISTRY, INDEX_GROUPS, INDEX_THRESHOLDS

# Klinické testy zobrazené vo filtri v bočnom paneli
CLINICAL_FILTER_TESTS = {
    "S-CRP":      (0.1,  5.0,   "mg/l",   "C-reaktívny proteín",  2),
    "S-IL6":      (1.5,  7.0,   "ng/l",   "Interleukín-6",        2),
    "S-FER":      (11,   307,   "µg/l",   "Feritín",              1),
    "D-dimér HS": (0.03, 0.5,   "mg/l",   "D-dimér",              3),
    "Neu abs":    (1.4,  6.5,   "×10⁹/l", "Neutrofily (abs.)",    2),
    "Ly abs":     (1.5,  4.0,   "×10⁹/l", "Lymfocyty (abs.)",     2),
    "PLT":        (150,  400,   "×10⁹/l", "Trombocyty",           "int"),
    "WBC":        (4.0,  10.0,  "×10⁹/l", "Leukocyty",            2),
    "S-Kreat":    (49,   104,   "µmol/l", "Kreatinín",            2),
    "S-Alb":      (35,   52,    "g/l",    "Albumín",              2),
    "PT (INR)":   (0.85, 1.15,  "ratio",  "Protrombínový čas",    2),
    "S-AST":      (0.05, 0.85,  "µkat/l", "AST",                  2),
    "S-ALT":      (0.05, 0.85,  "µkat/l", "ALT",                  2),
}


# ---------------------------------------------------------------------------
# POMOCNÉ FUNKCIE
# ---------------------------------------------------------------------------

def _col_range(df: pd.DataFrame, col: str) -> tuple:
    """Vráti (min, max) pre číselný stĺpec, alebo (None, None)."""
    s = pd.to_numeric(df.get(col, pd.Series()), errors="coerce").dropna()
    return (float(s.min()), float(s.max())) if not s.empty else (None, None)


def _fmt_val(val, fmt):
    return int(round(val)) if fmt == "int" else round(val, fmt)


def _apply_date_mask(mask, date_range, col: str, df: pd.DataFrame):
    """Aplikuje dátumový filter na masku."""
    if col not in df.columns or not isinstance(date_range, (list, tuple)) or len(date_range) < 2:
        return mask
    series = pd.to_datetime(df[col], errors="coerce")
    return mask & series.between(pd.Timestamp(date_range[0]), pd.Timestamp(date_range[1]))


# ---------------------------------------------------------------------------
# INDEX FILTER — preset tlačidlá + vlastný rozsah
# ---------------------------------------------------------------------------

def _render_index_filter(idx_name: str, df: pd.DataFrame, w_key: str):
    """
    Vykreslí filter pre jeden index (preset tlačidlá + vlastný rozsah).
    Vráti (i_min, i_max) alebo None ak nie je aktívny filter.
    """
    try:
        series = INDEX_REGISTRY[idx_name](df).dropna()
    except Exception:
        st.caption(f"⚠️ {idx_name}: Chyba výpočtu")
        return None

    if series.empty:
        st.caption(f"⚠️ {idx_name}: Nedostatok dát")
        return None

    data_min = float(series.min())
    data_max = float(series.max())
    thresh   = INDEX_THRESHOLDS.get(idx_name, {})
    ref_low  = thresh.get("low")
    ref_high = thresh.get("high")
    unit     = thresh.get("unit", "")

    unit_str = f" ({unit})" if unit else ""

    # Bez definovaných noriem — iba rozsah
    if ref_low is None or ref_high is None:
        st.write(f"**{idx_name}**{unit_str} | *norma nedefinovaná*")
        c1, c2 = st.columns(2)
        i_min = c1.number_input("od", value=data_min, format="%.4f", key=f"imin_{idx_name}_{w_key}")
        i_max = c2.number_input("do", value=data_max, format="%.4f", key=f"imax_{idx_name}_{w_key}")
        return (i_min, i_max)

    st.write(f"**{idx_name}**{unit_str} | ref: {ref_low} – {ref_high}")

    preset_key = f"preset_{idx_name}_{w_key}"
    if preset_key not in st.session_state:
        st.session_state[preset_key] = "Všetky"

    current = st.session_state[preset_key]
    preset_map = {"Pod normou": "Pod normou", "V norme": "V norme",
                  "Nad normou": "Nad normou", "Vlastný rozsah": "Vlastný"}

    for label, val in preset_map.items():
        if st.button(label, key=f"btn_{label}_{idx_name}_{w_key}",
                     use_container_width=True,
                     type="primary" if current == val else "secondary"):
            st.session_state[preset_key] = val
            st.rerun()

    if current == "Pod normou":
        st.caption(f"< {ref_low}")
        return (data_min, ref_low)
    if current == "V norme":
        st.caption(f"{ref_low} – {ref_high}")
        return (ref_low, ref_high)
    if current == "Nad normou":
        st.caption(f"> {ref_high}")
        return (ref_high, data_max)
    if current == "Vlastný":
        c1, c2 = st.columns(2)
        i_min = c1.number_input("od", value=data_min, format="%.4f", key=f"imin_{idx_name}_{w_key}")
        i_max = c2.number_input("do", value=data_max, format="%.4f", key=f"imax_{idx_name}_{w_key}")
        return (i_min, i_max)

    return None


# ---------------------------------------------------------------------------
# SIDEBAR — ŠTANDARDNÉ FILTRE (Databáza, Analýza indexov, Krivka mortality)
# ---------------------------------------------------------------------------

def render_sidebar_filters(df: pd.DataFrame):
    """
    Vykreslí štandardné filtre v sidebare (vlna, demografia, dátumy, testy, indexy).
    Zobrazuje sa len pre záložky: Databáza pacientov, Analýza indexov, Krivka mortality.
    Vráti (vyfiltrovaný DataFrame, zvolená vlna).
    """
    if df is None:
        return df, st.session_state.get("current_wave", 1)

    res_key = st.session_state.get("editor_key", 0)
    st.sidebar.title("Filtre")

    # Výber vlny
    current_wave = st.session_state.get("current_wave", 1)
    wave = st.sidebar.selectbox(
        "Vlna pandémie",
        options=[1, 2, 3, 4],
        index=[1, 2, 3, 4].index(current_wave) if current_wave in [1, 2, 3, 4] else 0,
        format_func=lambda x: f"Vlna {x}",
    )
    if wave != current_wave:
        return df, wave
    if df.empty:
        return df, wave

    w_key = f"w{wave}_r{res_key}"

    # --- DEMOGRAFICKÉ FILTRE ---
    with st.sidebar.expander("Demografické údaje", expanded=False, key=f"exp_demo_{res_key}"):
        all_ids     = sorted(df["ID"].unique(), key=lambda x: int(x) if str(x).isdigit() else x)
        search_ids  = st.multiselect("ID pacienta:", options=all_ids, key=f"ids_{w_key}")

        st.write("Pohlavie:")
        c_m, c_z   = st.columns(2)
        m_checked  = c_m.checkbox("Muž",  value=True, key=f"m_{w_key}")
        z_checked  = c_z.checkbox("Žena", value=True, key=f"z_{w_key}")

        st.write("Závažnosť priebehu:")
        outcomes          = [o for o in df["Závažnosť priebehu ochorenia"].unique() if pd.notna(o)]
        selected_outcomes = [o for o in outcomes if st.checkbox(str(o), value=True, key=f"out_{o}_{w_key}")]

        vek_s   = df["Vek"].dropna()
        min_age = int(vek_s.min()) if not vek_s.empty else 0
        max_age = int(vek_s.max()) if not vek_s.empty else 120
        st.write("Vek:")
        ca1, ca2 = st.columns(2)
        age_min  = ca1.number_input("od", 0, 120, min_age, key=f"age_min_{w_key}")
        age_max  = ca2.number_input("do", 0, 120, max_age, key=f"age_max_{w_key}")

        dur_s   = pd.to_numeric(df["Dĺžka hospitalizácie"], errors="coerce").dropna()
        min_dur = int(dur_s.min()) if not dur_s.empty else 0
        max_dur = int(dur_s.max()) if not dur_s.empty else 365
        st.write("Dĺžka hospitalizácie (dni):")
        cd1, cd2 = st.columns(2)
        dur_min  = cd1.number_input("od", 0, 1000, min_dur, key=f"dur_min_{w_key}")
        dur_max  = cd2.number_input("do", 0, 1000, max_dur, key=f"dur_max_{w_key}")

    # --- DÁTUMOVÉ FILTRE ---
    with st.sidebar.expander("Dátumy", expanded=False, key=f"exp_dates_{res_key}"):
        def _date_ui(label, col):
            if col not in df.columns:
                return None
            dates = pd.to_datetime(df[col], errors="coerce").dropna()
            if dates.empty:
                return None
            st.write(f"{label}:")
            return st.date_input(label, value=(dates.min().date(), dates.max().date()),
                                 label_visibility="collapsed", key=f"date_{col}_{w_key}")

        dr_odber       = _date_ui("Dátum odberu",      "Dátum odberu")
        dr_prijem      = _date_ui("Dátum príjmu",      "Dátum príjmu")
        dr_prepustenie = _date_ui("Dátum prepustenia", "Dátum prepustenia")

    # --- KLINICKÉ TESTY ---
    with st.sidebar.expander("Klinické testy", expanded=False, key=f"exp_tests_{res_key}"):
        available = [t for t in CLINICAL_FILTER_TESTS if t in df.columns]
        selected  = st.multiselect("Vybrať testy:", options=available,
                                   format_func=lambda t: f"{t}  ({CLINICAL_FILTER_TESTS[t][3]})",
                                   key=f"sel_tests_{w_key}")
        test_ranges = {}
        for test in selected:
            ref_min, ref_max, unit, label, fmt = CLINICAL_FILTER_TESTS[test]
            d_min, d_max = _col_range(df, test)
            if d_min is None:
                continue
            num_fmt = "%d" if fmt == "int" else f"%.{fmt}f"
            st.write(f"**{test}** ({unit}) | ref: {ref_min}–{ref_max}")
            tc1, tc2 = st.columns(2)
            t_min = tc1.number_input("od", value=_fmt_val(d_min, fmt), format=num_fmt, key=f"tmin_{test}_{w_key}")
            t_max = tc2.number_input("do", value=_fmt_val(d_max, fmt), format=num_fmt, key=f"tmax_{test}_{w_key}")
            test_ranges[test] = (t_min, t_max)

    # --- KLINICKÉ INDEXY ---
    with st.sidebar.expander("Klinické indexy", expanded=False, key=f"exp_indices_{res_key}"):
        index_ranges = {}
        for group_name, group_fns in INDEX_GROUPS.items():
            st.markdown(f"**{group_name}**")
            selected_in_group = st.multiselect("Vybrať indexy:", options=list(group_fns.keys()),
                                               key=f"sel_indices_{group_name}_{w_key}",
                                               label_visibility="collapsed")
            for idx_name in selected_in_group:
                st.divider()
                result = _render_index_filter(idx_name, df, w_key)
                if result is not None:
                    index_ranges[idx_name] = result
            st.markdown("")

    # --- RESET ---
    st.sidebar.markdown("---")
    if st.sidebar.button("Reset filtrov", use_container_width=True):
        _reset_filter_state()
        st.rerun()

    # --- APLIKÁCIA FILTROV ---
    pohlavie_filter = (["M"] if m_checked else []) + (["Ž"] if z_checked else [])
    selected_outcomes_ext = selected_outcomes + [None, float("nan"), "nan", ""]

    mask = (
        df["Pohlavie"].isin(pohlavie_filter)
        & df["Vek"].between(age_min, age_max)
        & df["Závažnosť priebehu ochorenia"].isin(selected_outcomes_ext)
        & pd.to_numeric(df["Dĺžka hospitalizácie"], errors="coerce").between(dur_min, dur_max)
    )

    if search_ids:
        mask &= df["ID"].isin(search_ids)

    mask = _apply_date_mask(mask, dr_odber,       "Dátum odberu",      df)
    mask = _apply_date_mask(mask, dr_prijem,       "Dátum príjmu",      df)
    mask = _apply_date_mask(mask, dr_prepustenie,  "Dátum prepustenia", df)

    for test, (t_min, t_max) in test_ranges.items():
        mask &= pd.to_numeric(df[test], errors="coerce").between(t_min, t_max)

    for idx_name, (i_min, i_max) in index_ranges.items():
        try:
            mask &= INDEX_REGISTRY[idx_name](df).between(i_min, i_max)
        except Exception:
            pass

    return df[mask].copy(), wave


# ---------------------------------------------------------------------------
# SIDEBAR — FILTER PRE ŠTATISTICKÚ ANALÝZU
# ---------------------------------------------------------------------------

def render_sidebar_stat_filters() -> dict:
    """
    Vykreslí v sidebare iba nastavenia filtrovania odľahlých hodnôt.
    Zobrazuje sa výhradne pre záložku Štatistická analýza.
    Vráti outlier_cfg dict kompatibilný so statistical_tests funkciami.
    """
    st.sidebar.title("Nastavenia analýzy")

    with st.sidebar.expander("Filtrovanie outlierov", expanded=True):
        outlier_method = st.radio(
            "Metóda:",
            options=["none", "iqr", "zscore", "percentile", "manual"],
            format_func=lambda x: {
                "none":       "Bez filtrovania",
                "iqr":        "IQR",
                "zscore":     "Z-skóre",
                "percentile": "Percentilové orezanie",
                "manual":     "Manuálny rozsah",
            }[x],
            index=0,
            key="stat_outlier_method",
        )

        iqr_k            = 1.5
        zscore_threshold = 3.0
        percentile_low   = 1.0
        percentile_high  = 99.0
        manual_low       = None
        manual_high      = None

        if outlier_method == "iqr":
            iqr_k = st.slider(
                "Násobok IQR (k)", 0.5, 5.0, 1.5, 0.1,
                key="stat_iqr_k",
                help="Štandardné: 1.5 | Miernejšie: 3.0 | Prísnejšie: 1.0",
            )
            st.caption(f"Odstráni hodnoty mimo Q1 − {iqr_k}×IQR a Q3 + {iqr_k}×IQR")

        elif outlier_method == "zscore":
            zscore_threshold = st.slider(
                "Prah z-skóre", 1.0, 5.0, 3.0, 0.1,
                key="stat_zscore",
                help="Štandardné: 3.0 | Prísnejšie: 2.0",
            )
            st.caption(f"Odstráni hodnoty s |z| > {zscore_threshold}")

        elif outlier_method == "percentile":
            col_pl, col_ph  = st.columns(2)
            percentile_low  = col_pl.number_input("Dolný %", 0.0,  49.0,  1.0, 0.5, key="stat_pct_low")
            percentile_high = col_ph.number_input("Horný %", 51.0, 100.0, 99.0, 0.5, key="stat_pct_high")
            st.caption(f"Zachová hodnoty medzi {percentile_low}. a {percentile_high}. percentilom")

        elif outlier_method == "manual":
            _data_min = float(st.session_state.get("stat_manual_data_min", 0.0))
            _data_max = float(st.session_state.get("stat_manual_data_max", 1000.0))
            col_ml, col_mh = st.columns(2)
            manual_low  = col_ml.number_input(
                "Min.", min_value=_data_min, max_value=_data_max,
                value=_data_min, format="%.4f", key="stat_manual_low",
            )
            manual_high = col_mh.number_input(
                "Max.", min_value=_data_min, max_value=_data_max,
                value=_data_max, format="%.4f", key="stat_manual_high",
            )
            if st.session_state.get("stat_manual_data_min") is not None:
                st.caption(f"Rozsah z analýzy: [{_data_min:.4f}, {_data_max:.4f}]")
            else:
                st.caption("Spustite analýzu pre dynamický rozsah.")

    return {
        "method":           outlier_method,
        "iqr_k":            iqr_k,
        "zscore_threshold": zscore_threshold,
        "percentile_low":   percentile_low,
        "percentile_high":  percentile_high,
        "manual_low":       manual_low,
        "manual_high":      manual_high,
    }


def _reset_filter_state():
    """Vymaže všetky kľúče filtrov zo session state."""
    prefixes = ["ids_", "m_", "z_", "out_", "age_", "dur_", "date_",
                "sel_", "tmin_", "tmax_", "imin_", "imax_", "preset_", "btn_"]
    to_delete = [k for k in st.session_state if any(k.startswith(p) for p in prefixes)]
    for k in to_delete:
        del st.session_state[k]
    st.session_state.editor_key += 1


# ---------------------------------------------------------------------------
# VÝBER SKUPINY INDEXOV
# ---------------------------------------------------------------------------

def render_index_group_selector(key_prefix: str) -> list[str]:
    """
    Dvojkrokový výber indexov: skupina → konkrétne indexy.
    Ľavý stĺpec: výber skupín. Pravý stĺpec: samostatný multiselect pre každú vybranú skupinu.
    Vráti zoznam vybraných názvov indexov.
    """
    col_groups, col_indices = st.columns(2)

    with col_groups:
        selected_groups = st.multiselect(
            "Skupina indexov:",
            options=list(INDEX_GROUPS.keys()),
            default=[],
            key=f"{key_prefix}_groups",
        )

    selected_indices = []
    with col_indices:
        if not selected_groups:
            st.multiselect("Indexy:", options=[], disabled=True, key=f"{key_prefix}_idx_empty")
        else:
            for group_name in selected_groups:
                indices = st.multiselect(
                    f"{group_name}:",
                    options=list(INDEX_GROUPS[group_name].keys()),
                    default=[],
                    key=f"{key_prefix}_idx_{group_name}",
                )
                selected_indices.extend(indices)

    return selected_indices