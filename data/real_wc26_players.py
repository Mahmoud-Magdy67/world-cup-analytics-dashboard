"""
Real FIFA World Cup 2026 player-performance loader (Kaggle / mominullptr dataset).

Source: https://www.kaggle.com/datasets/mominullptr/fifa-world-cup-2026-dataset
        CC0-1.0 (public domain). Verified stats from sofascore.com.
        1,248 WC26 squad players, 48 nations. Cross-check: player goals sum
        (297) + own goals (11) = 308 match goals, matching matches_detailed.csv.

Exposes per-player stats (goals/assists/minutes/cards/ratings), enriched with
team name, confederation, club, market value, and position group.

This REPLACES the prior data/athena.py get_players() / get_player_tournament_stats()
data layer for the player analysis page. Only real WC26 squad members appear.
"""
import os
import pandas as pd

_DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "kaggle_wc26")
_PLAYERS_FILE = os.path.join(_DATA_DIR, "player_stats.csv")
_TEAMS_FILE = os.path.join(_DATA_DIR, "teams.csv")
_SQUADS_FILE = os.path.join(_DATA_DIR, "squads_and_players.csv")

# ---------------------------------------------------------------------------
# Famous-name overrides — maps full legal name (Kaggle) → common name (Wikipedia)
# Only players whose Kaggle name differs from their famous name are listed.
# ---------------------------------------------------------------------------
_FAMOUS_NAME_OVERRIDES: dict[str, str] = {
    # Argentina
    "Lionel Andrés Messi": "Lionel Messi",
    # France
    "Masour Ousmane Dembele": "Ousmane Dembele",
    "Michael Akpovie Olise": "Michael Olise",
    "Kylian Mbappe": "Kylian Mbappé",
    # Norway
    "Erling Braut Haaland": "Erling Haaland",
    # England
    "Harry Edward Kane": "Harry Kane",
    "Jude Victor William Bellingham": "Jude Bellingham",
    "Kai Lukas Havertz": "Kai Havertz",
    "Cody Mathès Gakpo": "Cody Gakpo",
    "Marcus Rashford": "Marcus Rashford",
    "Phil Foden": "Phil Foden",
    "Bukayo Saka": "Bukayo Saka",
    "Declan Rice": "Declan Rice",
    "John Stones": "John Stones",
    "Jordan Pickford": "Jordan Pickford",
    # Netherlands
    "Virgil van Dijk": "Virgil van Dijk",
    "Frenkie de Jong": "Frenkie de Jong",
    "Memphis Depay": "Memphis Depay",
    # Spain
    "Mikel Oyarzabal": "Mikel Oyarzabal",
    "Lamine Yamal": "Lamine Yamal",
    "Nico Williams": "Nico Williams",
    "Dani Olmo": "Dani Olmo",
    "Pedri": "Pedri",
    "Gavi": "Gavi",
    "Aymeric Laporte": "Aymeric Laporte",
    "Rodri": "Rodri",
    "Alvaro Morata": "Álvaro Morata",
    "Unai Simon": "Unai Simón",
    # Brazil
    "Vinicius Junior": "Vinícius Júnior",
    "Endrick": "Endrick",
    "Rodrygo": "Rodrygo",
    "Casemiro": "Casemiro",
    "Marquinhos": "Marquinhos",
    "Alisson Becker": "Alisson Becker",
    # Portugal
    "Cristiano Ronaldo": "Cristiano Ronaldo",
    "Bruno Miguel Borges Fernandes": "Bruno Fernandes",
    "Bernardo Silva": "Bernardo Silva",
    "Ruben Dias": "Rúben Dias",
    "Joao Felix": "João Félix",
    "Rafael Leao": "Rafael Leão",
    "Diogo Jota": "Diogo Jota",
    "Nuno Mendes": "Nuno Mendes",
    # Belgium
    "Romelu Lukaku": "Romelu Lukaku",
    "Kevin De Bruyne": "Kevin De Bruyne",
    "Charles Marc De Ketelaere": "Charles De Ketelaere",
    "Jeremy Doku": "Jérémy Doku",
    "Amadou Onana": "Amadou Onana",
    "Youri Tielemans": "Youri Tielemans",
    # Germany
    "Joshua Kimmich": "Joshua Kimmich",
    "Ilkay Gündogan": "İlkay Gündoğan",
    "Kai Lukas Havertz": "Kai Havertz",
    "Florian Wirtz": "Florian Wirtz",
    "Jamal Musiala": "Jamal Musiala",
    "Antonio Rüdiger": "Antonio Rüdiger",
    "Niclas Füllkrug": "Niclas Füllkrug",
    "Deniz Undav": "Deniz Undav",
    "Jonathan Tah": "Jonathan Tah",
    # Italy
    "Federico Chiesa": "Federico Chiesa",
    "Nicolo Barella": "Nicolò Barella",
    "Gianluigi Donnarumma": "Gianluigi Donnarumma",
    "Alessandro Bastoni": "Alessandro Bastoni",
    # Croatia
    "Luka Modric": "Luka Modrić",
    "Mateo Kovacic": "Mateo Kovačić",
    "Marcelo Brozovic": "Marcelo Brozović",
    "Ivan Perisic": "Ivan Perišić",
    # Mexico
    "Julián Andrés Quinones": "Julián Quiñones",
    "Santiago Tomás Gimenez": "Santiago Giménez",
    "Edson Omar Alvarez": "Edson Álvarez",
    "Jorge Eduardo Sanchez": "Jorge Sánchez",
    "César Jasib Montes": "César Montes",
    "Jesús Daniel Gallardo": "Jesús Gallardo",
    "Luis Gerardo Chavez": "Luis Chávez",
    "Roberto Carlos Alvarado": "Roberto Alvarado",
    "Francisco Guillermo Ochoa": "Guillermo Ochoa",
    "Raúl Alonso Jimenez": "Raúl Jiménez",
    "Ernesto Alexis Vega": "Alexis Vega",
    "José Raúl Rangel": "Raúl Rangel",
    # USA
    "Christian Pulisic": "Christian Pulisic",
    "Gio Reyna": "Gio Reyna",
    "Weston McKennie": "Weston McKennie",
    "Tyler Adams": "Tyler Adams",
    "Sergino Dest": "Sergiño Dest",
    "Matt Turner": "Matt Turner",
    # Canada
    "Jonathan Christian David": "Jonathan David",
    "Alphonso Davies": "Alphonso Davies",
    "Cyle Larin": "Cyle Larin",
    "Stephen Eustaquio": "Stephen Eustáquio",
    # Colombia
    "James Rodriguez": "James Rodríguez",
    "Luis Diaz": "Luis Díaz",
    "Davinson Sanchez": "Davinson Sánchez",
    # Uruguay
    "Federico Valverde": "Federico Valverde",
    "Darwin Nunez": "Darwin Núñez",
    "Ronald Araujo": "Ronald Araújo",
    "Sergio Rochet": "Sergio Rochet",
    # Ecuador
    "Moisés Caicedo": "Moisés Caicedo",
    "Enner Valencia": "Enner Valencia",
    "Pervis Estupiñán": "Pervis Estupiñán",
    # Senegal
    "Sadio Mane": "Sadio Mané",
    "Edouard Mendy": "Édouard Mendy",
    "Kalidou Koulibaly": "Kalidou Koulibaly",
    # Morocco
    "Achraf Hakimi": "Achraf Hakimi",
    "Hakim Ziyech": "Hakim Ziyech",
    "Sofyan Amrabat": "Sofyan Amrabat",
    "Noussair Mazraoui": "Noussair Mazraoui",
    "Yassine Bounou": "Yassine Bounou",
    "Romain Saiss": "Romain Saïss",
    # Japan
    "Kaoru Mitoma": "Kaoru Mitoma",
    "Takefusa Kubo": "Takefusa Kubo",
    "Wataru Endo": "Wataru Endō",
    "Takehiro Tomiyasu": "Takehiro Tomiyasu",
    # South Korea
    "Son Heung-min": "Son Heung-min",
    "Kim Min-jae": "Kim Min-jae",
    "Lee Kang-in": "Lee Kang-in",
    "Hwang Hee-chan": "Hwang Hee-chan",
    # Australia
    "Mathew Ryan": "Mathew Ryan",
    "Aaron Mooy": "Aaron Mooy",
    # Ghana
    "Mohammed Kudus": "Mohammed Kudus",
    "Thomas Partey": "Thomas Partey",
    "Mohammed Salisu": "Mohammed Salisu",
    "André Ayew": "André Ayew",
    "Jordan Ayew": "Jordan Ayew",
    # Nigeria
    "Victor Osimhen": "Victor Osimhen",
    "Ademola Lookman": "Ademola Lookman",
    "Wilfred Ndidi": "Wilfred Ndidi",
    # Ivory Coast
    "Franck Kessié": "Franck Kessié",
    "Sébastien Haller": "Sébastien Haller",
    "Nicolas Pépé": "Nicolas Pépé",
    # Serbia
    "Aleksandar Mitrovic": "Aleksandar Mitrović",
    "Dusan Vlahovic": "Dušan Vlahović",
    "Sergej Milinkovic-Savic": "Sergej Milinković-Savić",
    # Denmark
    "Christian Eriksen": "Christian Eriksen",
    "Pierre-Emile Hojbjerg": "Pierre-Emile Højbjerg",
    "Mikkel Damsgaard": "Mikkel Damsgaard",
    "Joachim Andersen": "Joachim Andersen",
    # Sweden
    "Alexander Isak": "Alexander Isak",
    "Dejan Kulusevski": "Dejan Kulusevski",
    # Switzerland
    "Granit Xhaka": "Granit Xhaka",
    "Manuel Akanji": "Manuel Akanji",
    "Xherdan Shaqiri": "Xherdan Shaqiri",
    "Remo Freuler": "Remo Freuler",
    # Poland
    "Robert Lewandowski": "Robert Lewandowski",
    "Wojciech Szczesny": "Wojciech Szczęsny",
    "Piotr Zielinski": "Piotr Zieliński",
    # Austria
    "David Alaba": "David Alaba",
    "Marcel Sabitzer": "Marcel Sabitzer",
    "Marko Arnautovic": "Marko Arnautović",
    # Ukraine
    "Oleksandr Zinchenko": "Oleksandr Zinchenko",
    "Mykola Zhaborynskyi": "Mykola Zhaborynskyi",
    "Artem Dovbyk": "Artem Dovbyk",
    "Andriy Lunin": "Andriy Lunin",
    "Heorhiy Sudakov": "Heorhiy Sudakov",
    # Tunisia
    "Aïssa Laïdouni": "Aïssa Laïdouni",
    "Wahbi Khazri": "Wahbi Khazri",
    "Hannibal Mejbri": "Hannibal Mejbri",
    # Cameroun
    "André Onana": "André Onana",
    "Vincent Aboubakar": "Vincent Aboubakar",
    "Bryan Mbeumo": "Bryan Mbeumo",
    # Saudi Arabia
    "Salem Al-Dawsari": "Salem Al-Dawsari",
    # New Zealand
    "Chris Wood": "Chris Wood",
}


