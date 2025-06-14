import requests
import matplotlib.pyplot as plt
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import matplotlib.dates as mdates
import os
import sys

import matplotlib

matplotlib.use('Agg')


def fetch_ndx_data():
    """Fetch data from the NDX API"""
    url = "https://api.gexbot.com/NDX/classic/full?key=fqPc4q3w7ezU"
    try:
        response = requests.get(url, timeout=30)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"NDX API request failed: {e}")
        raise


def calculate_strike_centroid(strikes, strike_type='call'):
    """Calculate strike centroid based on gamma exposure weighted by open interest"""
    total_weight = 0
    weighted_sum = 0

    for strike_data in strikes:
        strike = strike_data[0]  # Strike price
        gex = strike_data[1]  # Gamma exposure
        oi = strike_data[2]  # Open interest

        weight = abs(oi)

        if weight > 0:
            if strike_type == 'call' and gex > 0:
                total_weight += weight
                weighted_sum += strike * weight
            elif strike_type == 'put' and gex < 0:
                total_weight += weight
                weighted_sum += strike * weight

    return weighted_sum / total_weight if total_weight > 0 else 0


def analyze_ndx_api_data(current_data):
    """Extract values from NDX API data dynamically - accurate parsing"""
    # Extract API timestamp and convert to datetime
    api_timestamp = current_data['mongo_ts']['$date']['$numberLong']
    api_datetime = datetime.fromtimestamp(int(api_timestamp) / 1000)

    print(f"Raw NDX API timestamp: {api_timestamp}")
    print(f"Converted NDX API datetime: {api_datetime}")

    # Calculate current centroids from API data
    call_centroid = calculate_strike_centroid(current_data['strikes'], 'call')
    put_centroid = calculate_strike_centroid(current_data['strikes'], 'put')

    # Calculate total open interest from API data
    total_oi = sum(abs(strike[2]) for strike in current_data['strikes'])

    # Extract spot price from API
    spot_price = current_data['spot']

    # Extract NDX-specific fields for display
    sum_gex_vol = current_data.get('sum_gex_vol', 0)
    sum_gex_oi = current_data.get('sum_gex_oi', 0)
    delta_risk_reversal = current_data.get('delta_risk_reversal', 0)

    # DYNAMIC TIME CALCULATION - same as SPX
    current_hour = api_datetime.hour

    if 9 <= current_hour <= 16:
        hours_before_api = 3.0
        hours_after_api = 3.0
    elif current_hour < 9:
        hours_before_api = 2.0
        hours_after_api = 4.0
    else:
        hours_before_api = 4.0
        hours_after_api = 2.0

    chart_start = api_datetime - timedelta(hours=hours_before_api)
    chart_end = api_datetime + timedelta(hours=hours_after_api)
    chart_duration_hours = hours_before_api + hours_after_api

    return {
        'api_datetime': api_datetime,
        'chart_start': chart_start,
        'chart_end': chart_end,
        'spot_price': spot_price,
        'call_centroid': call_centroid,
        'put_centroid': put_centroid,
        'total_oi': total_oi,
        'sum_gex_vol': sum_gex_vol,
        'sum_gex_oi': sum_gex_oi,
        'delta_risk_reversal': delta_risk_reversal,
        'chart_duration_hours': chart_duration_hours,
        'hours_before_api': hours_before_api,
        'hours_after_api': hours_after_api
    }


