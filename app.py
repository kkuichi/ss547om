import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go

from modules.state_manager import (
    initialize_session_state, load_new_wave,
    save_changes, undo_last_action, redo_action, reset_to_original,
)
from modules.filters import (
    render_sidebar_filters,
    render_sidebar_stat_filters,
    render_index_group_selector,
)
from modules.indices import INDEX_REGISTRY
from modules.visualization import (
    plot_patient_index_trend,
    plot_mortality_trend,
    compute_mortality_stats,
    compute_index_benchmark,
)
from modules.statistical_tests import (
    run_statistical_analysis,
    run_mortality_between_waves,
)

# ---------------------------------------------------------------------------
# KONFIGURÁCIA
# ---------------------------------------------------------------------------

st.set_page_config(page_title="COVID-19 CDSS", layout="wide")
initialize_session_state()

if st.session_state.master_data is None:
    load_new_wave(st.session_state.current_wave)

df = st.session_state.master_data
if not df.empty:
    df["ID"]           = df["ID"].astype(str)
    df["Dátum odberu"] = pd.to_datetime(df["Dátum odberu"], errors="coerce")
    if "Vlna" not in df.columns:
        df["Vlna"] = st.session_state.current_wave
    st.session_state.master_data = df

if "active_tab" not in st.session_state:
    st.session_state.active_tab = "db"

# ---------------------------------------------------------------------------
# TAB NAVIGÁCIA
# ---------------------------------------------------------------------------

TABS = {
    "db":        "Databáza pacientov",
    "analysis":  "Analýza indexov",
    "mortality": "Krivka mortality",
    "stats":     "Štatistická analýza",
}

# CSS pre navigáciu — tlačidlá štylizované ako taby
st.markdown("""
<style>
/* Skryje pôvodný obal tlačidla (border, background) pre nav tlačidlá */
div[data-testid="stHorizontalBlock"] > div[data-testid="stColumn"] > div[data-testid="stVerticalBlock"]
    button[kind="tertiary"].cdss-tab-btn {
    border: none !important;
    background: none !important;
}

/* Navigačný wrapper */
.cdss-nav-wrapper {
    border-bottom: 2px solid #e0e0e0;
    margin-bottom: 0.25rem;
}
</style>
""", unsafe_allow_html=True)

nav_cols = st.columns(len(TABS))
for i, (tab_key, tab_label) in enumerate(TABS.items()):
    is_active = st.session_state.active_tab == tab_key
    with nav_cols[i]:
        if is_active:
            st.markdown(
                f"<div style='"
                f"text-align:center; padding:8px 4px 6px 4px; "
                f"font-size:0.95rem; font-weight:600; color:#1a1a1a; "
                f"border-bottom:3px solid #1a73e8; cursor:default;'>"
                f"{tab_label}</div>",
                unsafe_allow_html=True,
            )
        else:
            if st.button(
                tab_label,
                key=f"nav_{tab_key}",
                use_container_width=True,
                type="tertiary",
            ):
                st.session_state.active_tab = tab_key
                st.rerun()

st.markdown(
    "<hr style='margin-top:0; margin-bottom:1.5rem; border:none; border-top:2px solid #e0e0e0;'>",
    unsafe_allow_html=True,
)

active = st.session_state.active_tab

# ---------------------------------------------------------------------------
# SIDEBAR
# ---------------------------------------------------------------------------

if active in ("db", "analysis", "mortality"):
    filtered_df, selected_wave = render_sidebar_filters(st.session_state.master_data)

    if st.session_state.current_wave != selected_wave:
        load_new_wave(selected_wave)
        st.session_state.selected_p_ids = []
        st.session_state.editor_key    += 1
        st.rerun()

    PATIENT_TABLE_COLS = [
        "ID", "Pohlavie", "Vek", "Dátum príjmu", "Dátum prepustenia",
        "Dĺžka hospitalizácie", "Záznamov", "Závažnosť priebehu ochorenia",
    ]

    if not filtered_df.empty:
        filtered_df           = filtered_df.copy()
        filtered_df["ID_num"] = pd.to_numeric(filtered_df["ID"], errors="coerce")
        sorted_df             = filtered_df.sort_values(["ID_num", "Dátum odberu"])
        odber_counts          = filtered_df["ID"].value_counts().to_dict()
        patient_view          = sorted_df.groupby("ID").tail(1).copy()
        patient_view["Záznamov"] = patient_view["ID"].map(odber_counts)
        patient_view          = patient_view.drop(columns=["ID_num"])
    else:
        patient_view = pd.DataFrame()

    outlier_cfg = None

