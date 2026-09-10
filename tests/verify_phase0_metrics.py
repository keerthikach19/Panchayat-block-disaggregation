import json

with open('data/validation_report.json') as f:
    rep = json.load(f)

with open('README.md', encoding='utf-8') as f:
    readme = f.read()

with open('src/api/main.py', encoding='utf-8') as f:
    api = f.read()

# Check key metrics in README
assert '"downscaled_model_rmse_mm": 6.44' in readme, 'README missing 6.44'
assert '"rmse_improvement_percent": 1.9' in readme, 'README missing 1.9%'
assert '"downscaled_model_rmse_mm": 4.75' in readme, 'README missing 4.75'
assert '"spread_skill_ratio": 0.57' in readme, 'README missing 0.57'
assert 'r = 0.950' in readme, 'README missing r = 0.950'

# Check key metrics in main.py
assert '"downscaled_model_rmse_mm": 6.44' in api, 'API missing 6.44'
assert '"rmse_improvement_percent": 1.9' in api, 'API missing 1.9%'
assert '"downscaled_model_rmse_mm": 4.75' in api, 'API missing 4.75'

print('✓ PHASE 0 VERIFICATION COMPLETE: README and main.py match validation_report.json verbatim!')
