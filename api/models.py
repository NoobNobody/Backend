from django.db import models

class Websites(models.Model):
    Website_name = models.CharField(max_length=200)
    Website_url = models.URLField()

    def __str__(self):
        return self.Website_name

class Categories(models.Model):
    Category_name = models.CharField(max_length=200)

    def __str__(self):
        return self.Category_name

class JobOffers(models.Model):
    Position = models.CharField(max_length=500)
    Website = models.ForeignKey(Websites, on_delete=models.CASCADE, null=True)
    Category = models.ForeignKey(Categories, on_delete=models.CASCADE, null=True)
    Firm = models.CharField(max_length=200, blank=True, null=True)
    Earnings = models.CharField(max_length=100, null=True, blank=True)
    Location = models.CharField(max_length=200, null=True, blank=True)
    Province = models.CharField(max_length=50, null=True, blank=True)
    Date = models.DateField(null=True, blank=True)
    Job_type = models.CharField(max_length=200, null=True, blank=True)
    Working_hours = models.CharField(max_length=200, null=True, blank=True)
    Job_model = models.CharField(max_length=200, null=True, blank=True)
    Link = models.URLField(max_length=1000, default='')

    class Meta:
        ordering = ['-Date'] 

    def __str__(self):
        return f"{self.Position} w {self.Website}"
    