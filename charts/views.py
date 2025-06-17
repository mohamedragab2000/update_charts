from django.shortcuts import render
from django.http import JsonResponse, HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.conf import settings
import os
import io
import base64
import matplotlib

matplotlib.use('Agg')  # Use non-GUI backend
import matplotlib.pyplot as plt
from datetime import datetime
import json
import traceback
import logging

# Set up logging
logger = logging.getLogger(__name__)

# Import your analysis functions
from .spx import (
    fetch_spx_data,
    analyze_api_data,
    generate_dynamic_historical_data,
    create_dynamic_plot,
    calculate_dynamic_dashed_lines
)

# Import NDX analysis functions - FIXED: Use the same functions from the first file
from .ndx import (
    fetch_ndx_data,
    analyze_api_data as analyze_ndx_api_data,  # Alias to avoid naming conflict
    generate_dynamic_historical_data as generate_ndx_dynamic_historical_data,
    create_dynamic_plot as create_ndx_dynamic_plot,
    calculate_dynamic_dashed_lines as calculate_ndx_dynamic_dashed_lines
)


def spx_dashboard(request):
    """Main dashboard view for SPX and NDX options flow analysis"""
    context = {
        'title': 'SPX vs NDX Options Flow Analysis',
        'current_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
    }
    return render(request, 'charts/dashboard.html', context)


def get_combined_data(request):
    """API endpoint to fetch both SPX and NDX data and return JSON"""
    try:
        # Fetch current API data for both indices
        spx_data = fetch_spx_data()
        ndx_data = fetch_ndx_data()

        # Analyze the API data
        spx_analysis = analyze_api_data(spx_data)
        ndx_analysis = analyze_ndx_api_data(ndx_data)

        # Calculate total GEX for both
        spx_total_gex = sum(abs(strike[1]) for strike in spx_data['strikes'])
        ndx_total_gex = sum(abs(strike[1]) for strike in ndx_data['strikes'])

        # Convert datetime objects to strings for JSON serialization
        response_data = {
            'success': True,
            'spx': {
                'api_time': spx_analysis['api_datetime'].strftime('%Y-%m-%d %H:%M:%S'),
                'spot_price': spx_analysis['spot_price'],
                'call_centroid': spx_analysis['call_centroid'],
                'put_centroid': spx_analysis['put_centroid'],
                'total_oi': spx_analysis['total_oi'],
                'total_gex': spx_total_gex,
                'chart_start': spx_analysis['chart_start'].strftime('%Y-%m-%d %H:%M:%S'),
                'chart_end': spx_analysis['chart_end'].strftime('%Y-%m-%d %H:%M:%S'),
            },
            'ndx': {
                'api_time': ndx_analysis['api_datetime'].strftime('%Y-%m-%d %H:%M:%S'),
                'spot_price': ndx_analysis['spot_price'],
                'call_centroid': ndx_analysis['call_centroid'],
                'put_centroid': ndx_analysis['put_centroid'],
                'total_oi': ndx_analysis['total_oi'],
                'total_gex': ndx_total_gex,
                'chart_start': ndx_analysis['chart_start'].strftime('%Y-%m-%d %H:%M:%S'),
                'chart_end': ndx_analysis['chart_end'].strftime('%Y-%m-%d %H:%M:%S'),
            }
        }

        return JsonResponse(response_data)

    except Exception as e:
        logger.error(f"Error in get_combined_data: {str(e)}")
        logger.error(traceback.format_exc())
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


def get_spx_data(request):
    """API endpoint to fetch current SPX data and return JSON (backward compatibility)"""
    try:
        # Fetch current API data
        current_data = fetch_spx_data()

        # Analyze the API data
        api_analysis = analyze_api_data(current_data)

        # Calculate total GEX from strikes data
        total_gex = sum(abs(strike[1]) for strike in current_data['strikes'])

        # Convert datetime objects to strings for JSON serialization
        response_data = {
            'success': True,
            'api_time': api_analysis['api_datetime'].strftime('%Y-%m-%d %H:%M:%S'),
            'spot_price': api_analysis['spot_price'],
            'call_centroid': api_analysis['call_centroid'],
            'put_centroid': api_analysis['put_centroid'],
            'total_oi': api_analysis['total_oi'],
            'total_gex': total_gex,
            'chart_start': api_analysis['chart_start'].strftime('%Y-%m-%d %H:%M:%S'),
            'chart_end': api_analysis['chart_end'].strftime('%Y-%m-%d %H:%M:%S'),
        }

        return JsonResponse(response_data)

    except Exception as e:
        logger.error(f"Error in get_spx_data: {str(e)}")
        logger.error(traceback.format_exc())
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