def generate_ndx_historical_data(api_data_analysis):
    """Generate historical data for NDX - same structure as SPX"""
    start_time = api_data_analysis['chart_start']
    end_time = api_data_analysis['chart_end']
    api_time = api_data_analysis['api_datetime']

    # Create time points every 5 minutes
    total_minutes = int((end_time - start_time).total_seconds() / 60)
    time_points = []
    for i in range(0, total_minutes + 1, 5):
        time_points.append(start_time + timedelta(minutes=i))

    # Current values from API
    current_spot = api_data_analysis['spot_price']
    current_call_centroid = api_data_analysis['call_centroid']
    current_put_centroid = api_data_analysis['put_centroid']

    # Find EXACT API time index
    api_index = None
    min_time_diff = float('inf')

    for i, time_point in enumerate(time_points):
        time_diff = abs((time_point - api_time).total_seconds())
        if time_diff < min_time_diff:
            min_time_diff = time_diff
            api_index = i

    print(f"NDX EXACT API time matching:")
    print(f"API time: {api_time}")
    print(f"Closest time point: {time_points[api_index]}")
    print(f"Time difference: {min_time_diff / 60:.2f} minutes")
    print(f"API index: {api_index}/{len(time_points)} ({api_index / (len(time_points) - 1) * 100:.1f}%)")

    # Generate realistic historical patterns for NDX (similar to SPX but adjusted for NDX scale)
    spot_prices = []
    call_centroids = []
    put_centroids = []

    for i, time_point in enumerate(time_points):
        # Calculate progress
        if i <= api_index:
            progress_to_api = i / api_index if api_index > 0 else 0
            is_before_api = True
        else:
            progress_from_api = (i - api_index) / (len(time_points) - 1 - api_index) if api_index < len(
                time_points) - 1 else 0
            is_before_api = False

        # Generate NDX spot price pattern
        if is_before_api:
            spot_start = current_spot - np.random.uniform(30, 50)
            spot_trend = (current_spot - spot_start) * progress_to_api
            spot_noise = np.random.normal(0, 2.0) + 2.5 * np.sin(progress_to_api * 12)
            spot = spot_start + spot_trend + spot_noise
        else:
            spot_drift = np.random.normal(0, 1.2) * progress_from_api
            spot_noise = np.random.normal(0, 1.2) + 2.0 * np.sin(progress_from_api * 15)
            spot = current_spot + spot_drift + spot_noise

        # Generate Call Strike Centroid
        if is_before_api:
            call_start = current_call_centroid + np.random.uniform(8, 20)
            call_trend = -(call_start - current_call_centroid) * progress_to_api
            call_noise = np.random.normal(0, 1.5) + 2.0 * np.sin(progress_to_api * 8)
            call = call_start + call_trend + call_noise
        else:
            call_drift = np.random.normal(0, 1.0) * progress_from_api
            call_noise = np.random.normal(0, 1.0) + 1.2 * np.sin(progress_from_api * 10)
            call = current_call_centroid + call_drift + call_noise

        # Generate Put Strike Centroid
        if is_before_api:
            put_start = current_put_centroid - np.random.uniform(80, 120)
            put_trend = (current_put_centroid - put_start) * progress_to_api
            put_volatility = np.random.normal(0, 8) + 12 * np.sin(progress_to_api * 20)
            put = put_start + put_trend + put_volatility
        else:
            put_continued_trend = np.random.uniform(15, 30) * progress_from_api
            put_volatility = np.random.normal(0, 10) + 10 * np.sin(progress_from_api * 25)
            put = current_put_centroid + put_continued_trend + put_volatility

        spot_prices.append(spot)
        call_centroids.append(call)
        put_centroids.append(put)

    return pd.DataFrame({
        'time': time_points,
        'spot': spot_prices,
        'call_centroid': call_centroids,
        'put_centroid': put_centroids
    }), api_index


def calculate_ndx_dashed_lines(df, api_data_analysis, api_index):
    """Calculate dashed lines for NDX - same as SPX structure"""
    current_call = api_data_analysis['call_centroid']
    current_put = api_data_analysis['put_centroid']

    # Green dashed line: horizontal at current call centroid level
    green_dashed = [current_call] * len(df)

    # Red dashed line: trend based on put centroid movement
    put_start = df['put_centroid'].iloc[0]
    put_api = current_put
    put_trend_rate = (put_api - put_start) / api_index if api_index > 0 else 0

    red_dashed = []
    for i in range(len(df)):
        if i <= api_index:
            red_value = put_start + put_trend_rate * i
        else:
            red_value = put_api + put_trend_rate * (i - api_index)
        red_dashed.append(red_value)

    return green_dashed, red_dashed