else:
    filtered_df  = st.session_state.master_data
    patient_view = pd.DataFrame()
    outlier_cfg  = render_sidebar_stat_filters()

    PATIENT_TABLE_COLS = []


# ---------------------------------------------------------------------------
# ZÁLOŽKA: DATABÁZA PACIENTOV
# ---------------------------------------------------------------------------

def _render_patient_card(p_id: str):
    """Zobrazí editovateľnú kartu pacienta."""
    p_history = (
        st.session_state.master_data[st.session_state.master_data["ID"] == p_id]
        .sort_values("Dátum odberu", ascending=False)
    )
    first_cols = ["Dátum odberu", "ID"]
    other_cols = [c for c in p_history.columns if c not in first_cols]
    p_history  = p_history[first_cols + other_cols]

    edited = st.data_editor(
        p_history,
        use_container_width=True,
        hide_index=True,
        key=f"edit_{p_id}_{st.session_state.editor_key}",
        column_config={
            "ID":           st.column_config.TextColumn("ID", disabled=True),
            "Dátum odberu": st.column_config.DateColumn("Dátum odberu"),
        },
    )
    if st.button("Uložiť zmeny", type="primary"):
        save_changes(edited)
        st.rerun()


if active == "db":
    available_cols = [c for c in PATIENT_TABLE_COLS if c in patient_view.columns]

    col_btns, col_stats = st.columns([1, 2], vertical_alignment="center")
    with col_btns:
        c1, _ = st.columns(2)
        with c1:
            with st.popover("Upraviť", use_container_width=False):
                if st.button("Späť",    type="tertiary", use_container_width=True):
                    undo_last_action(); st.rerun()
                if st.button("Vpred",   type="tertiary", use_container_width=True):
                    redo_action(); st.rerun()
                if st.button("Obnoviť", type="tertiary", use_container_width=True):
                    reset_to_original(); st.rerun()

    stats_placeholder = col_stats.empty()

    try:
        event = st.dataframe(
            patient_view[available_cols] if not patient_view.empty else pd.DataFrame(columns=available_cols),
            use_container_width=True,
            hide_index=True,
            key=f"master_df_{st.session_state.editor_key}",
            on_select="rerun",
            selection_mode="multi-row",
            column_config={
                "ID":           st.column_config.TextColumn("ID"),
                "Záznamov":     st.column_config.NumberColumn("Počet odberov"),
                "Dátum odberu": st.column_config.DateColumn("Posledný odber"),
                "Vek":          st.column_config.NumberColumn("Vek"),
                "Pohlavie":     st.column_config.TextColumn("Pohlavie"),
            },
        )

        selected_rows = event.selection.rows
        valid_rows    = [r for r in selected_rows if r < len(patient_view)]
        st.session_state.selected_p_ids = (
            patient_view.iloc[valid_rows]["ID"].tolist() if valid_rows else []
        )

        num_p = len(patient_view)
        sel_p = len(st.session_state.selected_p_ids)
        stats_placeholder.markdown(
            f"<p style='text-align:right; color:#555; margin:0; font-size:0.9rem;'>"
            f"Zobrazených: {num_p} | Vybraných: {sel_p}</p>",
            unsafe_allow_html=True,
        )

        if st.session_state.selected_p_ids:
            st.divider()
            p_id_active = st.session_state.selected_p_ids[-1]
            st.subheader(f"Karta pacienta: {p_id_active}")
            _render_patient_card(p_id_active)
        else:
            st.info("Pre zobrazenie karty pacienta označte príslušného pacienta.")

    except TypeError:
        st.error("Chyba verzie Streamlit. Spustite: `pip install --upgrade streamlit`")
        st.stop()


# ---------------------------------------------------------------------------
# TAB: ANALÝZA INDEXOV
# ---------------------------------------------------------------------------

