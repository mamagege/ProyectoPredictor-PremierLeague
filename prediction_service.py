"""
prediction_service.py
Módulo reutilizable para la predicción probabilística de partidos de fútbol (EPL)
mediante la Red Neuronal Profunda (Deep MLP) entrenada.
"""

import os
import json
import warnings
warnings.filterwarnings('ignore')
import joblib
import numpy as np
import pandas as pd
from datetime import datetime
import tensorflow as tf
from tensorflow import keras

def _resolve_path(p):
    if os.path.isabs(p) and os.path.exists(p):
        return p
    if os.path.exists(p):
        return p
    base_dir = os.path.dirname(os.path.abspath(__file__))
    cand1 = os.path.join(base_dir, p)
    if os.path.exists(cand1):
        return cand1
    cand2 = os.path.join(base_dir, '..', p)
    if os.path.exists(cand2):
        return cand2
    cand3 = os.path.join(os.getcwd(), 'hito2', p)
    if os.path.exists(cand3):
        return cand3
    return p


class EPLPredictor:
    def __init__(self, model_path='models/best_deep_mlp.keras',
                 scaler_path='models/scaler.pkl',
                 feature_names_path='models/feature_names.json',
                 epl_csv='datasets/English Premier League Match Data (2000-2025)/epl_final.csv',
                 matches_csv='datasets/Club Football Match Data (2000 - 2026)/Matches.csv',
                 prem_csv='datasets/Premier League (1993 - Present)/PremierLeague.csv'):
        
        model_path = _resolve_path(model_path)
        scaler_path = _resolve_path(scaler_path)
        feature_names_path = _resolve_path(feature_names_path)
        epl_csv = _resolve_path(epl_csv)
        matches_csv = _resolve_path(matches_csv)
        prem_csv = _resolve_path(prem_csv)
        
        self.model = keras.models.load_model(model_path)
        self.scaler = joblib.load(scaler_path)
        with open(feature_names_path, 'r', encoding='utf-8') as f:
            self.feature_names = json.load(f)
            
        # Cargar base de datos histórica para cómputo de estado del arte pre-partido
        self.epl = pd.read_csv(epl_csv)
        self.matches = pd.read_csv(matches_csv, low_memory=False)
        self.matches_e0 = self.matches[self.matches['Division'] == 'E0'].copy()
        self.matches_e0['HomeTeam'] = self.matches_e0['HomeTeam'].replace({'Nottm Forest': "Nott'm Forest"})
        self.matches_e0['AwayTeam'] = self.matches_e0['AwayTeam'].replace({'Nottm Forest': "Nott'm Forest"})
        
        self.prem = pd.read_csv(prem_csv, low_memory=False)
        
        # Equipos conocidos
        self.known_teams = set(self.epl['HomeTeam'].unique()).union(set(self.matches_e0['HomeTeam'].unique()))
        
        # Pre-procesar historial unificado para búsquedas rápidas
        m1 = pd.merge(
            self.epl,
            self.prem[['Date', 'HomeTeam', 'AwayTeam', 'B365HomeTeam', 'B365Draw', 'B365AwayTeam']],
            left_on=['MatchDate', 'HomeTeam', 'AwayTeam'],
            right_on=['Date', 'HomeTeam', 'AwayTeam'],
            how='inner'
        )
        self.df_history = pd.merge(
            m1,
            self.matches_e0[['MatchDate', 'HomeTeam', 'AwayTeam', 'HomeElo', 'AwayElo', 'Form3Home', 'Form5Home', 'Form3Away', 'Form5Away', 'OddHome', 'OddDraw', 'OddAway']],
            on=['MatchDate', 'HomeTeam', 'AwayTeam'],
            how='inner'
        )
        self.df_history['MatchDate'] = pd.to_datetime(self.df_history['MatchDate'])
        self.df_history = self.df_history.sort_values(['MatchDate', 'HomeTeam']).reset_index(drop=True)
        
    def get_latest_team_stats(self, team_name, target_date=None, k=5):
        """Calcula el estado histórico estricto de un equipo antes de target_date."""
        if target_date is not None:
            target_date = pd.to_datetime(target_date)
            hist = self.df_history[((self.df_history['HomeTeam'] == team_name) | (self.df_history['AwayTeam'] == team_name)) & (self.df_history['MatchDate'] < target_date)]
        else:
            hist = self.df_history[(self.df_history['HomeTeam'] == team_name) | (self.df_history['AwayTeam'] == team_name)]
            
        if hist.empty:
            return None
            
        recent = hist.tail(k)
        pts_list = []
        gf_list = []
        ga_list = []
        shots_list = []
        sot_list = []
        
        for _, row in recent.iterrows():
            if row['HomeTeam'] == team_name:
                res = row['FullTimeResult']
                pts = 3 if res == 'H' else (1 if res == 'D' else 0)
                gf = row['FullTimeHomeGoals']
                ga = row['FullTimeAwayGoals']
                sh = row['HomeShots'] if pd.notna(row['HomeShots']) else 11.0
                sot = row['HomeShotsOnTarget'] if pd.notna(row['HomeShotsOnTarget']) else 4.0
                elo = row['HomeElo'] if pd.notna(row['HomeElo']) else 1500.0
                form5 = row['Form5Home'] if pd.notna(row['Form5Home']) else 7.0
                form3 = row['Form3Home'] if pd.notna(row['Form3Home']) else 4.0
            else:
                res = row['FullTimeResult']
                pts = 3 if res == 'A' else (1 if res == 'D' else 0)
                gf = row['FullTimeAwayGoals']
                ga = row['FullTimeHomeGoals']
                sh = row['AwayShots'] if pd.notna(row['AwayShots']) else 11.0
                sot = row['AwayShotsOnTarget'] if pd.notna(row['AwayShotsOnTarget']) else 4.0
                elo = row['AwayElo'] if pd.notna(row['AwayElo']) else 1500.0
                form5 = row['Form5Away'] if pd.notna(row['Form5Away']) else 7.0
                form3 = row['Form3Away'] if pd.notna(row['Form3Away']) else 4.0
                
            pts_list.append(pts)
            gf_list.append(gf)
            ga_list.append(ga)
            shots_list.append(sh)
            sot_list.append(sot)
            
        last_match = hist.iloc[-1]
        last_date = last_match['MatchDate']
        ref_date = target_date if target_date is not None else self.df_history['MatchDate'].max()
        rest_days = min(30.0, max(1.0, float((ref_date - last_date).days)))
        
        # Season stats
        current_season = last_match['Season']
        season_hist = hist[hist['Season'] == current_season]
        s_pts = 0
        s_gf = 0
        s_ga = 0
        for _, row in season_hist.iterrows():
            if row['HomeTeam'] == team_name:
                s_pts += 3 if row['FullTimeResult'] == 'H' else (1 if row['FullTimeResult'] == 'D' else 0)
                s_gf += row['FullTimeHomeGoals']
                s_ga += row['FullTimeAwayGoals']
            else:
                s_pts += 3 if row['FullTimeResult'] == 'A' else (1 if row['FullTimeResult'] == 'D' else 0)
                s_gf += row['FullTimeAwayGoals']
                s_ga += row['FullTimeHomeGoals']
                
        return {
            'elo': elo,
            'form5': form5,
            'form3': form3,
            'rolling_pts5': np.mean(pts_list),
            'rolling_gf5': np.mean(gf_list),
            'rolling_ga5': np.mean(ga_list),
            'rolling_shots5': np.mean(shots_list),
            'rolling_sot5': np.mean(sot_list),
            'rest_days': rest_days,
            'season_pts': s_pts,
            'season_gd': s_gf - s_ga
        }

    def get_h2h_stats(self, home_team, away_team, target_date=None):
        if target_date is not None:
            target_date = pd.to_datetime(target_date)
            h2h = self.df_history[
                (((self.df_history['HomeTeam'] == home_team) & (self.df_history['AwayTeam'] == away_team)) |
                 ((self.df_history['HomeTeam'] == away_team) & (self.df_history['AwayTeam'] == home_team))) &
                (self.df_history['MatchDate'] < target_date)
            ]
        else:
            h2h = self.df_history[
                ((self.df_history['HomeTeam'] == home_team) & (self.df_history['AwayTeam'] == away_team)) |
                ((self.df_history['HomeTeam'] == away_team) & (self.df_history['AwayTeam'] == home_team))
            ]
            
        n = len(h2h)
        if n == 0:
            return 0.45, 0.25, 0.30
            
        hw = sum(1 for _, r in h2h.iterrows() if (r['HomeTeam'] == home_team and r['FullTimeResult'] == 'H') or (r['AwayTeam'] == home_team and r['FullTimeResult'] == 'A'))
        d = sum(1 for _, r in h2h.iterrows() if r['FullTimeResult'] == 'D')
        aw = sum(1 for _, r in h2h.iterrows() if (r['HomeTeam'] == away_team and r['FullTimeResult'] == 'H') or (r['AwayTeam'] == away_team and r['FullTimeResult'] == 'A'))
        
        return hw / n, d / n, aw / n

    TEAM_ALIASES = {
        'manchester city': 'Man City',
        'mancity': 'Man City',
        'manchester united': 'Man United',
        'man united': 'Man United',
        'manutd': 'Man United',
        'tottenham hotspur': 'Tottenham',
        'spurs': 'Tottenham',
        'newcastle united': 'Newcastle',
        'wolverhampton': 'Wolves',
        'wolverhampton wanderers': 'Wolves',
        'west ham united': 'West Ham',
        'brighton & hove albion': 'Brighton',
        'brighton and hove albion': 'Brighton',
        'afc bournemouth': 'Bournemouth',
        'leicester city': 'Leicester',
        'norwich city': 'Norwich',
        'cardiff city': 'Cardiff',
        'swansea city': 'Swansea',
        'hull city': 'Hull',
        'stoke city': 'Stoke',
        'ipswich town': 'Ipswich',
        'luton town': 'Luton',
        'huddersfield town': 'Huddersfield',
        'west bromwich albion': 'West Brom',
        'west bromwich': 'West Brom',
        'nottingham forest': "Nott'm Forest",
        'nottingham': "Nott'm Forest",
        'nottm forest': "Nott'm Forest",
        'sheffield utd': 'Sheffield United',
        'sheff utd': 'Sheffield United',
        'leeds united': 'Leeds',
    }

    def normalize_team(self, name):
        if not isinstance(name, str):
            return name
        clean = name.strip()
        return self.TEAM_ALIASES.get(clean.lower(), clean)

    def predict_match(self, home_team, away_team, match_date=None, odds=None):
        """
        Predice las probabilidades de resultado de un partido de la EPL.
        
        Parámetros:
            home_team (str): Nombre del equipo local.
            away_team (str): Nombre del equipo visitante.
            match_date (str/datetime, opcional): Fecha programada del partido (YYYY-MM-DD).
            odds (tuple/list, opcional): Cuotas decimales pre-partido [Odd_H, Odd_D, Odd_A].
            
        Retorna:
            dict con probabilidades porcentuales, clase más probable y estado del pronóstico.
        """
        home_team = self.normalize_team(home_team)
        away_team = self.normalize_team(away_team)

        # Validación de equipos
        if home_team not in self.known_teams:
            return {
                'status': 'error',
                'message': f"Equipo local no reconocido: '{home_team}'. No se pueden generar estadísticas válidas sin inventar datos.",
                'known_teams_sample': sorted(list(self.known_teams))[:10]
            }
        if away_team not in self.known_teams:
            return {
                'status': 'error',
                'message': f"Equipo visitante no reconocido: '{away_team}'. No se pueden generar estadísticas válidas sin inventar datos.",
                'known_teams_sample': sorted(list(self.known_teams))[:10]
            }
        if home_team == away_team:
            return {
                'status': 'error',
                'message': "Un equipo no puede jugar contra sí mismo."
            }
            
        h_stats = self.get_latest_team_stats(home_team, match_date)
        a_stats = self.get_latest_team_stats(away_team, match_date)
        
        if h_stats is None or a_stats is None:
            return {
                'status': 'error',
                'message': "Historial insuficiente para calcular variables pre-partido antes de la fecha especificada."
            }
            
        # Mercado: si se proporcionan cuotas, calcular probabilidades implícitas; si no, derivar de Elo
        if odds is not None and len(odds) == 3 and all(o > 1.0 for o in odds):
            raw_h, raw_d, raw_a = 1.0 / odds[0], 1.0 / odds[1], 1.0 / odds[2]
            overround = raw_h + raw_d + raw_a
            p_mkt_h, p_mkt_d, p_mkt_a = raw_h / overround, raw_d / overround, raw_a / overround
        else:
            diff_elo_val = h_stats['elo'] - a_stats['elo']
            p_elo_base = 1.0 / (1.0 + 10.0 ** ((-diff_elo_val - 100.0) / 400.0))
            p_mkt_h = float(np.clip(p_elo_base, 0.15, 0.85))
            p_mkt_d = 0.25
            p_mkt_a = float(np.clip(1.0 - p_mkt_h - p_mkt_d, 0.10, 0.75))
            sum_p = p_mkt_h + p_mkt_d + p_mkt_a
            p_mkt_h /= sum_p; p_mkt_d /= sum_p; p_mkt_a /= sum_p
            
        h2h_h, h2h_d, h2h_a = self.get_h2h_stats(home_team, away_team, match_date)
        
        diff_elo = h_stats['elo'] - a_stats['elo']
        elo_prob_home = 1.0 / (1.0 + 10.0 ** ((-diff_elo - 100.0) / 400.0))
        
        feature_dict = {
            'ProbMarket_Home': p_mkt_h,
            'ProbMarket_Draw': p_mkt_d,
            'ProbMarket_Away': p_mkt_a,
            'HomeElo': h_stats['elo'],
            'AwayElo': a_stats['elo'],
            'DiffElo': diff_elo,
            'EloProb_Home': elo_prob_home,
            'Form5Home': h_stats['form5'],
            'Form5Away': a_stats['form5'],
            'DiffForm5': h_stats['form5'] - a_stats['form5'],
            'Form3Home': h_stats['form3'],
            'Form3Away': a_stats['form3'],
            'DiffForm3': h_stats['form3'] - a_stats['form3'],
            'RollingPts5_Home': h_stats['rolling_pts5'],
            'RollingPts5_Away': a_stats['rolling_pts5'],
            'DiffRollingPts5': h_stats['rolling_pts5'] - a_stats['rolling_pts5'],
            'RollingGF5_Home': h_stats['rolling_gf5'],
            'RollingGF5_Away': a_stats['rolling_gf5'],
            'DiffRollingGF5': h_stats['rolling_gf5'] - a_stats['rolling_gf5'],
            'RollingGA5_Home': h_stats['rolling_ga5'],
            'RollingGA5_Away': a_stats['rolling_ga5'],
            'DiffRollingGA5': h_stats['rolling_ga5'] - a_stats['rolling_ga5'],
            'RollingShots5_Home': h_stats['rolling_shots5'],
            'RollingShots5_Away': a_stats['rolling_shots5'],
            'DiffRollingShots5': h_stats['rolling_shots5'] - a_stats['rolling_shots5'],
            'RollingSoT5_Home': h_stats['rolling_sot5'],
            'RollingSoT5_Away': a_stats['rolling_sot5'],
            'DiffRollingSoT5': h_stats['rolling_sot5'] - a_stats['rolling_sot5'],
            'RestDays_Home': h_stats['rest_days'],
            'RestDays_Away': a_stats['rest_days'],
            'DiffRestDays': h_stats['rest_days'] - a_stats['rest_days'],
            'SeasonPts_Home': h_stats['season_pts'],
            'SeasonPts_Away': a_stats['season_pts'],
            'DiffSeasonPts': h_stats['season_pts'] - a_stats['season_pts'],
            'SeasonGD_Home': h_stats['season_gd'],
            'SeasonGD_Away': a_stats['season_gd'],
            'DiffSeasonGD': h_stats['season_gd'] - a_stats['season_gd'],
            'H2H_HomeWins': h2h_h,
            'H2H_Draws': h2h_d,
            'H2H_AwayWins': h2h_a
        }
        
        # Construir vector alineado exactamente con feature_names
        x_vec = np.array([[feature_dict[col] for col in self.feature_names]])
        x_scaled = self.scaler.transform(x_vec)
        
        # Inferencia con la red neuronal profunda
        probs = self.model.predict(x_scaled, verbose=0)[0]
        
        p_home = float(probs[0])
        p_draw = float(probs[1])
        p_away = float(probs[2])
        
        # Asegurar suma 100%
        total_p = p_home + p_draw + p_away
        p_home_pct = round((p_home / total_p) * 100.0, 1)
        p_draw_pct = round((p_draw / total_p) * 100.0, 1)
        p_away_pct = round((p_away / total_p) * 100.0, 1)
        
        # Ajuste de redondeo para sumar exactamente 100.0
        diff_round = round(100.0 - (p_home_pct + p_draw_pct + p_away_pct), 1)
        p_home_pct += diff_round
        
        predicted_idx = int(np.argmax([p_home, p_draw, p_away]))
        class_names = [f"Victoria de {home_team} (Local)", "Empate", f"Victoria de {away_team} (Visitante)"]
        
        return {
            'status': 'success',
            'home_team': home_team,
            'away_team': away_team,
            'match_date': str(match_date) if match_date else "Último registro disponible",
            'probabilities': {
                'Victoria (Local)': f"{p_home_pct:.1f} %",
                'Empate': f"{p_draw_pct:.1f} %",
                'Derrota (Visitante)': f"{p_away_pct:.1f} %"
            },
            'numeric_probabilities': {
                'P_Home': p_home,
                'P_Draw': p_draw,
                'P_Away': p_away
            },
            'pronostico_mas_probable': class_names[predicted_idx],
            'suma_probabilidades': f"{p_home_pct + p_draw_pct + p_away_pct:.1f} %",
            'contexto_prepartido': {
                'Elo_Local': round(h_stats['elo'], 1),
                'Elo_Visitante': round(a_stats['elo'], 1),
                'Diferencial_Elo': round(diff_elo, 1),
                'Forma5_Local': round(h_stats['form5'], 1),
                'Forma5_Visitante': round(a_stats['form5'], 1),
                'Descanso_Local_Dias': h_stats['rest_days'],
                'Descanso_Visitante_Dias': a_stats['rest_days']
            }
        }

