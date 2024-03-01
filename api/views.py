from datetime import datetime, timedelta
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.pagination import PageNumberPagination
from .models import Categories, JobOffers
from .serializers import CategoriesSerializer, JobOffersSerializer
from rest_framework.response import Response
from django.db.models import Avg, Max, Min, Case, When, Value, Count, Q, CharField
from django.db.models.functions import TruncDay
import re
from .helping_methods import extract_earnings_data, sanitize_salary_range

class StandardResultsSetPagination(PageNumberPagination):
    page_size = 10
    page_size_query_param = 'limit'
    max_page_size = 100

class JobOffersList(APIView):
    def get(self, request, *args, **kwargs):
        paginator = StandardResultsSetPagination()
        offers = JobOffers.objects.all().select_related('Website', 'Category') 
        result_page = paginator.paginate_queryset(offers, request, view=self)
        serializer = JobOffersSerializer(result_page, many=True)
        return paginator.get_paginated_response(serializer.data)

class CategoriesList(APIView):
    def get(self, request, *args, **kwargs):
        categories = Categories.objects.all()
        serializer = CategoriesSerializer(categories, many=True)
        return Response(serializer.data)

class JobOffersAnalysis(APIView):
    def get(self, request, format=None):
        data = JobOffers.objects.values('Website__Website_name').annotate(offers_count=Count('Website')).order_by('-offers_count')
        return Response(data)
    
class JobOffersCategoryAnalysis(APIView):
    def get(self, request, format=None):
        data = JobOffers.objects.values('Category__Category_name').annotate(offers_count=Count('Category')).order_by('-offers_count')
        return Response(data)
    
class AverageEarningsAnalysis(APIView):
    def get(self, request, format=None):

        job_offers = JobOffers.objects.annotate(
            job_type=Case(
                When(Average_Earnings__gt=1000, Min_Earnings__gt=1000, Max_Earnings__gt=1000, then=Value('monthly')),
                When(Average_Earnings__lte=1000, then=Value('hourly')),
                default=Value('unknown'),  
                output_field=CharField(),
            )
        )

        hourly_stats = job_offers.filter(job_type='hourly').aggregate(
            avg_hourly=Avg('Average_Earnings'),
            min_hourly=Min('Min_Earnings'),
            max_hourly=Max('Max_Earnings')
        )

        monthly_stats = job_offers.filter(job_type='monthly').aggregate(
            avg_monthly=Avg('Average_Earnings'),
            min_monthly=Min('Min_Earnings'),
            max_monthly=Max('Max_Earnings')
        )

        def round_to_one_decimal(value):
            return round(value, 1) if value is not None else 0

        return Response({
            'average_hourly_earnings': round_to_one_decimal(hourly_stats['avg_hourly']),
            'min_hourly_earnings': round_to_one_decimal(hourly_stats['min_hourly']),
            'max_hourly_earnings': round_to_one_decimal(hourly_stats['max_hourly']),
            'average_monthly_earnings': round_to_one_decimal(monthly_stats['avg_monthly']),
            'min_monthly_earnings': round_to_one_decimal(monthly_stats['min_monthly']),
            'max_monthly_earnings': round_to_one_decimal(monthly_stats['max_monthly']),
        })
    
class EarningsHeatmapAnalysis(APIView):
    def get(self, request, format=None):
        job_offers = JobOffers.objects.exclude(Location_Latitude__isnull=True)\
                                      .exclude(Location_Longitude__isnull=True)\
                                      .exclude(Average_Earnings__isnull=True)\
                                      .filter(Average_Earnings__gt=1000)
        
        location_earnings = {}

        for offer in job_offers:
            location = re.sub(r'(\,|\().*$', '', offer.Location).strip()

            if location in location_earnings:
                location_earnings[location]['total'] += offer.Average_Earnings
                location_earnings[location]['count'] += 1
            else:
                location_earnings[location] = {
                    'total': offer.Average_Earnings,
                    'count': 1,
                    'lat': offer.Location_Latitude,
                    'lng': offer.Location_Longitude
                }

        response_data = [{
            "Location": location,
            "AverageEarnings": data['total'] / data['count'],
            "Coordinates": {
                "lat": data['lat'],
                "lng": data['lng']
            }
        } for location, data in location_earnings.items()]

        return Response(response_data)

class JobOffersByDayAnalysis(APIView):
    def get(self, request, format=None):
        job_offers_by_day = (
            JobOffers.objects
            .annotate(day=TruncDay('Date'))
            .values('day')
            .annotate(offers_count=Count('id'))
            .order_by('day')
        )
        return Response(job_offers_by_day)
       
class FilterAllJobOffers(APIView):
    def get(self, request, *args, **kwargs):
        paginator = StandardResultsSetPagination()
        search_query = request.query_params.get('search', None)
        category_name = request.query_params.get('categoryName', None)
        province_query = request.query_params.get('province', None)
        location_query = request.query_params.get('jobLocation', None)
        employment_types = request.query_params.getlist('selectedJobTime')
        date_filter = request.query_params.get('selectedDate', None)
        job_model_filter = request.query_params.getlist('selectedJobModel')
        job_type_filter = request.query_params.getlist('selectedJobType')
        salary_type = request.query_params.get('selectedSalaryType')
        salary_range = request.query_params.get('selectedSalaryRange')
        salary_range = sanitize_salary_range(salary_range)

        if category_name:
            offers_query = JobOffers.objects.filter(Category__Category_name=category_name)
        else:
            offers_query = JobOffers.objects.all()

        offers_query = offers_query.select_related('Website', 'Category')

        if search_query:
            offers_query = offers_query.filter(Position__icontains=search_query)

        if province_query:
            offers_query = offers_query.filter(Province__icontains=province_query)

        if location_query:
            offers_query = offers_query.filter(Location__icontains=location_query)


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

        offers_query = offers_query.order_by('-Date')
        result_page = paginator.paginate_queryset(offers_query, request, view=self)
        serializer = JobOffersSerializer(result_page, many=True)
        return paginator.get_paginated_response(serializer.data)    
    