def _render_benchmark_card(
    idx_name: str, p_val: float | None, bench: dict | None, col_idx: int, bench_cols: list
):
    """Vykreslí benchmarkovú kartu pre jeden index."""
    with bench_cols[col_idx % 4]:
        st.markdown(
            f"<div style='border:1px solid #ddd; border-radius:8px; padding:12px; background:#fafafa;'>"
            f"<b style='font-size:1rem;'>{idx_name}</b>",
            unsafe_allow_html=True,
        )
        if p_val is not None:
            st.metric("Posledná nameraná hodnota indexu u pacienta", f"{p_val:.2f}")
        else:
            st.markdown("*Hodnota pacienta nie je dostupná*")

        if bench:
            diff      = (p_val - bench["median"]) if p_val is not None else None
            delta_str = f"{'+' if diff >= 0 else ''}{diff:.2f} vs medián skupiny" if diff is not None else ""
            st.markdown(
                f"**Referenčná skupina** ({bench['n']} pacientov)<br>"
                f"Medián: `{bench['median']}`&nbsp;&nbsp;Priemer: `{bench['mean']}`<br>"
                f"Q1 / Q3: `{bench['q1']}` / `{bench['q3']}`<br>"
                f"Min / Max: `{bench['min']}` / `{bench['max']}`",
                unsafe_allow_html=True,
            )
            if delta_str and diff is not None:
                color = "#c0392b" if diff > 0 else "#27ae60"
                st.markdown(
                    f"<span style='color:{color}; font-weight:600;'>△ {delta_str}</span>",
                    unsafe_allow_html=True,
                )
        else:
            st.markdown(
                "<span style='color:#888; font-size:0.85rem;'>Nedostatok dát pre referenčnú skupinu</span>",
                unsafe_allow_html=True,
            )
        st.markdown("</div>", unsafe_allow_html=True)


if active == "analysis":
    if not st.session_state.selected_p_ids:
        st.info("Označte maximálne 5 pacientov v databáze.")
    elif len(st.session_state.selected_p_ids) > 5:
        st.warning("Zvoľte maximálne 5 pacientov.")
    else:
        chosen_indices = render_index_group_selector("analysis")

        if not chosen_indices:
            st.info("Zvoľte skupinu indexov, následne vyberte index.")
        else:
            wave_df_full = st.session_state.master_data.copy()

            for p_id in st.session_state.selected_p_ids:
                p_data = (
                    st.session_state.master_data[st.session_state.master_data["ID"] == p_id]
                    .copy()
                    .sort_values("Dátum odberu")
                )
                if p_data.empty:
                    continue

                last_row    = p_data.iloc[-1]
                p_pohlavie  = str(last_row.get("Pohlavie", ""))
                p_vek       = int(last_row["Vek"]) if pd.notna(last_row.get("Vek")) else None
                p_zavaznost = str(last_row.get("Závažnosť priebehu ochorenia", ""))

                with st.expander(
                    f"Pacient ID {p_id}  |  {p_pohlavie}  |  {p_vek} r.  |  {p_zavaznost}",
                    expanded=True,
                ):
                    for i in range(0, len(chosen_indices), 2):
                        cols = st.columns(2)
                        for j, idx_name in enumerate(chosen_indices[i:i + 2]):
                            p_data[idx_name] = INDEX_REGISTRY[idx_name](p_data)
                            fig = plot_patient_index_trend(p_data, idx_name)
                            cols[j].plotly_chart(fig, use_container_width=True,
                                                 key=f"ch_{p_id}_{idx_name}")

                    if p_vek is not None and p_pohlavie and p_zavaznost:
                        st.markdown("#### Porovnanie s podobnými pacientmi")
                        st.caption(
                            f"Referenčná skupina: **{p_pohlavie}**, vek **{p_vek - 5}–{p_vek + 5} rokov**, "
                            f"výsledok: **{p_zavaznost}** | Pacient z rovnakej vlny"
                        )
                        bench_cols = st.columns(min(len(chosen_indices), 4))

                        for col_i, idx_name in enumerate(chosen_indices):
                            bench = compute_index_benchmark(
                                wave_df=wave_df_full,
                                index_name=idx_name,
                                pohlavie=p_pohlavie,
                                vek=p_vek,
                                zavaznost=p_zavaznost,
                                index_fn=INDEX_REGISTRY[idx_name],
                            )
                            idx_vals = p_data[idx_name].dropna()
                            idx_vals = idx_vals[np.isfinite(idx_vals)]
                            p_val    = float(idx_vals.iloc[-1]) if not idx_vals.empty else None
                            _render_benchmark_card(idx_name, p_val, bench, col_i, bench_cols)

# ---------------------------------------------------------------------------
# TAB: KRIVKA MORTALITY
# ---------------------------------------------------------------------------

