# Indicator Variant Reference

Date: 2026-05-10

These tables preserve exploratory full-period backtests for possible later use. The test period is 1960-10-14 through 2026-05-08, using the extended U.S. equity proxy, cash/risk-free series, and the current macro-data implementation.

## CAGR By Decade Summary

Benchmark is buy-and-hold CAGR for each decade. `# Better` counts decades where the variant CAGR exceeded buy-and-hold CAGR.

| Group | Variant | Full CAGR | # Better | Worst Decade | Best Decade |
|---|---|---:|---:|---|---|
| Current | All indicators; UNRATE=2; gate >=2 | 11.5% | 4 | 2000s (5.4%) | 1980s (17.7%) |
| Only one | UNRATE | 12.0% | 4 | 2000s (8.1%) | 1980s (17.7%) |
| Only one | Retail Sales | 10.8% | 2 | 2000s (1.0%) | 1990s (17.8%) |
| Only one | Industrial Production | 11.7% | 3 | 1970s (4.2%) | 1980s (17.9%) |
| Only one | Employment | 10.9% | 2 | 2000s (3.0%) | 1980s (18.3%) |
| Only one | Real Income | 10.9% | 3 | 2000s (3.3%) | 1980s (20.0%) |
| Only one | Housing Starts | 12.3% | 6 | 2000s (2.5%) | 1980s (18.1%) |
| All but one | Excluding UNRATE | 12.1% | 3 | 2000s (5.1%) | 1980s (17.9%) |
| All but one | Excluding Retail Sales | 11.4% | 4 | 2000s (5.5%) | 1980s (17.7%) |
| All but one | Excluding Industrial Production | 11.3% | 4 | 2000s (5.4%) | 1980s (17.7%) |
| All but one | Excluding Employment | 12.0% | 4 | 2000s (7.6%) | 1980s (17.7%) |
| All but one | Excluding Real Income | 11.8% | 4 | 2000s (7.6%) | 1980s (17.7%) |
| All but one | Excluding Housing Starts | 11.5% | 4 | 2000s (5.5%) | 1980s (17.7%) |
| Combo | UNRATE + Employment; gate >=1 | 11.4% | 4 | 2000s (5.5%) | 1980s (17.7%) |

Buy-and-hold decade CAGRs used as benchmark: 1960s 9.0%, 1970s 5.6%, 1980s 17.2%, 1990s 17.8%, 2000s -0.9%, 2010s 13.3%, 2020s 15.4%.

## Sharpe By Decade Summary

Benchmark is buy-and-hold Sharpe for each decade. `# Better` counts decades where the variant Sharpe exceeded buy-and-hold Sharpe.

| Group | Variant | Full Sharpe | # Better | Worst Decade | Best Decade |
|---|---|---:|---:|---|---|
| Current | All indicators; UNRATE=2; gate >=2 | 0.57 | 4 | 2000s (0.26) | 1990s (0.78) |
| Only one | UNRATE | 0.58 | 4 | 1970s (0.35) | 2010s (0.82) |
| Only one | Retail Sales | 0.48 | 1 | 2000s (-0.04) | 2010s (0.90) |
| Only one | Industrial Production | 0.54 | 3 | 1970s (-0.10) | 2010s (0.90) |
| Only one | Employment | 0.49 | 2 | 1970s (-0.07) | 1990s (0.85) |
| Only one | Real Income | 0.55 | 4 | 2000s (0.10) | 1990s (0.80) |
| Only one | Housing Starts | 0.58 | 5 | 2000s (0.06) | 2010s (0.90) |
| All but one | Excluding UNRATE | 0.59 | 5 | 2000s (0.23) | 1990s (0.87) |
| All but one | Excluding Retail Sales | 0.56 | 4 | 2000s (0.27) | 1990s (0.78) |
| All but one | Excluding Industrial Production | 0.55 | 4 | 2000s (0.26) | 1990s (0.78) |
| All but one | Excluding Employment | 0.59 | 4 | 1970s (0.35) | 2010s (0.80) |
| All but one | Excluding Real Income | 0.57 | 4 | 1970s (0.35) | 2010s (0.82) |
| All but one | Excluding Housing Starts | 0.57 | 4 | 2000s (0.27) | 1990s (0.78) |
| Combo | UNRATE + Employment; gate >=1 | 0.55 | 4 | 2000s (0.27) | 1990s (0.78) |