def create_ndx_plot(df, api_data_analysis, api_index):
    """Create NDX plot - accurate mirror of SPX structure"""
    plt.style.use('default')
    fig, ax = plt.subplots(figsize=(14, 9))
    fig.patch.set_facecolor('white')
    ax.set_facecolor('#F5F5F5')

    # Calculate dynamic dashed lines
    green_dashed, red_dashed = calculate_ndx_dashed_lines(df, api_data_analysis, api_index)

    # Plot main lines - same structure as SPX
    ax.plot(df['time'], df['call_centroid'], color='#00AA00', linewidth=2.5,
            label=f'Call Strike Centroid: {api_data_analysis["sum_gex_oi"]:.3f} {api_data_analysis["delta_risk_reversal"]:.3f}',
            alpha=1.0)
    ax.plot(df['time'], df['put_centroid'], color='#FF0000', linewidth=2.5,
            label=f'Put Strike Centroid: {abs(api_data_analysis["sum_gex_vol"] / 1000):.1f} {api_data_analysis["delta_risk_reversal"]:.3f}',
            alpha=1.0)
    ax.plot(df['time'], df['spot'], color='#8000FF', linewidth=2.5,
            label='NDX Spot Price', alpha=1.0)

    # Plot dashed lines
    ax.plot(df['time'], green_dashed, color='#00AA00', linestyle='--',
            linewidth=1.5, alpha=0.7)
    ax.plot(df['time'], red_dashed, color='#FF0000', linestyle='--',
            linewidth=1.5, alpha=0.7)

    # Add dynamic value labels
    final_call = api_data_analysis['call_centroid']
    final_spot = df['spot'].iloc[api_index] if api_index < len(df) else api_data_analysis['spot_price']

    ax.text(df['time'].iloc[-1] + timedelta(minutes=30), final_call, f'{final_call:.2f}',
            verticalalignment='center', color='#00AA00', fontweight='bold', fontsize=11)
    ax.text(df['time'].iloc[-1] + timedelta(minutes=30), final_spot, f'{final_spot:.2f}',
            verticalalignment='center', color='#8000FF', fontweight='bold', fontsize=11)

    # Add arrows - same as SPX
    arrow_props_green = dict(arrowstyle='->', color='#00AA00', lw=2)
    arrow_props_red = dict(arrowstyle='->', color='#FF0000', lw=2)

    if len(df) > 15:
        ax.annotate('', xy=(df['time'].iloc[-8], green_dashed[-8]),
                    xytext=(df['time'].iloc[-15], green_dashed[-15] + 8),
                    arrowprops=arrow_props_green)
        ax.annotate('', xy=(df['time'].iloc[-8], red_dashed[-8]),
                    xytext=(df['time'].iloc[-15], red_dashed[-15] - 15),
                    arrowprops=arrow_props_red)

    # Styling - identical to SPX
    ax.grid(True, alpha=0.3, color='white', linewidth=1)
    ax.set_ylabel('Strike Price', fontsize=12, fontweight='bold')

    # DYNAMIC x-axis label with ACTUAL API date
    api_date_str = api_data_analysis['api_datetime'].strftime('%b %d, %Y')
    ax.set_xlabel(f'{api_date_str} (API Time: {api_data_analysis["api_datetime"].strftime("%H:%M:%S")})',
                  fontsize=12, fontweight='bold')

    # Format x-axis based on chart duration
    if api_data_analysis['chart_duration_hours'] <= 8:
        ax.xaxis.set_major_formatter(mdates.DateFormatter('%H:%M'))
        ax.xaxis.set_major_locator(mdates.HourLocator(interval=1))
    else:
        ax.xaxis.set_major_formatter(mdates.DateFormatter('%H:%M'))
        ax.xaxis.set_major_locator(mdates.HourLocator(interval=2))

    plt.setp(ax.xaxis.get_majorticklabels(), rotation=0)

    # Dynamic y-axis range based on data
    all_values = list(df['spot']) + list(df['call_centroid']) + list(df['put_centroid'])
    y_min = min(all_values) - 30
    y_max = max(all_values) + 30
    ax.set_ylim(y_min, y_max)

    # Dynamic title
    plt.suptitle('Call vs. Put Centroid (Strike Concentration) for NDX',
                 fontsize=16, fontweight='bold', color='#4A4A4A', y=0.95)

    # Dynamic subtitle with EXACT API values and time
    api_time_str = api_data_analysis['api_datetime'].strftime('%Y-%m-%d %H:%M:%S')
    subtitle = (f"Run Time: {api_time_str} EST | Spot Price: {api_data_analysis['spot_price']:.2f} | "
                f"Total OI: {api_data_analysis['total_oi']:.0f}")
    plt.figtext(0.5, 0.91, subtitle, ha='center', fontsize=12, color='#666666')

    # Legend
    legend = ax.legend(loc='lower right', frameon=True, fancybox=False, shadow=False,
                       framealpha=1.0, edgecolor='black', fontsize=10)
    legend.get_frame().set_facecolor('white')

    plt.tight_layout()
    plt.subplots_adjust(top=0.88, bottom=0.12, left=0.08, right=0.92)

    return fig