def _stat_row(label: str, value, unit: str = "") -> str:
    if value is None:
        return f"<tr><td style='color:#555;'>{label}</td><td>–</td></tr>"
    return f"<tr><td style='color:#555;'>{label}</td><td><b>{value}{unit}</b></td></tr>"


def _render_mortality_card(col, skupina: str, s: dict | None, color: str):
    """Vykreslí štatistickú kartu pre skupinu (Exitus/Prepustenie)."""
    with col:
        st.markdown(
            f"<div style='border-left:4px solid {color}; padding:12px 16px; "
            f"background:#fafafa; border-radius:6px;'>"
            f"<h4 style='color:{color}; margin:0 0 12px 0;'>{skupina}</h4>",
            unsafe_allow_html=True,
        )
        if s is None:
            st.markdown("*Žiadne dáta*")
            st.markdown("</div>", unsafe_allow_html=True)
            return

        table = f"""
        <table style='width:100%; border-collapse:collapse; font-size:0.9rem;'>
          <thead><tr><th style='text-align:left; border-bottom:1px solid #ddd; padding:4px 0;'
              colspan='2'>Hospitalizácia (dni)</th></tr></thead>
          <tbody>
            {_stat_row("Priemer",   s['hosp_mean'],   " dní")}
            {_stat_row("Medián",    s['hosp_median'],  " dní")}
            {_stat_row("Min / Max", f"{s['hosp_min']} / {s['hosp_max']}" if s['hosp_min'] is not None else None)}
          </tbody>
          <thead><tr><th style='text-align:left; border-bottom:1px solid #ddd; padding:8px 0 4px 0;'
              colspan='2'>Vek pacientov</th></tr></thead>
          <tbody>
            {_stat_row("Priemer",   s['vek_mean'],  " r.")}
            {_stat_row("Medián",    s['vek_median'], " r.")}
            {_stat_row("Min / Max", f"{s['vek_min']} / {s['vek_max']} r." if s['vek_min'] is not None else None)}
          </tbody>
          <thead><tr><th style='text-align:left; border-bottom:1px solid #ddd; padding:8px 0 4px 0;'
              colspan='2'>Pohlavie</th></tr></thead>
          <tbody>
            {_stat_row("Muži",  f"{s['muz_n']} ({s['muz_pct']} %)")}
            {_stat_row("Ženy",  f"{s['zena_n']} ({s['zena_pct']} %)")}
          </tbody>
        </table></div>
        """
        st.markdown(table, unsafe_allow_html=True)


if active == "mortality":
    if not st.session_state.selected_p_ids:
        st.info("Označte skupinu pacientov v databáze.")
    else:
        final_outcomes = (
            st.session_state.master_data[
                st.session_state.master_data["ID"].isin(st.session_state.selected_p_ids)
            ]
            .sort_values(["ID", "Dátum odberu"])
            .groupby("ID")
            .tail(1)
        )

        total         = len(final_outcomes)
        deaths        = (final_outcomes["Závažnosť priebehu ochorenia"] == "Exitus").sum()
        discharged    = (final_outcomes["Závažnosť priebehu ochorenia"] == "Prepustenie").sum()
        mortality_pct = (deaths / total * 100) if total > 0 else 0

        mort_stats = compute_mortality_stats(final_outcomes)

        st.plotly_chart(plot_mortality_trend(final_outcomes), use_container_width=True)
        st.divider()
        st.markdown("### Súhrnné štatistiky")

        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Analyzovaní pacienti", total)
        m2.metric("Mortalita",            f"{mortality_pct:.1f}%")
        m3.metric("Exitus",               int(deaths))
        m4.metric("Prepustení",           int(discharged))

        st.markdown("")
        col_ex, col_pre = st.columns(2)
        _render_mortality_card(col_ex,  "Exitus",      mort_stats.get("exitus"),      "#e74c3c")
        _render_mortality_card(col_pre, "Prepustenie", mort_stats.get("prepustenie"), "#27ae60")


# ---------------------------------------------------------------------------
# TAB: ŠTATISTICKÁ ANALÝZA
# ---------------------------------------------------------------------------

def _render_desc_stats(label: str, n: int, mean: float, median: float,
                       q1: float, q3: float, vmin: float, vmax: float):
    st.markdown(f"**{label}**")
    st.markdown(f"Referenčná skupina: `{n}` pacientov")
    st.markdown(f"Priemer: `{mean:.3f}`")
    st.markdown(f"Medián: `{median:.3f}`")
    st.markdown(f"Q1 / Q3: `{q1:.3f}` / `{q3:.3f}`")
    st.markdown(f"Min / Max: `{vmin:.3f}` / `{vmax:.3f}`")


