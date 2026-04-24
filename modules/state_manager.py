import os
import streamlit as st
import pandas as pd
from modules.data_loader import load_wave_data

_WAVE_PATH = "data/vlna_{wave}.csv"


def initialize_session_state():
    """Inicializuje session state pri prvom spustení aplikácie."""
    defaults = {
        "master_data":    None,
        "original_data":  None,
        "history_stack":  [],
        "redo_stack":     [],
        "current_wave":   1,
        "editor_key":     0,
        "selected_p_ids": [],
    }
    for key, val in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = val


def load_new_wave(wave_id: int):
    """Načíta vlnu a resetuje históriu zmien."""
    data = load_wave_data(wave_id)
    st.session_state.master_data   = data.copy()
    st.session_state.original_data = data.copy()
    st.session_state.history_stack = []
    st.session_state.redo_stack    = []
    st.session_state.current_wave  = wave_id
    st.session_state.editor_key   += 1


def _persist(df: pd.DataFrame):
    """Uloží DataFrame na disk pre aktuálnu vlnu."""
    wave = st.session_state.get("current_wave", 1)
    os.makedirs("data", exist_ok=True)
    df.to_csv(_WAVE_PATH.format(wave=wave), index=False, encoding="utf-8-sig")


def save_changes(updated_df: pd.DataFrame):
    """Uloží zmeny z editora — pridá snapshot do histórie."""
    st.session_state.history_stack.append(st.session_state.master_data.copy())
    st.session_state.redo_stack    = []
    st.session_state.master_data   = updated_df.copy()
    _persist(updated_df)
    st.toast("Zmeny boli uložené.")


def undo_last_action():
    """Vráti stav o jeden krok späť."""
    if not st.session_state.history_stack:
        return
    st.session_state.redo_stack.append(st.session_state.master_data.copy())
    st.session_state.master_data = st.session_state.history_stack.pop()
    _persist(st.session_state.master_data)
    st.session_state.editor_key += 1
    st.toast("Akcia vrátená späť.")


def redo_action():
    """Posunie stav o jeden krok vpred."""
    if not st.session_state.redo_stack:
        return
    st.session_state.history_stack.append(st.session_state.master_data.copy())
    st.session_state.master_data = st.session_state.redo_stack.pop()
    _persist(st.session_state.master_data)
    st.session_state.editor_key += 1
    st.toast("Akcia vrátená vpred.")


def reset_to_original():
    """Resetuje dáta aktuálnej vlny do pôvodného načítaného stavu."""
    if st.session_state.original_data is None:
        return
    st.session_state.history_stack.append(st.session_state.master_data.copy())
    st.session_state.master_data = st.session_state.original_data.copy()
    _persist(st.session_state.master_data)
    st.session_state.editor_key += 1
    st.toast("Dáta obnovené do pôvodného stavu.")