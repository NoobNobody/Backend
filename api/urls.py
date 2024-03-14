from django.urls import path
from .views import JobOffersByDayAnalysis, JobOffersList, CategoriesList, FilterAllJobOffers, JobOffersAnalysis, JobOffersCategoryAnalysis, AverageEarningsAnalysis, EarningsHeatmapAnalysis, JobOffersLocations

urlpatterns = [
    path('offers/', JobOffersList.as_view(), name='job_offers_list'),
    path('categories/', CategoriesList.as_view(), name='categories-list'),
    path('offers/filter/', FilterAllJobOffers.as_view(), name='search-job-offers'),

    path('analysis/job_offers', JobOffersAnalysis.as_view(), name='job_offers_analysis'),
    path('analysis/job_offers_category/', JobOffersCategoryAnalysis.as_view(), name='job_offers_category_analysis'),
    path('analysis/average_earnings/', AverageEarningsAnalysis.as_view(), name='average_earnings_analysis'),
    path('analysis/earnings_heatmap/', EarningsHeatmapAnalysis.as_view(), name='heatmap_earnings_analysis'),
    path('analysis/job_offers_by_day/', JobOffersByDayAnalysis.as_view(), name='job_offers_by_day'),
    path('job_offers_location_map/', JobOffersLocations.as_view(), name='job_offers_by_day'),
]
    

    

