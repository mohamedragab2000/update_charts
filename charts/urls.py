from django.urls import path
from . import views

urlpatterns = [
    # Main dashboard
    path('', views.spx_dashboard, name='spx_dashboard'),

    # Data endpoints
    path('get_spx_data/', views.get_spx_data, name='get_spx_data'),
    path('get_ndx_data/', views.get_ndx_data, name='get_ndx_data'),
    path('get_combined_data/', views.get_combined_data, name='get_combined_data'),

    # Plot generation endpoints
    path('generate_spx_plot/', views.generate_spx_plot, name='generate_spx_plot'),
    path('generate_ndx_plot/', views.generate_ndx_plot, name='generate_ndx_plot'),
    path('generate_combined_plot/', views.generate_combined_plot, name='generate_combined_plot'),

    # Legacy/compatibility endpoints
    path('refresh_plot/', views.refresh_plot, name='refresh_plot'),

    # Download endpoints
    path('download_plot/', views.download_plot, name='download_plot'),
    path('download_combined_plot/', views.download_combined_plot, name='download_combined_plot'),

    # Summary and debug endpoints
    path('market_summary/', views.market_summary, name='market_summary'),
    path('debug_api/', views.debug_api, name='debug_api'),
]