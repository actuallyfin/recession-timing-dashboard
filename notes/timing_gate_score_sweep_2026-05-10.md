# Timing Gate Score Sweep

Date: 2026-05-10

This note preserves a one-off sensitivity test for possible later use. The dashboard configuration at the time used a 7-point maximum indicator score:

- UNRATE trend: 2 points
- Real retail sales growth: 1 point
- Industrial production growth: 1 point
- Payroll employment growth: 1 point
- Real personal income growth: 1 point
- Housing starts growth: 1 point

The test used the current point-in-time FRED revision-history implementation, SPY adjusted close as the total-return price series proxy, the 200-day SMA trend rule, and the cash/risk-free return series already used by the dashboard.

## Results

| Timing gate | Final equity | CAGR | Vol | Sharpe | Max DD | Avg % invested | Timing on % |
|---:|---:|---:|---:|---:|---:|---:|---:|
| Score >= 1 | $272,054 | 10.7% | 12.9% | 0.70 | -21.5% | 81.1% | 68.4% |
| Score >= 2 | $428,016 | 12.3% | 14.5% | 0.74 | -26.6% | 86.4% | 36.2% |
| Score >= 3 | $426,334 | 12.2% | 15.5% | 0.70 | -33.7% | 89.0% | 28.3% |
| Score >= 4 | $401,317 | 12.0% | 16.4% | 0.66 | -40.6% | 93.1% | 17.0% |
| Score >= 5 | $373,217 | 11.8% | 16.9% | 0.63 | -47.5% | 96.7% | 8.2% |

## Baselines

| Strategy | Final equity | CAGR | Vol | Sharpe | Max DD | Avg % invested |
|---|---:|---:|---:|---:|---:|---:|
| 200D SMA always on | $170,527 | 9.1% | 12.1% | 0.62 | -22.4% | 77.1% |
| Buy and hold | $283,923 | 10.8% | 18.8% | 0.54 | -55.2% | 100.0% |

## Takeaway

The score >= 2 threshold produced the best result in this sweep, narrowly ahead of score >= 3 on final equity and Sharpe. Score >= 1 was much more defensive and gave up too much upside. Score >= 4 and score >= 5 waited longer to activate timing, which increased equity exposure but also increased drawdowns and lowered risk-adjusted performance.
