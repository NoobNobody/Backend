from rest_framework import serializers
from .models import JobOffers, Websites, Categories

class WebsiteSerializer(serializers.ModelSerializer):
    class Meta:
        model = Websites
        fields = ['Website_name', 'Website_url']

class CategoriesSerializer(serializers.ModelSerializer):
    offers_count = serializers.SerializerMethodField()

    class Meta:
        model = Categories
        fields = ('id', 'Category_name', 'offers_count')

    def get_offers_count(self, obj):
        return obj.joboffers_set.count() 

class JobOffersSerializer(serializers.ModelSerializer):
    Website_info = serializers.SerializerMethodField()
    Category_info = serializers.SerializerMethodField()

    class Meta:
        model = JobOffers
        fields = ['Position', 'Firm', 'Website_info', 'Category_info', 'Category', 'Date', 'Location', 'Job_type', 'Working_hours', 'Job_model', 'Earnings', 'Link']

    def get_Website_info(self, obj):
        website = obj.Website
        return WebsiteSerializer(website).data
    
    def get_Category_info(self, obj):
        category = obj.Category
        return CategoriesSerializer(category).data