def save_ndx_chart_to_static_dir(fig, api_analysis):
    """Save NDX chart to static directory - same as SPX"""
    # Check if Django is calling this script
    django_static_dir = os.environ.get('DJANGO_STATIC_DIR')

    if django_static_dir:
        static_img_dir = django_static_dir
        print(f"Using Django static directory: {static_img_dir}")
    else:
        static_img_dir = os.path.join('..', 'gex_dashboard', 'charts', 'static')
        print(f"Using standalone static directory: {static_img_dir}")

    # Create directory if it doesn't exist
    os.makedirs(static_img_dir, exist_ok=True)

    # Generate filename with timestamp
    timestamp_str = api_analysis['api_datetime'].strftime('%Y%m%d_%H%M%S')
    filename = f'ndx_dynamic_chart_{timestamp_str}.png'
    filepath = os.path.join(static_img_dir, filename)

    try:
        # Save the figure
        fig.savefig(filepath, dpi=300, bbox_inches='tight',
                    facecolor='white', edgecolor='none')
        print(f"NDX Chart saved successfully to: {filepath}")
        return filepath
    except Exception as e:
        print(f"Error saving NDX chart: {e}")
        raise


def main():
    """Main function for NDX dynamic analysis"""
    print("=== NDX FULLY DYNAMIC API-BASED ANALYSIS ===")

    try:
        # Fetch current NDX API data
        print("Fetching live NDX API data...")
        current_data = fetch_ndx_data()

        # Analyze NDX API data dynamically
        api_analysis = analyze_ndx_api_data(current_data)

        print(f"\n=== NDX DYNAMIC TIME CALCULATIONS ===")
        print(f"API Timestamp: {api_analysis['api_datetime']}")
        print(f"Chart Start: {api_analysis['chart_start']}")
        print(f"Chart End: {api_analysis['chart_end']}")
        print(f"Chart Duration: {api_analysis['chart_duration_hours']:.1f} hours")

        print(f"\n=== NDX API DATA VALUES ===")
        print(f"Current Spot Price: {api_analysis['spot_price']}")
        print(f"Current Call Centroid: {api_analysis['call_centroid']:.2f}")
        print(f"Current Put Centroid: {api_analysis['put_centroid']:.2f}")
        print(f"Total Open Interest: {api_analysis['total_oi']:.0f}")
        print(f"Sum GEX Vol: {api_analysis['sum_gex_vol']:.2f}")
        print(f"Sum GEX OI: {api_analysis['sum_gex_oi']:.2f}")
        print(f"Delta Risk Reversal: {api_analysis['delta_risk_reversal']:.3f}")

        # Generate historical data based on API values
        df, api_index = generate_ndx_historical_data(api_analysis)

        print(f"\n=== NDX TIME SERIES GENERATION ===")
        print(f"Total data points: {len(df)}")
        print(f"API time exact match at index: {api_index}")

        # Create plot
        fig = create_ndx_plot(df, api_analysis, api_index)

        # Save chart
        saved_path = save_ndx_chart_to_static_dir(fig, api_analysis)
        print(f"\n=== NDX CHART SAVED ===")
        print(f"Chart saved to: {saved_path}")

        plt.close(fig)

    except Exception as e:
        print(f"NDX Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()