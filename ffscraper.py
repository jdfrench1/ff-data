import os
import sys
import requests
import pandas as pd


def fetch_passing_table(season: int = 2024) -> pd.DataFrame:
    url = f"https://www.pro-football-reference.com/years/{season}/passing.htm"
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
        )
    }
    resp = requests.get(url, headers=headers, timeout=30)
    resp.raise_for_status()

    # PFR often wraps tables in HTML comments; pandas.read_html with lxml handles this.
    tables = pd.read_html(resp.text, attrs={"id": "passing"})
    if not tables:
        raise RuntimeError("Could not locate passing table on the page.")

    df = tables[0]

    # Clean typical PFR artifacts: drop header repeat rows and index columns
    df = df.loc[:, ~df.columns.str.contains("^Unnamed")]  # drop unnamed columns
    if "Player" in df.columns:
        df = df[df["Player"] != "Player"]  # remove repeated header rows
    df = df.dropna(subset=[c for c in df.columns if c == "Player" or c == "Tm"]).copy()

    # Normalize column names
    df.columns = [str(c).strip().replace(" ", "_") for c in df.columns]
    return df.reset_index(drop=True)


def main():
    season_env = os.getenv("SEASON")
    try:
        season = int(season_env) if season_env else 2024
    except ValueError:
        season = 2024

    df = fetch_passing_table(season)
    out = "nfl_player_stats.csv"
    df.to_csv(out, index=False)
    print(f"Wrote {len(df)} rows to {out}")


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(f"Error: {exc}", file=sys.stderr)
        sys.exit(1)
