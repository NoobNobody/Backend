from datetime import datetime, timedelta
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.pagination import PageNumberPagination
from .models import Categories, JobOffers, Websites
from .serializers import CategoriesSerializer, JobOffersSerializer
from rest_framework import status
from rest_framework.response import Response
from django.db.models import Q
import re
import logging

class StandardResultsSetPagination(PageNumberPagination):
    page_size = 10
    page_size_query_param = 'limit'
    max_page_size = 100

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

def extract_earnings_data(earnings_str):
    if not earnings_str:
        logger.debug(f"Earnings string is None or empty.")
        return None, None, None

    earnings_str = re.sub(r'\s+|\u00A0', '', earnings_str)
    earnings_str = earnings_str.replace('–', '-').replace('—', '-')

    matches = re.findall(r'(\d+)-(\d+)zł(/(godz\.|mies\.))?', earnings_str)
    if not matches:
        logger.debug(f"No matches found in earnings string: {earnings_str}")
        return None, None, None

    min_earnings, max_earnings, _, earnings_type = matches[0]
    min_earnings, max_earnings = int(min_earnings), int(max_earnings)
    earnings_type = 'hourly' if 'godz.' in earnings_str else 'monthly'

    logger.debug(f"Extracted earnings data from string '{earnings_str}': min_earnings={min_earnings}, max_earnings={max_earnings}, earnings_type={earnings_type}")
    return min_earnings, max_earnings, earnings_type


class JobOffersList(APIView):
    def get(self, request, *args, **kwargs):
        paginator = StandardResultsSetPagination()
        offers = JobOffers.objects.all().select_related('Website', 'Category') 
        result_page = paginator.paginate_queryset(offers, request, view=self)
        serializer = JobOffersSerializer(result_page, many=True)
        return paginator.get_paginated_response(serializer.data)

class JobOffersByCategory(APIView):
    def get(self, request, category_id, *args, **kwargs):
        paginator = StandardResultsSetPagination()
        offers_query = JobOffers.objects.filter(Category_id=category_id).select_related('Website', 'Category')

        offers_query = offers_query.order_by('-Date')

        result_page = paginator.paginate_queryset(offers_query, request, view=self)
        serializer = JobOffersSerializer(result_page, many=True)
        return paginator.get_paginated_response(serializer.data)
    
class CategoriesList(APIView):
    def get(self, request, *args, **kwargs):
        categories = Categories.objects.all()
        serializer = CategoriesSerializer(categories, many=True)
        return Response(serializer.data)
    
class CategoryDetail(APIView):
    def get(self, request, category_id, *args, **kwargs):
        try:
            category = Categories.objects.get(pk=category_id)
            serializer = CategoriesSerializer(category)
            return Response(serializer.data)
        except Categories.DoesNotExist:
            return Response({'error': 'Kategoria nie istnieje'}, status=status.HTTP_404_NOT_FOUND)
        
class SearchJobOffersByPosition(APIView):
    def get(self, request, category_id, *args, **kwargs):
        search_query = request.query_params.get('search', None)
        paginator = StandardResultsSetPagination()
        offers_query = JobOffers.objects.filter(Category_id=category_id).select_related('Website', 'Category')

        if search_query:
            offers_query = offers_query.filter(Q(Position__icontains=search_query))

        offers_query = offers_query.order_by('-Date')

        result_page = paginator.paginate_queryset(offers_query, request, view=self)
        serializer = JobOffersSerializer(result_page, many=True)
        return paginator.get_paginated_response(serializer.data)

