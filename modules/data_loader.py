import os
import pandas as pd
import streamlit as st

PRIORITY_COLS = [
    "ID", "Pohlavie", "Vek", "Dátum príjmu", "Dátum prepustenia",
    "Dĺžka hospitalizácie", "Závažnosť priebehu ochorenia", "Dátum odberu",
]
DATE_COLS = ["Dátum odberu", "Dátum príjmu", "Dátum prepustenia"]


def load_wave_data(wave: int) -> pd.DataFrame:
    """Načíta CSV súbor pre danú vlnu, vyčistí stĺpce a skonvertuje dátumy."""
    path = f"data/vlna_{wave}.csv"
    if not os.path.exists(path):
        return pd.DataFrame(columns=PRIORITY_COLS)
    try:
        df = pd.read_csv(path, dtype={"ID": str})
        drop = [c for c in df.columns if "Unnamed" in str(c) or not str(c).strip()]
        df = df.drop(columns=drop, errors="ignore")
        for col in DATE_COLS:
            if col in df.columns:
                df[col] = pd.to_datetime(df[col], errors="coerce").dt.date
        priority = [c for c in PRIORITY_COLS if c in df.columns]
        others   = [c for c in df.columns if c not in PRIORITY_COLS]
        return df[priority + others]
    except Exception as e:
        st.error(f"Chyba pri načítaní vlny {wave}: {e}")
        return pd.DataFrame(columns=PRIORITY_COLS)