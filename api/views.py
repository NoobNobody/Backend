from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.pagination import PageNumberPagination
from .models import Categories, JobOffers, Websites
from .serializers import JobOffersSerializer
from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.response import Response
from django.http import JsonResponse

class StandardResultsSetPagination(PageNumberPagination):
    page_size = 10
    page_size_query_param = 'limit'
    max_page_size = 100

@api_view(['GET'])
def hello_world(request):
    data = {'message': 'Hello, world!'}
    return JsonResponse(data, content_type='text/javascript')

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
        offers = JobOffers.objects.filter(Category_id=category_id).select_related('Website', 'Category')
        result_page = paginator.paginate_queryset(offers, request, view=self)
        serializer = JobOffersSerializer(result_page, many=True)
        return paginator.get_paginated_response(serializer.data)

@api_view(['POST'])
def create_job_offer(request):
    if request.method == 'POST':
        category_name = request.data.get('Category')
        website_name = request.data.get('Website_name')
        website_url = request.data.get('Website')
        
        # Znajdź lub utwórz obiekty
        category_obj, _ = Categories.objects.get_or_create(Category_name=category_name)
        website_obj, _ = Websites.objects.get_or_create(Website_url=website_url, Website_name=website_name)

        # Aktualizuj dane, aby używać instancji modeli
        request.data['Category'] = category_obj.id
        request.data['Website'] = website_obj.id
        
        serializer = JobOffersSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        else:
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
