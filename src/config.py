"""Configuración centralizada, rutas portables, constantes y normalización de equipos."""

from __future__ import annotations

from pathlib import Path
from typing import Iterable

import pandas as pd

# Raíz del repositorio independiente del directorio de ejecución
ROOT_DIR: Path = Path(__file__).resolve().parent.parent
DATASETS_DIR: Path = ROOT_DIR / "datasets"
MODELS_DIR: Path = ROOT_DIR / "models"

# Rutas a los datasets históricos
PREMIER_LEAGUE_CSV: Path = DATASETS_DIR / "Premier League (1993 - Present)" / "PremierLeague.csv"
MATCHES_CSV: Path = DATASETS_DIR / "Club Football Match Data (2000 - 2026)" / "Matches.csv"
ELO_RATINGS_CSV: Path = DATASETS_DIR / "Club Football Match Data (2000 - 2026)" / "EloRatings.csv"
EPL_FINAL_CSV: Path = DATASETS_DIR / "English Premier League Match Data (2000-2025)" / "epl_final.csv"

# Rutas a los artefactos serializados
MODEL_PATH: Path = MODELS_DIR / "best_deep_mlp.keras"
SCALER_PATH: Path = MODELS_DIR / "scaler.pkl"
PREPROCESSOR_PATH: Path = MODELS_DIR / "preprocessor.pkl"
FEATURE_NAMES_PATH: Path = MODELS_DIR / "feature_names.json"
CALIBRATION_PATH: Path = MODELS_DIR / "calibration.json"
TRAINING_SUMMARY_PATH: Path = MODELS_DIR / "training_summary.json"

# Semilla global para reproducibilidad
SEED: int = 42

# Mapeo de clases objetivo
TARGET_MAP: dict[str, int] = {"H": 0, "D": 1, "A": 2}
INV_TARGET_MAP: dict[int, str] = {
    0: "Victoria Local (H)",
    1: "Empate (D)",
    2: "Victoria Visitante (A)",
}
CLASS_CODES: tuple[str, str, str] = ("H", "D", "A")

# Particiones cronológicas estrictas por temporada EPL
TRAIN_SEASONS: tuple[str, ...] = tuple(
    f"{year}/{str(year + 1)[-2:]}" for year in range(2000, 2017)
)  # 17 temporadas: 2000/01 - 2016/17 (6,460 partidos)

VAL_SEASONS: tuple[str, ...] = tuple(
    f"{year}/{str(year + 1)[-2:]}" for year in range(2017, 2021)
)  # 4 temporadas: 2017/18 - 2020/21 (1,520 partidos)

TEST_SEASONS: tuple[str, ...] = tuple(
    f"{year}/{str(year + 1)[-2:]}" for year in range(2021, 2025)
)  # 4 temporadas: 2021/22 - 2024/25 (1,520 partidos)

PROSPECTIVE_SEASONS: tuple[str, ...] = ("2025/26",)  # Temporada futura fuera de muestra (380 partidos)

