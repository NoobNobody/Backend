from django.urls import path
from .views import JobOffersList, JobOffersByCategory, create_job_offer, hello_world

urlpatterns = [
    path('oferty/', JobOffersList.as_view(), name='lista-ofert-pracy'),
    path('oferty/kategoria/<int:category_id>/', JobOffersByCategory.as_view(), name='oferty-pracy-wedlug-kategorii'),
    path('ofertypracy/', create_job_offer, name='create_job_offer'),
    path('hello-world/', hello_world, name='hello_world'),
]
