import nfl_data_py as nfl
pfr = nfl.import_weekly_pfr([2023])
print(len(pfr.columns))
print(pfr.columns.tolist())
print(pfr[['player', 'player_id', 'game_id', 'week', 'team', 'opponent']].head())
