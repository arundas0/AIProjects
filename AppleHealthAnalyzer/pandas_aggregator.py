from __future__ import annotations

from typing import Any, Dict, List, Optional
import math

import pandas as pd


# These thresholds are defaults; tune them to your data units if needed.
GLUCOSE_HIGH_THRESHOLD = 140.0  # mg/dL
OXYGEN_LOW_THRESHOLD = 0.90     # fraction (0-1)


def build_aggregations(records: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Build pandas-based daily aggregations for model input.
    Returns a structured dict of tables (list-of-dicts).
    """
    if not records:
        return {}

    df = pd.DataFrame(records)
    if df.empty:
        return {}

    df = df.copy()
    df["value"] = pd.to_numeric(df.get("value"), errors="coerce")
    df["start_dt"] = pd.to_datetime(df.get("start_date"), errors="coerce")
    df["end_dt"] = pd.to_datetime(df.get("end_date"), errors="coerce")
    df = df.dropna(subset=["start_dt"])
    df["date"] = df["start_dt"].dt.date

    steps_calories = _clean_records(_build_steps_calories_circadian(df))
    heart_rate_stats = _clean_records(_build_heart_rate_stats(df))
    glucose_oxygen = _clean_records(_build_glucose_oxygen_thresholds(df))
    sleep_shift = _clean_records(_build_sleep_session_shift(df))

    return {
        "steps_calories_circadian": steps_calories,
        "heart_rate_stats": heart_rate_stats,
        "glucose_oxygen_thresholds": glucose_oxygen,
        "sleep_session_shift": sleep_shift,
    }


def _clean_records(rows: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Ensure JSON-safe values by replacing NaN/inf with None.
    """
    cleaned: List[Dict[str, Any]] = []
    for row in rows:
        new_row: Dict[str, Any] = {}
        for key, value in row.items():
            if value is None:
                new_row[key] = None
                continue
            if isinstance(value, float):
                if math.isfinite(value):
                    new_row[key] = value
                else:
                    new_row[key] = None
                continue
            if pd.isna(value):
                new_row[key] = None
                continue
            new_row[key] = value
        cleaned.append(new_row)
    return cleaned


def _bucket_circadian(hour: int) -> str:
    """
    Map hour to circadian bucket.
    Morn: 04-11, Aft: 12-17, Eve: 18-03.
    """
    if 4 <= hour <= 11:
        return "Morn"
    if 12 <= hour <= 17:
        return "Aft"
    return "Eve"


def _build_steps_calories_circadian(df: pd.DataFrame) -> List[Dict[str, Any]]:
    steps = df[df["type"].str.contains("StepCount", na=False)].copy()
    calories = df[df["type"].str.contains("ActiveEnergyBurned", na=False)].copy()

    def agg_circadian(frame: pd.DataFrame, value_col: str) -> pd.DataFrame:
        if frame.empty:
            return pd.DataFrame(columns=["date", "bucket", value_col])
        frame["bucket"] = frame["start_dt"].dt.hour.map(_bucket_circadian)
        grouped = (
            frame.groupby(["date", "bucket"], as_index=False)["value"]
            .sum()
            .rename(columns={"value": value_col})
        )
        return grouped

    steps_g = agg_circadian(steps, "steps")
    calories_g = agg_circadian(calories, "calories")

    # Pivot to wide format and merge steps + calories by date.
    steps_w = steps_g.pivot(index="date", columns="bucket", values="steps").fillna(0)
    calories_w = calories_g.pivot(index="date", columns="bucket", values="calories").fillna(0)

    steps_w.columns = [f"steps_{c.lower()}" for c in steps_w.columns]
    calories_w.columns = [f"calories_{c.lower()}" for c in calories_w.columns]

    merged = (
        pd.concat([steps_w, calories_w], axis=1)
        .reset_index()
        .sort_values("date")
        .fillna(0)
    )
    if "date" in merged.columns:
        merged["date"] = merged["date"].astype(str)

    return merged.tail(365).to_dict(orient="records")


def _build_heart_rate_stats(df: pd.DataFrame) -> List[Dict[str, Any]]:
    hr = df[df["type"].str.contains("HeartRate", na=False)].copy()
    if hr.empty:
        return []

    daily = hr.groupby("date")["value"].agg(["min", "max", "median"]).reset_index()
    daily = daily.rename(
        columns={"min": "min_bpm", "max": "max_bpm", "median": "median_bpm"}
    )
    if "date" in daily.columns:
        daily["date"] = daily["date"].astype(str)
    return daily.tail(365).to_dict(orient="records")


def _normalize_oxygen_value(value: float) -> float:
    # Some exports use 0-1, others use percent like 95.
    if value is None:
        return value
    if value > 1.0:
        return value / 100.0
    return value


def _build_glucose_oxygen_thresholds(df: pd.DataFrame) -> List[Dict[str, Any]]:
    glucose = df[df["type"].str.contains("BloodGlucose", na=False)].copy()
    oxygen = df[df["type"].str.contains("OxygenSaturation", na=False)].copy()

    if not oxygen.empty:
        oxygen["value"] = oxygen["value"].map(_normalize_oxygen_value)

    glucose_daily = (
        glucose.assign(is_high=glucose["value"] >= GLUCOSE_HIGH_THRESHOLD)
        .groupby("date")["is_high"]
        .sum()
        .rename("glucose_high_count")
    )

    oxygen_daily = (
        oxygen.assign(is_low=oxygen["value"] <= OXYGEN_LOW_THRESHOLD)
        .groupby("date")["is_low"]
        .sum()
        .rename("oxygen_low_count")
    )

    combined = pd.concat([glucose_daily, oxygen_daily], axis=1).fillna(0).reset_index()
    if "date" in combined.columns:
        combined["date"] = combined["date"].astype(str)
    return combined.tail(365).to_dict(orient="records")


def _build_sleep_session_shift(df: pd.DataFrame) -> List[Dict[str, Any]]:
    sleep = df[df["type"].str.contains("Sleep", na=False)].copy()
    if sleep.empty:
        return []

    sleep = sleep.dropna(subset=["end_dt"])
    if sleep.empty:
        return []

    # Pick earliest start per day as the primary sleep session start.
    daily = sleep.groupby("date").agg(
        sleep_start=("start_dt", "min"),
        sleep_end=("end_dt", "max"),
    ).reset_index().sort_values("date")

    daily["sleep_start_min"] = daily["sleep_start"].dt.hour * 60 + daily["sleep_start"].dt.minute
    daily["shift_minutes"] = daily["sleep_start_min"].diff().fillna(0).astype(int)

    return [
        {
            "date": str(row["date"]),
            "sleep_start": row["sleep_start"].isoformat(),
            "sleep_end": row["sleep_end"].isoformat(),
            "shift_minutes": int(row["shift_minutes"]),
        }
        for _, row in daily.tail(365).iterrows()
    ]