def _render_desc_stats_from_dict(label: str, s: dict):
    _render_desc_stats(label, s["n"], s["mean"], s["median"], s["q1"], s["q3"], s["min"], s["max"])


def _render_statistical_metrics(p_value: float, cliffs_d: float):
    """Zobrazí p-hodnotu a veľkosť účinku (Cliff's delta)."""
    if p_value < 0.0001:
        exp = abs(int(np.floor(np.log10(p_value))))
        st.markdown("<span style='font-size:0.8rem; color:#555;'>p-hodnota</span>", unsafe_allow_html=True)
        st.markdown(
            f"<p style='font-size:1.8rem; font-weight:700; margin:2px 0 16px 0; line-height:1;'>"
            f"&lt;&nbsp;1&times;10<sup style='font-size:1rem; font-weight:600;'>−{exp}</sup></p>",
            unsafe_allow_html=True,
        )
    else:
        st.metric("p-hodnota", f"{p_value:.4f}")

    abs_d    = abs(cliffs_d)
    category = (
        "zanedbateľný účinok" if abs_d < 0.147
        else "malý účinok"    if abs_d < 0.330
        else "stredný účinok" if abs_d < 0.474
        else "veľký účinok"
    )
    st.markdown(
        f"<div style='margin-top:4px;'>"
        f"<span style='font-size:0.8rem; color:#555;'>Veľkosť účinku (Cliff's delta)</span><br>"
        f"<span style='font-size:1.4rem; font-weight:700;'>{cliffs_d:.3f}</span>"
        f"<span style='font-size:0.9rem; color:#444; margin-left:8px;'>{category}</span>"
        f"</div>"
        f"<div style='margin-top:10px; font-size:0.78rem; color:#888; line-height:1.6;'>"
        f"&lt; 0.147 zanedbateľný &nbsp;·&nbsp; 0.147–0.330 malý &nbsp;·&nbsp; "
        f"0.330–0.474 stredný &nbsp;·&nbsp; ≥ 0.474 veľký"
        f"</div>",
        unsafe_allow_html=True,
    )


def _make_boxplot(
    d1_raw, name1: str, color1: str,
    d2_raw, name2: str, color2: str,
    title: str, key: str,
    d1_filtered=None, d2_filtered=None,
    outlier_method: str = "none",
):
    """Boxplot dvoch skupín. Ak je aktívny outlier filter, zobrazí filtrované dáta."""
    use_filtered = outlier_method != "none" and d1_filtered is not None and d2_filtered is not None
    d1 = d1_filtered if use_filtered else d1_raw
    d2 = d2_filtered if use_filtered else d2_raw

    fig = go.Figure()
    for data, name, color in [(d1, name1, color1), (d2, name2, color2)]:
        fig.add_trace(go.Box(
            y=data, name=name, marker_color=color,
            boxmean=True, boxpoints="outliers", jitter=0.3, pointpos=0,
        ))
    suffix = " (po filtrovaní outlierov)" if use_filtered else ""
    fig.update_layout(
        title=dict(text=title + suffix, font=dict(size=13)),
        showlegend=True, height=380,
        margin=dict(t=40, b=30, l=10, r=10),
        plot_bgcolor="white",
        yaxis=dict(gridcolor="#eeeeee"),
    )
    st.plotly_chart(fig, use_container_width=True, key=key)


def _render_result_container(
    idx_name: str, sig: bool, p_value: float, cliffs_d: float,
    col_stats_content: callable, col_box_content: callable,
):
    """Obaľovací kontajner pre výsledok jedného indexu."""
    sig_label = "Štatisticky významný rozdiel (p < 0.05)" if sig else "Rozdiel nie je štatisticky významný (p ≥ 0.05)"
    sig_color = "#d4edda" if sig else "#f8d7da"

    with st.container(border=True):
        st.markdown(f"### {idx_name}")
        col_s, col_b = st.columns([1, 2])
        with col_s:
            st.markdown(
                f"<div style='background:{sig_color}; padding:8px 12px; border-radius:6px; "
                f"font-weight:600; margin-bottom:12px;'>{sig_label}</div>",
                unsafe_allow_html=True,
            )
            _render_statistical_metrics(p_value, cliffs_d)
            st.divider()
            col_stats_content()
        with col_b:
            col_box_content()


