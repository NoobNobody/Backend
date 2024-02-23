from django.urls import path
from .views import CategoriesList, CategoryDetail, FilteredJobOffers, JobOffersList, JobOffersByCategory, SearchJobOffersByPosition

urlpatterns = [
    path('oferty/', JobOffersList.as_view(), name='lista-ofert-pracy'),
    path('oferty/kategoria/<int:category_id>/', JobOffersByCategory.as_view(), name='oferty-pracy-wedlug-kategorii'),
    path('kategorie/', CategoriesList.as_view(), name='categories-list'),
    path('kategorie/<int:category_id>/', CategoryDetail.as_view(), name='category-detail'), 
    path('oferty/filtrowane/<int:category_id>/', FilteredJobOffers.as_view(), name='filtrowane-oferty-pracy'),
    path('oferty/kategoria/<int:category_id>/search/', SearchJobOffersByPosition.as_view(), name='search-job-offers-by-position'),
    
]