def _famous_name(full_name: str) -> str:
    """Return the common/famous name for a player, falling back to the
    original name if no override exists."""
    if not isinstance(full_name, str):
        return full_name
    return _FAMOUS_NAME_OVERRIDES.get(full_name, full_name)


def _load_raw() -> pd.DataFrame:
    """Load player_stats merged with team + squad context."""
    ps = pd.read_csv(_PLAYERS_FILE)
    teams = pd.read_csv(_TEAMS_FILE)[["team_id", "team_name", "fifa_code", "confederation"]]
    squads = pd.read_csv(_SQUADS_FILE)[["player_id", "club_team", "market_value_eur",
                                         "caps", "date_of_birth", "height_cm"]]
    df = ps.merge(teams, on="team_id", how="left").merge(squads, on="player_id", how="left")
    return df


def get_real_wc26_players() -> pd.DataFrame:
    """All 1,248 WC26 squad players with tournament stats + context.

    Returns columns (all English):
      player_id, player_name, team_id, position, matches_played, matches_started,
      minutes_played, goals, assists, shots, shots_on_target,
      yellow_cards, red_cards, penalty_goals, own_goals,
      clean_sheets, saves, goals_conceded, average_rating,
      team_name, fifa_code (nation code), confederation,
      club_team, market_value_eur, caps, date_of_birth, height_cm,
      goal_contribution (goals + assists),
      ninety_goals (goals per 90), ninety_assists (assists per 90),
      ninety_contributions (contributions per 90)
    """
    df = _load_raw()

    # Derived fields
    df["goal_contribution"] = df["goals"] + df["assists"]
    mp = df["minutes_played"].clip(lower=1)  # avoid div-by-zero
    df["ninety_goals"] = (df["goals"] / mp * 90).round(2)
    df["ninety_assists"] = (df["assists"] / mp * 90).round(2)
    df["ninety_contributions"] = (df["goal_contribution"] / mp * 90).round(2)

    # Rename for display compatibility with prior page schema
    df = df.rename(columns={
        "goals": "wc26_goals",
        "assists": "wc26_assists",
    })

    # Apply famous-name aliases to player_name itself so every downstream
    # dataframe (top_scorers, top_assists, gk_leaders, nation_contrib, etc.)
    # inherits the short name without further work.
    df["player_name"] = df["player_name"].apply(_famous_name)

    # Display aliases (added here so all derived dataframes inherit them)
    df["spotlight_name"] = df["player_name"]
    df["display_name"] = df["player_name"]
    df["nation_code"] = df["fifa_code"]
    df["wc26_minutes"] = df["minutes_played"]

    # Sort by goal contribution (goals first, then assists)
    df = df.sort_values(["goal_contribution", "wc26_goals", "wc26_assists"],
                        ascending=[False, False, False]).reset_index(drop=True)
    return df