if active == "stats":
    if "stat_gen_results" not in st.session_state:
        st.session_state.stat_gen_results = None
    if "stat_mort_results" not in st.session_state:
        st.session_state.stat_mort_results = None
    sub_general, sub_mort = st.tabs(["Porovnanie medzi vlnami", "Porovnanie s mortalitou"])

    # ---------------------------------------------------------------------------
    # POROVNANIE INDEXOV MEDZI VLNAMI
    # ---------------------------------------------------------------------------
    with sub_general:
        st.subheader("Mann-Whitney U Test – Porovnanie indexov medzi vlnami")

        col1, col2       = st.columns(2)
        wave1            = col1.selectbox("Vlna X:", [1, 2, 3, 4], key="gen_wave1")
        wave2            = col2.selectbox("Vlna Y:", [1, 2, 3, 4], index=1, key="gen_wave2")
        selected_indices = render_index_group_selector("gen")

        if st.button("Spustiť analýzu", type="primary", key="btn_general"):
            if wave1 == wave2:
                st.warning("⚠️ Zvoľte rôzne vlny.")
            elif not selected_indices:
                st.warning("⚠️ Zvoľte minimálne jeden index.")
            else:
                with st.spinner("Prebieha analýza..."):
                    results_df, failed, plot_data = run_statistical_analysis(
                        wave1, wave2, selected_indices, outlier_cfg
                    )
                st.session_state.stat_gen_results = {
                    "results_df":       results_df,
                    "failed":           failed,
                    "plot_data":        plot_data,
                    "wave1":            wave1,
                    "wave2":            wave2,
                    "outlier_method":   outlier_cfg["method"],
                    "iqr_k":            outlier_cfg["iqr_k"],
                    "zscore_threshold": outlier_cfg["zscore_threshold"],
                    "percentile_low":   outlier_cfg["percentile_low"],
                    "percentile_high":  outlier_cfg["percentile_high"],
                    "manual_low":       outlier_cfg["manual_low"],
                    "manual_high":      outlier_cfg["manual_high"],
                }
                if not results_df.empty:
                    row = results_df.iloc[0]
                    st.session_state.stat_manual_data_min = float(min(row["min_wave1"], row["min_wave2"]))
                    st.session_state.stat_manual_data_max = float(max(row["max_wave1"], row["max_wave2"]))

        gen = st.session_state.stat_gen_results
        if gen is not None:
            results_df = gen["results_df"]
            plot_data  = gen["plot_data"]
            w1, w2     = gen["wave1"], gen["wave2"]
            om         = gen["outlier_method"]

            if gen["failed"]:
                st.warning(f"⚠️ Indexy **{', '.join(gen['failed'])}** sa nepodarilo vypočítať.")

            if results_df.empty:
                st.error("Žiadny index sa nepodarilo analyzovať.")
            else:
                for _, row in results_df.iterrows():
                    idx_name = row["index"]
                    pdata    = plot_data[idx_name]

                    def _stats_col(r=row, w1=w1, w2=w2):
                        t1, t2 = st.columns(2)
                        with t1:
                            _render_desc_stats(
                                f"Vlna {w1}", int(r["n_wave1"]), r["mean_wave1"], r["median_wave1"],
                                r["q1_wave1"], r["q3_wave1"], r["min_wave1"], r["max_wave1"],
                            )
                        with t2:
                            _render_desc_stats(
                                f"Vlna {w2}", int(r["n_wave2"]), r["mean_wave2"], r["median_wave2"],
                                r["q1_wave2"], r["q3_wave2"], r["min_wave2"], r["max_wave2"],
                            )

                    def _box_col(pd=pdata, n=idx_name, w1=w1, w2=w2):
                        _make_boxplot(
                            pd["raw_data_wave1"], f"Vlna {w1}", "#4C9BE8",
                            pd["raw_data_wave2"], f"Vlna {w2}", "#E8784C",
                            f"{n} – rozloženie hodnôt",
                            key=f"box_gen_{n}_{w1}_{w2}",
                            d1_filtered=pd["test_data_wave1"],
                            d2_filtered=pd["test_data_wave2"],
                            outlier_method=om,
                        )

                    _render_result_container(
                        idx_name, row["significant"], row["p_value"], row["cliffs_d"],
                        _stats_col, _box_col,
                    )

                st.caption("Mann-Whitney U test, dvojstranný | α = 0.05")

    # ---------------------------------------------------------------------------
    # POROVNANIE S MORTALITOU
    # ---------------------------------------------------------------------------
    with sub_mort:
        st.subheader("Mann-Whitney U Test – Porovnanie indexov s ohľadom na mortalitu")

        col1, col2  = st.columns(2)
        ma_wave1    = col1.selectbox("Vlna X:", [1, 2, 3, 4], key="ma_wave1")
        ma_skupina1 = col1.selectbox("Závažnosť priebehu ochorenia vo vlne X:",
                                     ["Exitus", "Prepustenie"], key="ma_skupina1")
        ma_wave2    = col2.selectbox("Vlna Y:", [1, 2, 3, 4], index=1, key="ma_wave2")
        ma_skupina2 = col2.selectbox("Závažnosť priebehu ochorenia vo vlne Y:",
                                     ["Exitus", "Prepustenie"], key="ma_skupina2")
        ma_indices  = render_index_group_selector("ma")

        if st.button("Spustiť analýzu", type="primary", key="btn_mort_a"):
            if ma_wave1 == ma_wave2 and ma_skupina1 == ma_skupina2:
                st.warning("⚠️ Zvoľte rôzne vlny alebo rôzne skupiny.")
            elif not ma_indices:
                st.warning("⚠️ Zvoľte minimálne jeden index.")
            else:
                with st.spinner("Prebieha analýza..."):
                    ma_results, ma_failed = run_mortality_between_waves(
                        ma_wave1, ma_wave2, ma_indices, outlier_cfg,
                        skupina1=ma_skupina1, skupina2=ma_skupina2,
                    )
                st.session_state.stat_mort_results = {
                    "results":        ma_results,
                    "failed":         ma_failed,
                    "wave1":          ma_wave1,
                    "wave2":          ma_wave2,
                    "skupina1":       ma_skupina1,
                    "skupina2":       ma_skupina2,
                    "outlier_method": outlier_cfg["method"],
                }
                if ma_results:
                    s1 = ma_results[0]["stats_wave1"]
                    s2 = ma_results[0]["stats_wave2"]
                    st.session_state.stat_manual_data_min = float(min(s1["min"], s2["min"]))
                    st.session_state.stat_manual_data_max = float(max(s1["max"], s2["max"]))

        mort = st.session_state.stat_mort_results
        if mort is not None:
            ma_results = mort["results"]
            w1, w2     = mort["wave1"],    mort["wave2"]
            sk1, sk2   = mort["skupina1"], mort["skupina2"]
            om         = mort["outlier_method"]

            if mort["failed"]:
                st.warning(f"⚠️ Indexy **{', '.join(mort['failed'])}** – nedostatok dát.")

            if not ma_results:
                st.error("Žiadny index sa nepodarilo analyzovať.")
            else:
                for res in ma_results:
                    idx_name = res["index"]
                    label1   = f"Vlna {w1} – {sk1}"
                    label2   = f"Vlna {w2} – {sk2}"
                    color1   = "#c0392b" if sk1 == "Exitus" else "#27ae60"
                    color2   = "#8e44ad" if sk2 == "Exitus" else "#2980b9"

                    def _stats_col_m(r=res, l1=label1, l2=label2):
                        t1, t2 = st.columns(2)
                        with t1: _render_desc_stats_from_dict(l1, r["stats_wave1"])
                        with t2: _render_desc_stats_from_dict(l2, r["stats_wave2"])

                    def _box_col_m(r=res, n=idx_name, l1=label1, l2=label2,
                                   c1=color1, c2=color2, w1=w1, w2=w2):
                        _make_boxplot(
                            r["raw_data_wave1"], l1, c1,
                            r["raw_data_wave2"], l2, c2,
                            f"{n} – {l1} vs {l2}",
                            key=f"box_ma_{n}_{w1}_{w2}",
                            d1_filtered=r["test_data_wave1"],
                            d2_filtered=r["test_data_wave2"],
                            outlier_method=om,
                        )

                    _render_result_container(
                        idx_name, res["significant"], res["p_value"], res["cliffs_d"],
                        _stats_col_m, _box_col_m,
                    )

                st.caption("Mann-Whitney U test, dvojstranný | α = 0.05 | Použitý posledný odber pacienta")