# Función directa para coincidir con la especificación del requerimiento
def predecir_partido(equipo_local, equipo_visitante, fecha_partido=None, cuotas=None):
    predictor = EPLPredictor()
    return predictor.predict_match(equipo_local, equipo_visitante, fecha_partido, cuotas)

if __name__ == '__main__':
    print("Probando función predecir_partido...")
    p = EPLPredictor()
    
    # Caso 1: Partido clásico inglés (Arsenal vs Chelsea)
    res1 = p.predict_match('Arsenal', 'Chelsea', '2024-04-23', odds=[1.55, 4.50, 5.50])
    print("\n--- Caso 1: Arsenal vs Chelsea (2024-04-23) ---")
    print(json.dumps(res1, indent=2, ensure_ascii=False))
    
    # Caso 2: Manchester City vs Liverpool (partido parejo en la cumbre)
    res2 = p.predict_match('Man City', 'Liverpool', '2023-11-25', odds=[1.75, 4.20, 4.33])
    print("\n--- Caso 2: Man City vs Liverpool (2023-11-25) ---")
    print(json.dumps(res2, indent=2, ensure_ascii=False))
    
    # Caso 3: Hull City vs Everton (caso de estudio del Proyecto 2)
    res3 = p.predict_match('Hull', 'Everton', '2016-12-30', odds=[4.20, 3.50, 1.95])
    print("\n--- Caso 3: Hull vs Everton (2016-12-30) ---")
    print(json.dumps(res3, indent=2, ensure_ascii=False))
    
    # Caso 4: Equipo desconocido (prueba de robustez y control de errores)
    res4 = p.predict_match('Real Madrid', 'Barcelona')
    print("\n--- Caso 4: Equipo desconocido ---")
    print(json.dumps(res4, indent=2, ensure_ascii=False))
