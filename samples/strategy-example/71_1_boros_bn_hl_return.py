"""
Boros BN-HL Return Analysis

This script processes the boros.account.csv file to calculate the rate of return.
For rows with position_count == 1 (holding position), it calculates:
1. diff_rate: absolute difference between the two markets' mark rates at position opening
2. annualized_return: time-weighted composite annualized return

Time-Weighted Formula:
    composite_annualized = Σ(rate_i × duration_i) / Σ(duration_i)
"""

import pandas as pd
import numpy as np
from pathlib import Path


def load_account_data(csv_path: str) -> pd.DataFrame:
    """Load and preprocess the account CSV file."""
    df = pd.read_csv(csv_path, header=[0, 1])
    
    # Flatten column names
    df.columns = [f"{col[0]}_{col[1]}" if col[1] else col[0] for col in df.columns]
    
    # Rename the timestamp column
    df = df.rename(columns={"l1_l2": "timestamp"})
    df["timestamp"] = pd.to_datetime(df["timestamp"])
    
    return df


def identify_position_changes(df: pd.DataFrame) -> pd.DataFrame:
    """
    Identify position change points.
    position_count == 1 means holding position (open)
    position_count == 0 means no position (closed)
    """
    # Get position counts from both markets
    binance_position = df["binance_feb27_position_count"]
    hyperliquid_position = df["hyperliquid_feb27_position_count"]
    
    # Use max of both to determine overall position status
    df["has_position"] = (binance_position == 1) | (hyperliquid_position == 1)
    
    # Find position open/close transitions
    df["position_change"] = df["has_position"].ne(df["has_position"].shift()).astype(int)
    df["position_group"] = df["position_change"].cumsum()
    
    return df


def calculate_diff_rate(df: pd.DataFrame) -> pd.DataFrame:
    """
    Calculate diff_rate for each position period.
    diff_rate = |binance_mark_rate - hyperliquid_mark_rate| at the first row of each position period.
    """
    # Get mark rates from both markets
    binance_rate = df["binance_feb27_current_mark_rate"]
    hyperliquid_rate = df["hyperliquid_feb27_current_mark_rate"]
    
    # Calculate the absolute rate difference
    df["rate_diff"] = abs(binance_rate - hyperliquid_rate)
    
    # Initialize diff_rate column (will be filled for position periods)
    df["diff_rate"] = np.nan
    
    # For each position group where we have a position, calculate diff_rate
    for group_id in df[df["has_position"]]["position_group"].unique():
        group_mask = df["position_group"] == group_id
        first_idx = df[group_mask].index[0]
        
        # Set diff_rate for the entire position group to the first row's rate_diff
        df.loc[group_mask, "diff_rate"] = df.loc[first_idx, "rate_diff"]
    
    return df


def calculate_time_weighted_annualized_return(df: pd.DataFrame) -> pd.DataFrame:
    """
    Calculate time-weighted composite annualized return.
    
    Formula: composite_annualized = Σ(rate_i × duration_i) / Σ(duration_i)
    
    This method weights each position period's return by its duration.
    """
    # Calculate duration (in minutes) for each position group
    position_groups = df[df["has_position"]].groupby("position_group")
    
    # Calculate total duration and weighted return for each position group
    group_stats = []
    for group_id, group_df in position_groups:
        duration = len(group_df)  # Each row represents 1 minute
        diff_rate = group_df["diff_rate"].iloc[0]  # First row's rate
        group_stats.append({
            "position_group": group_id,
            "duration_minutes": duration,
            "diff_rate": diff_rate,
            "weighted_return": diff_rate * duration
        })
    
    stats_df = pd.DataFrame(group_stats)
    
    # Calculate time-weighted composite annualized return
    total_duration = stats_df["duration_minutes"].sum()
    total_weighted_return = stats_df["weighted_return"].sum()
    composite_annualized = total_weighted_return / total_duration
    
    print("\n" + "=" * 60)
    print("TIME-WEIGHTED BREAKDOWN BY POSITION PERIOD")
    print("=" * 60)
    print(f"{'Period':<10} {'Duration(min)':<15} {'diff_rate':<15} {'weighted':<15}")
    print("-" * 60)
    for _, row in stats_df.iterrows():
        print(f"{int(row['position_group']):<10} {int(row['duration_minutes']):<15} {row['diff_rate']*100:.2f}%{'':<8} {row['weighted_return']*100:.2f}%")
    print("-" * 60)
    print(f"{'TOTAL':<10} {int(total_duration):<15} {'':<15} {composite_annualized*100:.2f}%")
    
    # Store the composite annualized return in the dataframe
    # We'll add a summary row to show this is the time-weighted result
    df["annualized_return"] = df["diff_rate"]  # Keep per-row for reference
    
    # Create a new column for the time-weighted composite
    df["time_weighted_annualized_return"] = composite_annualized
    
    return df, composite_annualized, stats_df


def main():
    # File paths
    input_path = Path("result/boros.account.csv")
    output_path = Path("result/boros.account.with_return.csv")
    
    print("Loading account data...")
    df = load_account_data(input_path)
    print(f"Loaded {len(df)} rows")
    
    print("\nIdentifying position changes...")
    df = identify_position_changes(df)
    
    print("\nCalculating diff_rate for position periods...")
    df = calculate_diff_rate(df)
    
    print("\nCalculating time-weighted annualized return...")
    df, composite_return, stats_df = calculate_time_weighted_annualized_return(df)
    
    # Display summary statistics
    print("\n" + "=" * 60)
    print("SUMMARY STATISTICS")
    print("=" * 60)
    
    # Filter to rows with positions
    position_rows = df[df["has_position"] == True]
    print(f"Total rows with positions: {len(position_rows)}")
    print(f"Number of position periods: {stats_df.shape[0]}")
    print(f"Total duration: {stats_df['duration_minutes'].sum()} minutes ({stats_df['duration_minutes'].sum()/60:.1f} hours)")
    
    # Statistics for diff_rate (per-position period)
    print(f"\nDiff Rate Statistics (per position period):")
    print(f"  Mean (simple):   {stats_df['diff_rate'].mean()*100:.2f}%")
    print(f"  Median:          {stats_df['diff_rate'].median()*100:.2f}%")
    print(f"  Min:             {stats_df['diff_rate'].min()*100:.2f}%")
    print(f"  Max:             {stats_df['diff_rate'].max()*100:.2f}%")
    
    # Time-weighted composite return
    print(f"\n{'='*60}")
    print(f"TIME-WEIGHTED COMPOSITE ANNUALIZED RETURN: {composite_return*100:.2f}%")
    print(f"{'='*60}")
    
    # Save results
    print(f"\nSaving results to {output_path}...")
    df.to_csv(output_path, index=False)
    print("Done!")
    
    # Show sample output
    print("\n" + "=" * 60)
    print("SAMPLE OUTPUT (first 10 rows with positions)")
    print("=" * 60)
    sample_cols = ["timestamp", "binance_feb27_position_count", "hyperliquid_feb27_position_count",
                   "binance_feb27_current_mark_rate", "hyperliquid_feb27_current_mark_rate",
                   "diff_rate", "annualized_return"]
    print(position_rows[sample_cols].head(10).to_string())


if __name__ == "__main__":
    main()
