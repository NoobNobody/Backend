# Generated by Django 5.0.1 on 2024-02-25 13:59

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='Categories',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('Category_name', models.CharField(max_length=200)),
            ],
        ),
        migrations.CreateModel(
            name='Websites',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('Website_name', models.CharField(max_length=200)),
                ('Website_url', models.URLField()),
            ],
        ),
        migrations.CreateModel(
            name='JobOffers',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('Position', models.CharField(max_length=500)),
                ('Firm', models.CharField(blank=True, max_length=200, null=True)),
                ('Earnings', models.CharField(blank=True, max_length=100, null=True)),
                ('Location', models.CharField(blank=True, max_length=200, null=True)),
                ('Province', models.CharField(blank=True, max_length=100, null=True)),
                ('Date', models.DateField(blank=True, null=True)),
                ('Job_type', models.CharField(blank=True, max_length=200, null=True)),
                ('Working_hours', models.CharField(blank=True, max_length=200, null=True)),
                ('Job_model', models.CharField(blank=True, max_length=200, null=True)),
                ('Link', models.URLField(default='', max_length=1000)),
                ('Category', models.ForeignKey(null=True, on_delete=django.db.models.deletion.CASCADE, to='api.categories')),
                ('Website', models.ForeignKey(null=True, on_delete=django.db.models.deletion.CASCADE, to='api.websites')),
            ],
            options={
                'ordering': ['-Date'],
            },
        ),
    ]