# Alias completos para normalización case-insensitive de clubes de la EPL
TEAM_ALIASES: dict[str, str] = {
    "afc bournemouth": "Bournemouth",
    "bournemouth": "Bournemouth",
    "arsenal": "Arsenal",
    "arsenal fc": "Arsenal",
    "aston villa": "Aston Villa",
    "birmingham": "Birmingham",
    "birmingham city": "Birmingham",
    "blackburn": "Blackburn",
    "blackburn rovers": "Blackburn",
    "blackpool": "Blackpool",
    "bolton": "Bolton",
    "bolton wanderers": "Bolton",
    "bradford": "Bradford",
    "bradford city": "Bradford",
    "brentford": "Brentford",
    "brighton": "Brighton",
    "brighton & hove albion": "Brighton",
    "brighton and hove albion": "Brighton",
    "burnley": "Burnley",
    "cardiff": "Cardiff",
    "cardiff city": "Cardiff",
    "charlton": "Charlton",
    "charlton athletic": "Charlton",
    "chelsea": "Chelsea",
    "chelsea fc": "Chelsea",
    "coventry": "Coventry",
    "coventry city": "Coventry",
    "crystal palace": "Crystal Palace",
    "derby": "Derby",
    "derby county": "Derby",
    "everton": "Everton",
    "fulham": "Fulham",
    "huddersfield": "Huddersfield",
    "huddersfield town": "Huddersfield",
    "hull": "Hull",
    "hull city": "Hull",
    "ipswich": "Ipswich",
    "ipswich town": "Ipswich",
    "leeds": "Leeds",
    "leeds united": "Leeds",
    "leicester": "Leicester",
    "leicester city": "Leicester",
    "liverpool": "Liverpool",
    "liverpool fc": "Liverpool",
    "luton": "Luton",
    "luton town": "Luton",
    "man city": "Man City",
    "manchester city": "Man City",
    "mancity": "Man City",
    "man united": "Man United",
    "man utd": "Man United",
    "manchester united": "Man United",
    "manchester utd": "Man United",
    "manutd": "Man United",
    "middlesbrough": "Middlesbrough",
    "boro": "Middlesbrough",
    "newcastle": "Newcastle",
    "newcastle united": "Newcastle",
    "newcastle utd": "Newcastle",
    "norwich": "Norwich",
    "norwich city": "Norwich",
    "nott'm forest": "Nott'm Forest",
    "nottm forest": "Nott'm Forest",
    "nottingham": "Nott'm Forest",
    "nottingham forest": "Nott'm Forest",
    "portsmouth": "Portsmouth",
    "qpr": "QPR",
    "queens park rangers": "QPR",
    "reading": "Reading",
    "sheff utd": "Sheffield United",
    "sheffield utd": "Sheffield United",
    "sheffield united": "Sheffield United",
    "southampton": "Southampton",
    "stoke": "Stoke",
    "stoke city": "Stoke",
    "sunderland": "Sunderland",
    "swansea": "Swansea",
    "swansea city": "Swansea",
    "tottenham": "Tottenham",
    "tottenham hotspur": "Tottenham",
    "spurs": "Tottenham",
    "watford": "Watford",
    "west brom": "West Brom",
    "west bromwich": "West Brom",
    "west bromwich albion": "West Brom",
    "west ham": "West Ham",
    "west ham united": "West Ham",
    "wigan": "Wigan",
    "wigan athletic": "Wigan",
    "wolves": "Wolves",
    "wolverhampton": "Wolves",
    "wolverhampton wanderers": "Wolves",
}


def normalize_season_label(season: str) -> str:
    """Convierte formatos como '2000-2001' o '2000/01' al formato canónico 'YYYY/YY'."""
    s = str(season).strip()
    if "/" in s and len(s) == 7:
        return s
    if "-" in s:
        parts = s.split("-")
        if len(parts) == 2 and len(parts[0]) == 4:
            return f"{parts[0]}/{parts[1][-2:]}"
    return s


def infer_epl_season(dt: pd.Timestamp | str) -> str:
    """Infiere la temporada canónica de la EPL ('YYYY/YY') dada una fecha."""
    ts = pd.Timestamp(dt)
    if ts.month >= 7:
        return f"{ts.year}/{str(ts.year + 1)[-2:]}"
    return f"{ts.year - 1}/{str(ts.year)[-2:]}"


def normalize_team_name(name: str, known_teams: Iterable[str] | None = None) -> str:
    """Normaliza un nombre o alias de equipo de forma insensible a mayúsculas y espacios."""
    if not isinstance(name, str):
        return name
    clean = " ".join(name.strip().split())
    lowered = clean.lower()
    if lowered in TEAM_ALIASES:
        return TEAM_ALIASES[lowered]
    if known_teams is not None:
        known_lookup = {team.lower(): team for team in known_teams}
        if lowered in known_lookup:
            return known_lookup[lowered]
    return clean