Buy-and-hold decade Sharpes used as benchmark: 1960s 0.53, 1970s 0.03, 1980s 0.51, 1990s 0.87, 2000s -0.05, 2010s 0.90, 2020s 0.68.

## Max Drawdown By Decade Summary

Benchmark is buy-and-hold max drawdown for each decade. `# Better` counts decades where the variant drawdown was less severe than buy-and-hold.

| Group | Variant | Full Max DD | # Better | Worst Decade | Best Decade |
|---|---|---:|---:|---|---|
| Current | All indicators; UNRATE=2; gate >=2 | -33.0% | 6 | 1980s (-33.0%) | 1990s (-19.0%) |
| Only one | UNRATE | -33.7% | 6 | 2020s (-33.7%) | 2000s (-18.7%) |
| Only one | Retail Sales | -52.9% | 1 | 2000s (-52.9%) | 1990s (-19.2%) |
| Only one | Industrial Production | -43.8% | 5 | 1970s (-43.8%) | 1990s (-19.2%) |
| Only one | Employment | -44.9% | 2 | 1970s (-44.9%) | 1990s (-19.2%) |
| Only one | Real Income | -33.0% | 5 | 2000s (-27.3%) | 1980s (-17.4%) |
| Only one | Housing Starts | -45.5% | 4 | 2000s (-45.5%) | 1970s (-14.8%) |
| All but one | Excluding UNRATE | -33.0% | 4 | 1980s (-33.0%) | 1990s (-19.0%) |
| All but one | Excluding Retail Sales | -33.0% | 6 | 1980s (-33.0%) | 2000s (-18.7%) |
| All but one | Excluding Industrial Production | -33.7% | 5 | 2020s (-33.7%) | 1990s (-19.0%) |
| All but one | Excluding Employment | -33.0% | 7 | 1980s (-33.0%) | 2000s (-18.7%) |
| All but one | Excluding Real Income | -33.7% | 6 | 2020s (-33.7%) | 2000s (-18.7%) |
| All but one | Excluding Housing Starts | -33.0% | 6 | 1980s (-33.0%) | 2000s (-18.7%) |
| Combo | UNRATE + Employment; gate >=1 | -33.7% | 5 | 2020s (-33.7%) | 2000s (-18.7%) |

Buy-and-hold decade max drawdowns used as benchmark: 1960s -26.7%, 1970s -44.9%, 1980s -33.0%, 1990s -19.2%, 2000s -55.2%, 2010s -19.4%, 2020s -33.7%.

## Additional Recent Tests

UNRATE and employment variants, with each included indicator worth 1 point and timing on at score >= 1:

| Variant | Final Equity | CAGR | Vol | Sharpe | Max DD | Avg % Invested | Timing On % |
|---|---:|---:|---:|---:|---:|---:|---:|
| UNRATE only | $16.43M | 12.0% | 13.9% | 0.58 | -33.7% | 87.9% | 36.4% |
| Employment only | $9.02M | 10.9% | 14.9% | 0.49 | -44.9% | 95.3% | 16.5% |
| UNRATE + Employment | $11.63M | 11.4% | 13.7% | 0.55 | -33.7% | 87.0% | 38.9% |

Drop UNRATE and employment growth, using the remaining four indicators:

| Timing Gate | Final Equity | CAGR | Vol | Sharpe | Max DD | Avg % Invested | Timing On % |
|---:|---:|---:|---:|---:|---:|---:|---:|
| Score >= 1 | $12.00M | 11.4% | 12.0% | 0.61 | -26.7% | 82.3% | 62.0% |
| Score >= 2 | $20.57M | 12.3% | 14.1% | 0.60 | -33.0% | 90.5% | 25.7% |