def get_real_wc26_top_scorers(limit: int = 25) -> pd.DataFrame:
    """Tournament top scorers (sorted by goals, then assists)."""
    df = get_real_wc26_players()
    df = df[df["wc26_goals"] > 0].sort_values(["wc26_goals", "wc26_assists"], ascending=[False, False])
    return df.head(limit).reset_index(drop=True)


def get_real_wc26_top_assists(limit: int = 25) -> pd.DataFrame:
    """Tournament top assist providers (sorted by assists, then goals)."""
    df = get_real_wc26_players()
    df = df[df["wc26_assists"] > 0].sort_values(["wc26_assists", "wc26_goals"], ascending=[False, False])
    return df.head(limit).reset_index(drop=True)


def get_real_wc26_top_contributors(limit: int = 25) -> pd.DataFrame:
    """Tournament top goal contributors (goals + assists)."""
    df = get_real_wc26_players()
    df = df[df["goal_contribution"] > 0].sort_values(
        ["goal_contribution", "wc26_goals", "wc26_assists"], ascending=[False, False, False])
    return df.head(limit).reset_index(drop=True)


def get_real_wc26_player_summary() -> pd.DataFrame:
    """Tournament-level summary metrics (one row)."""
    df = get_real_wc26_players()
    return pd.DataFrame([{
        "players_tracked": len(df),
        "wc26_goals": int(df["wc26_goals"].sum()),
        "wc26_assists": int(df["wc26_assists"].sum()),
        "goal_contributions": int(df["goal_contribution"].sum()),
        "active_nations": int(df["team_name"].nunique()),
        "players_with_goals": int((df["wc26_goals"] > 0).sum()),
        "players_with_assists": int((df["wc26_assists"] > 0).sum()),
        "players_with_contributions": int((df["goal_contribution"] > 0).sum()),
        "golden_boot": df.sort_values(["wc26_goals", "wc26_assists"], ascending=[False, False]).iloc[0]["player_name"],
        "golden_boot_goals": int(df["wc26_goals"].max()),
        "playmaker": df.sort_values(["wc26_assists", "wc26_goals"], ascending=[False, False]).iloc[0]["player_name"],
        "playmaker_assists": int(df["wc26_assists"].max()),
    }])


