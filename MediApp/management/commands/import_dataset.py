import csv
from datetime import datetime
from pathlib import Path
from django.conf import settings
from django.core.management.base import BaseCommand
from django.utils import timezone
from MediApp.utils.data_loader import import_csv_dataset

class Command(BaseCommand):
    help = 'Imports data from CSV dataset files'

    def handle(self, *args, **kwargs):
        base_dir = Path(settings.BASE_DIR)
        self.stdout.write(f'Importing CSV dataset from {base_dir}')
        imported = import_csv_dataset(base_dir)

        if imported:
            self.stdout.write(self.style.SUCCESS('Successfully imported dataset.'))
        else:
            self.stdout.write(self.style.WARNING('No dataset imported. CSV files not found.'))