class FilteredJobOffers(APIView):
    def get(self, request, category_id, *args, **kwargs):
        paginator = StandardResultsSetPagination()
        search_query = request.query_params.get('search', None)
        offers_query = JobOffers.objects.filter(Category_id=category_id).select_related('Website', 'Category')
        employment_types = request.query_params.getlist('selectedJobTime')
        date_filter = request.query_params.get('selectedDate', None)
        job_model_filter = request.query_params.getlist('selectedJobModel')
        job_type_filter = request.query_params.getlist('selectedJobType')
        salary_type = request.query_params.get('selectedSalaryType')
        salary_range = request.query_params.get('selectedSalaryRange')
        
        logger.debug(f"Received jobModels filter: {job_model_filter}")
        logger.debug(f"Received workingours filter: {employment_types}")
        logger.debug(f"Query params: {request.query_params}")
        logger.debug(f"Search query: {search_query}")

        if search_query:
            offers_query = offers_query.filter(Q(Position__icontains=search_query))

        if date_filter:
            if date_filter == 'last24Hours':
                offers_query = offers_query.filter(Date__gte=datetime.now() - timedelta(days=1))
            elif date_filter == 'last3Days':
                offers_query = offers_query.filter(Date__gte=datetime.now() - timedelta(days=3))
            elif date_filter == 'lastWeek':
                offers_query = offers_query.filter(Date__gte=datetime.now() - timedelta(weeks=1))
            elif date_filter == 'last2Weeks':
                offers_query = offers_query.filter(Date__gte=datetime.now() - timedelta(weeks=2))

        if employment_types:
            query = Q()
            for employment_type in employment_types:
                if employment_type == 'fullTime':
                    query |= Q(Working_hours__iexact="Pełny etat") | Q(Working_hours__iexact="Pełen etat")
                elif employment_type == 'partTime':
                    query |= Q(Working_hours__icontains="Część etatu") | Q(Working_hours__icontains="Niepełny etat") | Q(Working_hours__icontains="3/4 etatu")
                elif employment_type == 'temporary':
                    query |= Q(Working_hours__icontains="Tymczasowa")
            offers_query = offers_query.filter(query)

        if job_model_filter:
            query = Q()
            for job_model in job_model_filter:
                if job_model == 'stationaryWork':
                    query |= Q(Job_model__icontains="Praca stacjonarna") | Q(Job_model__icontains="W siedzibie firmy")
                elif job_model == 'hybridWork':
                    query |= Q(Job_model__icontains="Praca hybrydowa")
                elif job_model == 'remoteWork':
                    query |= Q(Job_model__icontains="Praca zdalna")
                elif job_model == 'mobileWork':
                    query |= Q(Job_model__icontains="Praca mobilna")
            offers_query = offers_query.filter(query)

        if job_type_filter:
            query = Q()
            for job_type in job_type_filter:
                if job_type == 'contractOfEmployment':
                    query |= Q(Job_type__icontains="Umowa o pracę")
                elif job_type == 'mandateContract':
                    query |= Q(Job_type__icontains="Umowa zlecenie")
                elif job_type == 'different':
                    query |= Q(Job_type__icontains="Inny") | Q(Job_type__icontains="Praca tymczasowa") | Q(Job_type__icontains="Praca stała") | Q(Job_type__icontains="umowa na zastępstwo") | Q(Job_type__icontains="umowa o pracę tymczasową")
                elif job_type == 'contractWork': 
                    query |= Q(Job_type__icontains="Umowa o dzieło")
                elif job_type == 'selfEmployment':
                    query |= Q(Job_type__icontains="Samozatrudnienie")
                elif job_type == 'internship':
                    query |= Q(Job_type__icontains="staż/praktyka") | Q(Job_type__icontains="Praktyka / staż") | Q(Job_type__icontains="Umowa o staż / praktyki")
                elif job_type == 'b2bContract':
                    query |= Q(Job_type__icontains="Kontrakt B2B")
            offers_query = offers_query.filter(query)  

        if salary_type and salary_range:
            if salary_range.startswith('>'):
                min_range = int(salary_range[1:])
                offers = []
                for offer in offers_query:
                    min_earnings, max_earnings, earnings_type = extract_earnings_data(offer.Earnings)
                    if earnings_type == salary_type and max_earnings is not None:
                        if max_earnings > min_range:
                            offers.append(offer)
            elif salary_range.startswith('<'):
                max_range = int(salary_range[1:])
                offers = []
                for offer in offers_query:
                    min_earnings, max_earnings, earnings_type = extract_earnings_data(offer.Earnings)
                    if earnings_type == salary_type and min_earnings is not None:
                        if min_earnings < max_range:
                            offers.append(offer)
            else:
                min_range, max_range = map(int, salary_range.split('-'))
                offers = []
                for offer in offers_query:
                    min_earnings, max_earnings, earnings_type = extract_earnings_data(offer.Earnings)
                    if earnings_type == salary_type and min_earnings is not None and max_earnings is not None:
                        if min_earnings <= max_range and max_earnings >= min_range:
                            offers.append(offer)
            offers_query = JobOffers.objects.filter(id__in=[offer.id for offer in offers])

        logger.debug(f"Final query: {str(offers_query.query)}")
        offers_query = offers_query.order_by('-Date')
        result_page = paginator.paginate_queryset(offers_query, request, view=self)
        serializer = JobOffersSerializer(result_page, many=True)
        return paginator.get_paginated_response(serializer.data)