def get_ndx_data(request):
    """API endpoint to fetch current NDX data and return JSON"""
    try:
        # Fetch current API data
        current_data = fetch_ndx_data()

        # Analyze the API data
        api_analysis = analyze_ndx_api_data(current_data)

        # Calculate total GEX from strikes data
        total_gex = sum(abs(strike[1]) for strike in current_data['strikes'])

        # Convert datetime objects to strings for JSON serialization
        response_data = {
            'success': True,
            'api_time': api_analysis['api_datetime'].strftime('%Y-%m-%d %H:%M:%S'),
            'spot_price': api_analysis['spot_price'],
            'call_centroid': api_analysis['call_centroid'],
            'put_centroid': api_analysis['put_centroid'],
            'total_oi': api_analysis['total_oi'],
            'total_gex': total_gex,
            'chart_start': api_analysis['chart_start'].strftime('%Y-%m-%d %H:%M:%S'),
            'chart_end': api_analysis['chart_end'].strftime('%Y-%m-%d %H:%M:%S'),
        }

        return JsonResponse(response_data)

    except Exception as e:
        logger.error(f"Error in get_ndx_data: {str(e)}")
        logger.error(traceback.format_exc())
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


@csrf_exempt
@require_http_methods(["GET", "POST"])
def generate_combined_plot(request):
    """Generate and return combined SPX and NDX options flow plot as base64 image"""
    try:
        logger.info("Starting combined plot generation...")

        # Fetch and analyze current data for both indices
        spx_data = fetch_spx_data()
        ndx_data = fetch_ndx_data()
        logger.info("Data fetched successfully for both SPX and NDX")

        spx_analysis = analyze_api_data(spx_data)
        ndx_analysis = analyze_ndx_api_data(ndx_data)
        logger.info("Data analyzed successfully for both indices")

        # Generate historical data for both
        spx_df, spx_api_index = generate_dynamic_historical_data(spx_analysis)
        ndx_df, ndx_api_index = generate_ndx_dynamic_historical_data(ndx_analysis)
        logger.info(f"Historical data generated - SPX: {len(spx_df)} points, NDX: {len(ndx_df)} points")

        # Create combined plot
        fig = create_combined_plot(spx_df, spx_analysis, spx_api_index,
                                   ndx_df, ndx_analysis, ndx_api_index)
        logger.info("Combined plot created successfully")

        # Convert plot to base64 string
        buffer = io.BytesIO()
        try:
            fig.savefig(buffer, format='png', dpi=150, bbox_inches='tight',
                        facecolor='white', edgecolor='none',
                        pad_inches=0.2)
            buffer.seek(0)
            image_bytes = buffer.getvalue()
            image_base64 = base64.b64encode(image_bytes).decode('utf-8')
            logger.info(f"Image converted to base64, size: {len(image_base64)} characters")
        finally:
            buffer.close()
            plt.close(fig)

        # Calculate total GEX for both
        spx_total_gex = sum(abs(strike[1]) for strike in spx_data['strikes'])
        ndx_total_gex = sum(abs(strike[1]) for strike in ndx_data['strikes'])

        response_data = {
            'success': True,
            'image': image_base64,
            'spx': {
                'api_time': spx_analysis['api_datetime'].strftime('%Y-%m-%d %H:%M:%S'),
                'spot_price': float(spx_analysis['spot_price']),
                'call_centroid': float(spx_analysis['call_centroid']),
                'put_centroid': float(spx_analysis['put_centroid']),
                'total_oi': float(spx_analysis['total_oi']),
                'total_gex': float(spx_total_gex / 1000000),
            },
            'ndx': {
                'api_time': ndx_analysis['api_datetime'].strftime('%Y-%m-%d %H:%M:%S'),
                'spot_price': float(ndx_analysis['spot_price']),
                'call_centroid': float(ndx_analysis['call_centroid']),
                'put_centroid': float(ndx_analysis['put_centroid']),
                'total_oi': float(ndx_analysis['total_oi']),
                'total_gex': float(ndx_total_gex / 1000000),
            }
        }

        logger.info("Combined plot generation completed successfully")
        return JsonResponse(response_data)

    except Exception as e:
        logger.error(f"Error in generate_combined_plot: {str(e)}")
        logger.error(traceback.format_exc())
        return JsonResponse({
            'success': False,
            'error': str(e),
            'traceback': traceback.format_exc() if settings.DEBUG else None
        }, status=500)


