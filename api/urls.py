from django.urls import path
from .views import CategoriesList, CategoryDetail, FiltrateAndSearchJobOffersByCategory, FiltrateAndSearchAllJobOffers, JobOffersList, JobOffersByCategory, SearchJobOffersByPosition, filterAllJobOffers

urlpatterns = [
    path('all_offers/', JobOffersList.as_view(), name='lista-ofert-pracy'),
    path('oferty/kategoria/<int:category_id>/', JobOffersByCategory.as_view(), name='oferty-pracy-wedlug-kategorii'),
    path('categories/', CategoriesList.as_view(), name='categories-list'),
    path('kategorie/<int:category_id>/', CategoryDetail.as_view(), name='category-detail'), 
    path('oferty/filtrowane/<int:category_id>/', FiltrateAndSearchJobOffersByCategory.as_view(), name='filtrowane-oferty-pracy'),
    path('oferty/kategoria/<int:category_id>/search/', SearchJobOffersByPosition.as_view(), name='search-job-offers-by-position'),
    path('offers/search/', FiltrateAndSearchAllJobOffers.as_view(), name='search-job-offers'),
    path('offers/zwraca/', filterAllJobOffers.as_view(), name='search-job-offers'),
]
