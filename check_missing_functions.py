missing_functions = [
    'get_stage_probabilities',
    'get_tournament_overview',
    'get_team_attributes',
    'get_model_methodology',
    'get_data_quality_report'
]

print("Missing functions that are imported in __init__.py:")
for func in missing_functions:
    print(f"  - {func}")

print("\nThese functions were likely part of the BigQuery implementation")
print("but were not migrated to the Athena implementation.")

# Let's check what functions actually exist
existing_functions = [
    'get_data_source_status',
    'get_teams',
    'get_players',
    'get_matches',
    'get_predictions'
]

print("\nExisting functions in athena.py:")
for func in existing_functions:
    print(f"  - {func}")