@csrf_exempt
@require_http_methods(["GET", "POST"])
def generate_spx_plot(request):
    """Generate and return SPX options flow plot as base64 image (backward compatibility)"""
    try:
        logger.info("Starting SPX plot generation...")

        # Fetch and analyze current data
        current_data = fetch_spx_data()
        logger.info("SPX data fetched successfully")

        api_analysis = analyze_api_data(current_data)
        logger.info("SPX data analyzed successfully")

        # Generate historical data
        df, api_index = generate_dynamic_historical_data(api_analysis)
        logger.info(f"SPX historical data generated: {len(df)} points, api_index: {api_index}")

        # Create the plot
        fig = create_dynamic_plot(df, api_analysis, api_index)
        logger.info("SPX plot created successfully")

        # Convert plot to base64 string
        buffer = io.BytesIO()
        try:
            fig.savefig(buffer, format='png', dpi=150, bbox_inches='tight',
                        facecolor='white', edgecolor='none',
                        pad_inches=0.2)
            buffer.seek(0)
            image_bytes = buffer.getvalue()
            image_base64 = base64.b64encode(image_bytes).decode('utf-8')
            logger.info(f"SPX image converted to base64, size: {len(image_base64)} characters")
        finally:
            buffer.close()
            plt.close(fig)

        # Calculate total GEX from strikes data
        total_gex = sum(abs(strike[1]) for strike in current_data['strikes'])

        response_data = {
            'success': True,
            'image': image_base64,
            'api_time': api_analysis['api_datetime'].strftime('%Y-%m-%d %H:%M:%S'),
            'spot_price': float(api_analysis['spot_price']),
            'call_centroid': float(api_analysis['call_centroid']),
            'put_centroid': float(api_analysis['put_centroid']),
            'total_oi': float(api_analysis['total_oi']),
            'total_gex': float(total_gex / 1000000),
        }

        logger.info("SPX plot generation completed successfully")
        return JsonResponse(response_data)

    except Exception as e:
        logger.error(f"Error in generate_spx_plot: {str(e)}")
        logger.error(traceback.format_exc())
        return JsonResponse({
            'success': False,
            'error': str(e),
            'traceback': traceback.format_exc() if settings.DEBUG else None
        }, status=500)


@csrf_exempt
@require_http_methods(["GET", "POST"])
def generate_ndx_plot(request):
    """Generate and return NDX options flow plot as base64 image"""
    try:
        logger.info("Starting NDX plot generation...")

        # Fetch and analyze current data
        current_data = fetch_ndx_data()
        logger.info("NDX data fetched successfully")

        api_analysis = analyze_ndx_api_data(current_data)
        logger.info("NDX data analyzed successfully")

        # Generate historical data
        df, api_index = generate_ndx_dynamic_historical_data(api_analysis)
        logger.info(f"NDX historical data generated: {len(df)} points, api_index: {api_index}")

        # Create the plot
        fig = create_ndx_dynamic_plot(df, api_analysis, api_index)
        logger.info("NDX plot created successfully")

        # Convert plot to base64 string
        buffer = io.BytesIO()
        try:
            fig.savefig(buffer, format='png', dpi=150, bbox_inches='tight',
                        facecolor='white', edgecolor='none',
                        pad_inches=0.2)
            buffer.seek(0)
            image_bytes = buffer.getvalue()
            image_base64 = base64.b64encode(image_bytes).decode('utf-8')
            logger.info(f"NDX image converted to base64, size: {len(image_base64)} characters")
        finally:
            buffer.close()
            plt.close(fig)

        # Calculate total GEX from strikes data
        total_gex = sum(abs(strike[1]) for strike in current_data['strikes'])

        response_data = {
            'success': True,
            'image': image_base64,
            'api_time': api_analysis['api_datetime'].strftime('%Y-%m-%d %H:%M:%S'),
            'spot_price': float(api_analysis['spot_price']),
            'call_centroid': float(api_analysis['call_centroid']),
            'put_centroid': float(api_analysis['put_centroid']),
            'total_oi': float(api_analysis['total_oi']),
            'total_gex': float(total_gex / 1000000),
        }

        logger.info("NDX plot generation completed successfully")
        return JsonResponse(response_data)

    except Exception as e:
        logger.error(f"Error in generate_ndx_plot: {str(e)}")
        logger.error(traceback.format_exc())
        return JsonResponse({
            'success': False,
            'error': str(e),
            'traceback': traceback.format_exc() if settings.DEBUG else None
        }, status=500)