def get_real_wc26_nation_contributions() -> pd.DataFrame:
    """Per-team aggregate goals + assists (for nation-level contribution charts)."""
    df = get_real_wc26_players()
    agg = df.groupby(["team_name", "fifa_code", "confederation"]).agg(
        tgoals=("wc26_goals", "sum"),
        tassists=("wc26_assists", "sum"),
        tcontributions=("goal_contribution", "sum"),
        nplayers=("player_id", "size"),
    ).reset_index()
    return agg.sort_values(["tcontributions", "tgoals"], ascending=[False, False]).reset_index(drop=True)


def get_real_wc26_position_breakdown() -> pd.DataFrame:
    """Per-position aggregates (GK/DEF/MID/FWD)."""
    df = get_real_wc26_players()
    return df.groupby("position").agg(
        players=("player_id", "size"),
        goals=("wc26_goals", "sum"),
        assists=("wc26_assists", "sum"),
        clean_sheets=("clean_sheets", "sum"),
        yellow_cards=("yellow_cards", "sum"),
        red_cards=("red_cards", "sum"),
    ).reset_index().sort_values("goals", ascending=False).reset_index(drop=True)


def get_real_wc26_gk_leaders(limit: int = 10) -> pd.DataFrame:
    """Top goalkeepers by clean sheets, with saves/goals_conceded context."""
    df = get_real_wc26_players()
    gk = df[df["position"] == "GK"].copy()
    gk = gk.sort_values(["clean_sheets", "saves"], ascending=[False, False])
    return gk.head(limit).reset_index(drop=True)
