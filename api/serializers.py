from rest_framework import serializers
from .models import JobOffers, Websites, Categories

class WebsiteSerializer(serializers.ModelSerializer):
    class Meta:
        model = Websites
        fields = ['Website_name', 'Website_url']

class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Categories
        fields = ['Category_name'] 

class JobOffersSerializer(serializers.ModelSerializer):
    Website = serializers.PrimaryKeyRelatedField(queryset=Websites.objects.all())
    Category = serializers.PrimaryKeyRelatedField(queryset=Categories.objects.all())

    class Meta:
        model = JobOffers
        fields = ['Position', 'Firm', 'Website', 'Category', 'Date', 'Location', 'Job_type', 'Working_hours', 'Job_model', 'Earnings', 'Link']