def create_combined_plot(spx_df, spx_analysis, spx_api_index, ndx_df, ndx_analysis, ndx_api_index):
    """Create a combined plot showing both SPX and NDX data"""
    plt.style.use('default')
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(16, 12))
    fig.patch.set_facecolor('white')

    # SPX Plot (top)
    ax1.set_facecolor('#F5F5F5')
    ax1.plot(spx_df['time'], spx_df['call_centroid'], color='#00AA00', linewidth=2.5,
             label='SPX Call Strike Centroid', alpha=1.0)
    ax1.plot(spx_df['time'], spx_df['put_centroid'], color='#FF0000', linewidth=2.5,
             label='SPX Put Strike Centroid', alpha=1.0)
    ax1.plot(spx_df['time'], spx_df['spot'], color='#0066CC', linewidth=2.5,
             label='SPX Spot Price', alpha=1.0)

    # Add vertical line at API time for SPX
    api_time_spx = spx_analysis['api_datetime']
    ax1.axvline(x=api_time_spx, color='red', linestyle='--', alpha=0.7,
                label=f'Current Time: {api_time_spx.strftime("%H:%M")}')

    ax1.set_title(f'SPX Options Flow Analysis - {spx_analysis["api_datetime"].strftime("%Y-%m-%d %H:%M:%S")}',
                  fontsize=14, fontweight='bold', color='#4A4A4A')
    ax1.set_ylabel('SPX Price', fontsize=12, fontweight='bold')
    ax1.grid(True, alpha=0.3, color='white', linewidth=1)
    ax1.legend(loc='upper left', frameon=True, fancybox=False, shadow=False,
               framealpha=1.0, edgecolor='black', fontsize=10)

    # NDX Plot (bottom)
    ax2.set_facecolor('#F5F5F5')
    ax2.plot(ndx_df['time'], ndx_df['call_centroid'], color='#00AA00', linewidth=2.5,
             label='NDX Call Strike Centroid', alpha=1.0)
    ax2.plot(ndx_df['time'], ndx_df['put_centroid'], color='#FF0000', linewidth=2.5,
             label='NDX Put Strike Centroid', alpha=1.0)
    ax2.plot(ndx_df['time'], ndx_df['spot'], color='#8000FF', linewidth=2.5,
             label='NDX Spot Price', alpha=1.0)

    # Add vertical line at API time for NDX
    api_time_ndx = ndx_analysis['api_datetime']
    ax2.axvline(x=api_time_ndx, color='red', linestyle='--', alpha=0.7,
                label=f'Current Time: {api_time_ndx.strftime("%H:%M")}')

    ax2.set_title(f'NDX Options Flow Analysis - {ndx_analysis["api_datetime"].strftime("%Y-%m-%d %H:%M:%S")}',
                  fontsize=14, fontweight='bold', color='#4A4A4A')
    ax2.set_xlabel('Time', fontsize=12, fontweight='bold')
    ax2.set_ylabel('NDX Price', fontsize=12, fontweight='bold')
    ax2.grid(True, alpha=0.3, color='white', linewidth=1)
    ax2.legend(loc='upper left', frameon=True, fancybox=False, shadow=False,
               framealpha=1.0, edgecolor='black', fontsize=10)

    # Format x-axis for both subplots
    import matplotlib.dates as mdates
    for ax in [ax1, ax2]:
        ax.xaxis.set_major_formatter(mdates.DateFormatter('%H:%M'))
        ax.xaxis.set_major_locator(mdates.HourLocator(interval=1))
        plt.setp(ax.xaxis.get_majorticklabels(), rotation=0)

    plt.tight_layout()
    plt.subplots_adjust(top=0.95, bottom=0.08, left=0.08, right=0.95, hspace=0.3)

    return fig


def debug_api(request):
    """Debug endpoint to inspect both SPX and NDX API responses"""
    try:
        spx_data = fetch_spx_data()
        ndx_data = fetch_ndx_data()

        # Create debug information
        debug_data = {
            'spx': {
                'api_keys': list(spx_data.keys()),
                'spot_price': spx_data.get('spot'),
                'mongo_ts': spx_data.get('mongo_ts'),
                'strikes_count': len(spx_data.get('strikes', [])),
                'sample_strikes': spx_data.get('strikes', [])[:5] if spx_data.get('strikes') else [],
                'full_response_size': len(str(spx_data))
            },
            'ndx': {
                'api_keys': list(ndx_data.keys()),
                'spot_price': ndx_data.get('spot'),
                'mongo_ts': ndx_data.get('mongo_ts'),
                'strikes_count': len(ndx_data.get('strikes', [])),
                'sample_strikes': ndx_data.get('strikes', [])[:5] if ndx_data.get('strikes') else [],
                'full_response_size': len(str(ndx_data))
            }
        }

        return JsonResponse({
            'success': True,
            'debug_data': debug_data
        })

    except Exception as e:
        logger.error(f"Error in debug_api: {str(e)}")
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


