# Generated by Django 5.0.1 on 2024-03-02 00:21

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('api', '0005_joboffers_earnings_range_joboffers_earnings_type'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='joboffers',
            name='Earnings_Range',
        ),
    ]
