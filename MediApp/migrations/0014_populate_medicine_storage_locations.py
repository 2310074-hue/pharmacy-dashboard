from django.db import migrations
import random


def populate_storage_locations(apps, schema_editor):
    Medicine = apps.get_model('MediApp', 'Medicine')
    
    racks_map = {
        'A': ['Rack A-1', 'Rack A-2', 'Rack A-3'],
        'B': ['Rack B-1', 'Rack B-2', 'Rack B-3'],
        'C': ['Rack C-1', 'Rack C-2', 'Rack C-3'],
        'D': ['Rack D-1', 'Rack D-2', 'Rack D-3'],
        'E': ['Rack E-1', 'Rack E-2'],
        'F': ['Rack F-1', 'Rack F-2'],
        'G': ['Rack G-1', 'Rack G-2'],
        'H': ['Rack H-1', 'Rack H-2'],
        'I': ['Rack I-1', 'Rack I-2'],
        'J': ['Rack J-1', 'Rack J-2'],
        'K': ['Rack K-1', 'Rack K-2'],
        'L': ['Rack L-1', 'Rack L-2'],
        'M': ['Rack M-1', 'Rack M-2', 'Rack M-3'],
        'N': ['Rack N-1', 'Rack N-2'],
        'O': ['Rack O-1', 'Rack O-2'],
        'P': ['Rack P-1', 'Rack P-2', 'Rack P-3'],
        'Q': ['Rack Q-1'],
        'R': ['Rack R-1', 'Rack R-2'],
        'S': ['Rack S-1', 'Rack S-2', 'Rack S-3'],
        'T': ['Rack T-1', 'Rack T-2'],
        'U': ['Rack U-1'],
        'V': ['Rack V-1', 'Rack V-2'],
        'W': ['Rack W-1'],
        'X': ['Rack X-1'],
        'Y': ['Rack Y-1'],
        'Z': ['Rack Z-1', 'Rack Z-2'],
    }
    
    shelves = ['Shelf 1', 'Shelf 2', 'Shelf 3', 'Shelf 4', 'Drawer A', 'Drawer B', 'Box 1', 'Box 2']
    
    rng = random.Random(101)
    
    for medicine in Medicine.objects.all():
        if not medicine.rack_number:
            first_letter = medicine.name[0].upper() if medicine.name else 'A'
            rack_choices = racks_map.get(first_letter, ['Rack A-1', 'Rack B-1', 'Rack C-1', 'Cabinet D-1'])
            medicine.rack_number = rng.choice(rack_choices)
        if not medicine.shelf_number:
            medicine.shelf_number = rng.choice(shelves)
        medicine.save()


def reverse_func(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('MediApp', '0013_medicine_rack_number_medicine_shelf_number'),
    ]

    operations = [
        migrations.RunPython(populate_storage_locations, reverse_func),
    ]
