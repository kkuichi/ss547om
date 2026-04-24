import pandas as pd
import numpy as np


# ---------------------------------------------------------------------------
# VÝPOČTOVÉ FUNKCIE INDEXOV
# ---------------------------------------------------------------------------

def nlr(df):
    return df["Neu abs"] / df["Ly abs"].replace(0, np.nan)

def plr(df):
    return df["PLT"] / df["Ly abs"].replace(0, np.nan)

def dnlr(df):
    denom = (df["WBC"] - df["Neu abs"]).replace(0, np.nan)
    return df["Neu abs"] / denom.where(denom > 0, np.nan)

def sii(df):
    return (df["PLT"] * df["Neu abs"]) / df["Ly abs"].replace(0, np.nan)

def car(df):
    return df["S-CRP"] / df["S-Alb"].replace(0, np.nan)

def clr(df):
    return df["S-CRP"] / df["Ly abs"].replace(0, np.nan)

def ferritin_ly(df):
    return df["S-FER"] / df["Ly abs"].replace(0, np.nan)

def far(df):
    return df["Fib"] / df["S-Alb"].replace(0, np.nan)

def bun_cr(df):
    return df["S-Urea"] / df["S-Kreat"].replace(0, np.nan)

def de_ritis(df):
    return df["S-AST"] / df["S-ALT"].replace(0, np.nan)

def ast_plt(df):
    return df["S-AST"] / df["PLT"].replace(0, np.nan)

def ldh_albumin(df):
    return df["S-LD"] / df["S-Alb"].replace(0, np.nan)

def dlr(df):
    return df["D-dimér HS"] / df["Ly abs"].replace(0, np.nan)

def ddimer_albumin(df):
    return df["D-dimér HS"] / df["S-Alb"].replace(0, np.nan)

def fibrinogen_ly(df):
    return df["Fib"] / df["Ly abs"].replace(0, np.nan)

def plt_fibrinogen(df):
    return df["PLT"] / df["Fib"].replace(0, np.nan)

def blr(df):
    return df["S-PBNP"] / df["Ly abs"].replace(0, np.nan)


# ---------------------------------------------------------------------------
# REGISTER INDEXOV
# ---------------------------------------------------------------------------

INDEX_GROUPS: dict[str, dict[str, callable]] = {
    "Hematologické": {
        "NLR":  nlr,
        "PLR":  plr,
        "dNLR": dnlr,
        "SII":  sii,
    },
    "Biochemické": {
        "CAR":         car,
        "CLR":         clr,
        "Ferritin/Ly": ferritin_ly,
        "FAR":         far,
        "BUN/Cr":      bun_cr,
        "De Ritis":    de_ritis,
        "AST/PLT":     ast_plt,
        "LDH/Albumin": ldh_albumin,
    },
    "Koagulačné": {
        "DLR":             dlr,
        "D-dimér/Albumin": ddimer_albumin,
        "Fibrinogen/Ly":   fibrinogen_ly,
        "PLT/Fibrinogen":  plt_fibrinogen,
    },
    "Kardiošpecifické": {
        "BLR": blr,
    },
}

INDEX_REGISTRY: dict[str, callable] = {}
for _group in INDEX_GROUPS.values():
    INDEX_REGISTRY.update(_group)


# ---------------------------------------------------------------------------
# REFERENČNÉ MEDZE INDEXOV
# ---------------------------------------------------------------------------

INDEX_THRESHOLDS: dict[str, dict] = {
    "NLR":             {"low": 0.350,   "high": 4.333,    "unit": "bezrozmerný"},
    "PLR":             {"low": 37.500,  "high": 266.667,  "unit": "bezrozmerný"},
    "dNLR":            {"low": 0.163,   "high": 3.130,    "unit": "bezrozmerný"},
    "SII":             {"low": 52.500,  "high": 1733.000, "unit": "×10⁹/L"},
    "CAR":             {"low": 0.002,   "high": 0.143,    "unit": "bezrozmerný"},
    "CLR":             {"low": 0.025,   "high": 3.333,    "unit": "bezrozmerný"},
    "Ferritin/Ly":     {"low": 2.750,   "high": 204.667,  "unit": "bezrozmerný"},
    "FAR":             {"low": 0.035,   "high": 0.100,    "unit": "bezrozmerný"},
    "BUN/Cr":          {"low": 0.027,   "high": 0.147,    "unit": "bezrozmerný"},
    "De Ritis":        {"low": 0.083,   "high": 12.000,   "unit": "bezrozmerný"},
    "AST/PLT":         {"low": 0.000,   "high": 0.004,    "unit": "bezrozmerný"},
    "LDH/Albumin":     {"low": None,    "high": None,     "unit": "bezrozmerný"},
    "DLR":             {"low": 0.007,   "high": 0.333,    "unit": "bezrozmerný"},
    "D-dimér/Albumin": {"low": 0.001,   "high": 0.014,    "unit": "bezrozmerný"},
    "Fibrinogen/Ly":   {"low": 0.450,   "high": 2.333,    "unit": "bezrozmerný"},
    "PLT/Fibrinogen":  {"low": 42.857,  "high": 222.222,  "unit": "bezrozmerný"},
    "BLR":             {"low": 1.250,   "high": 83.333,   "unit": "bezrozmerný"},
}