@csrf_exempt
def refresh_plot(request):
    """AJAX endpoint to refresh the plot - redirect to generate_combined_plot"""
    return generate_combined_plot(request)


def download_combined_plot(request):
    """Download the current combined plot as PNG file"""
    try:
        # Fetch and analyze current data for both indices
        spx_data = fetch_spx_data()
        ndx_data = fetch_ndx_data()

        spx_analysis = analyze_api_data(spx_data)
        ndx_analysis = analyze_ndx_api_data(ndx_data)

        # Generate historical data for both
        spx_df, spx_api_index = generate_dynamic_historical_data(spx_analysis)
        ndx_df, ndx_api_index = generate_ndx_dynamic_historical_data(ndx_analysis)

        # Create combined plot
        fig = create_combined_plot(spx_df, spx_analysis, spx_api_index,
                                   ndx_df, ndx_analysis, ndx_api_index)

        # Save to buffer
        buffer = io.BytesIO()
        try:
            fig.savefig(buffer, format='png', dpi=300, bbox_inches='tight',
                        facecolor='white', edgecolor='none')
            buffer.seek(0)
            image_bytes = buffer.getvalue()
        finally:
            plt.close(fig)

        # Create filename with timestamp
        timestamp_str = spx_analysis['api_datetime'].strftime('%Y%m%d_%H%M%S')
        filename = f'spx_ndx_options_flow_{timestamp_str}.png'

        # Create HTTP response
        response = HttpResponse(image_bytes, content_type='image/png')
        response['Content-Disposition'] = f'attachment; filename="{filename}"'

        return response

    except Exception as e:
        logger.error(f"Error in download_combined_plot: {str(e)}")
        return HttpResponse(f'Error generating plot: {str(e)}', status=500)


def download_plot(request):
    """Download the current plot as PNG file (backward compatibility - downloads combined plot)"""
    return download_combined_plot(request)


def market_summary(request):
    """Get market summary data for both SPX and NDX"""
    try:
        # Fetch current API data for both indices
        spx_data = fetch_spx_data()
        ndx_data = fetch_ndx_data()

        spx_analysis = analyze_api_data(spx_data)
        ndx_analysis = analyze_ndx_api_data(ndx_data)

        # Calculate total GEX for both
        spx_total_gex = sum(abs(strike[1]) for strike in spx_data['strikes'])
        ndx_total_gex = sum(abs(strike[1]) for strike in ndx_data['strikes'])

        # Calculate additional metrics
        spx_call_put_ratio = spx_analysis['call_centroid'] / spx_analysis['put_centroid'] if spx_analysis[
                                                                                                 'put_centroid'] != 0 else 0
        ndx_call_put_ratio = ndx_analysis['call_centroid'] / ndx_analysis['put_centroid'] if ndx_analysis[
                                                                                                 'put_centroid'] != 0 else 0

        spx_gex_millions = spx_total_gex / 1000000
        ndx_gex_millions = ndx_total_gex / 1000000

        # Determine market status (assuming same for both)
        current_hour = spx_analysis['api_datetime'].hour
        market_status = 'OPEN' if 9 <= current_hour <= 16 else 'CLOSED'

        summary_data = {
            'success': True,
            'timestamp': spx_analysis['api_datetime'].strftime('%Y-%m-%d %H:%M:%S EST'),
            'market_status': market_status,
            'spx': {
                'spot_price': f"{spx_analysis['spot_price']:.2f}",
                'call_centroid': f"{spx_analysis['call_centroid']:.2f}",
                'put_centroid': f"{spx_analysis['put_centroid']:.2f}",
                'call_put_ratio': f"{spx_call_put_ratio:.3f}",
                'total_oi': f"{spx_analysis['total_oi']:,.0f}",
                'total_gex': f"${spx_gex_millions:.1f}M",
            },
            'ndx': {
                'spot_price': f"{ndx_analysis['spot_price']:.2f}",
                'call_centroid': f"{ndx_analysis['call_centroid']:.2f}",
                'put_centroid': f"{ndx_analysis['put_centroid']:.2f}",
                'call_put_ratio': f"{ndx_call_put_ratio:.3f}",
                'total_oi': f"{ndx_analysis['total_oi']:,.0f}",
                'total_gex': f"${ndx_gex_millions:.1f}M",
            }
        }

        return JsonResponse(summary_data)

    except Exception as e:
        logger.error(f"Error in market_summary: {str(e)}")
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)