import numpy as np
import pandas as pd

from simulation.site_demand_forecast import SiteDemandForecaster


print("TIME-VARYING XGBOOST SITE FORECAST TEST")

forecaster = SiteDemandForecaster()

site_timestamps = pd.date_range("2026-01-01 00:00", "2026-01-01 23:45", freq="15min")
site_df = pd.DataFrame(
    {
        "timestamp": site_timestamps,
        "building_demand_kw": [120.0 + 8.0 * (i % 12) + 2.0 * ((i // 12) % 2) for i in range(len(site_timestamps))],
    }
)

profile = forecaster.forecast_site_demand_profile(site_df)

print(f"Forecast records: {len(profile)}")
print("First few predictions:")
print(
    profile[
        [
            "timestamp",
            "current_site_demand_kw",
            "predicted_site_demand_kw",
            "reference_current_demand_kw",
            "reference_predicted_demand_kw",
        ]
    ]
    .head()
    .to_string(index=False)
)

predictions = profile["predicted_site_demand_kw"].astype(float)
print("\nForecast statistics:")
print(f"Minimum predicted site demand: {predictions.min():.3f} kW")
print(f"Maximum predicted site demand: {predictions.max():.3f} kW")
print(f"Mean predicted site demand: {predictions.mean():.3f} kW")
print(f"Std predicted site demand: {predictions.std():.3f} kW")
print(f"Number of unique forecast values: {predictions.nunique()}")

assert len(profile) == 96, f"Expected 96 forecast rows, found {len(profile)}"
assert predictions.notna().all(), "NaN predictions detected"
assert (predictions >= 0).all(), "Negative predicted demand detected"
assert predictions.nunique() > 1, "Forecast is not time-varying"
assert (predictions.max() - predictions.min()) > 0, "Forecast variation is zero"
assert (profile["forecast_timestamp"] - profile["timestamp"] == pd.Timedelta(minutes=15)).all(), "Interval spacing invalid"
assert (profile["reference_current_demand_kw"].notna() & profile["reference_predicted_demand_kw"].notna()).all(), "Reference forecast missing values"
scaling_values = profile["scaling_ratio"].astype(float)
assert scaling_values.notna().all(), "Scaling ratio missing values"
assert np.isfinite(scaling_values.to_numpy()).all(), "Scaling ratio not finite"

print("\nTIME-VARYING FORECAST: PASSED")
