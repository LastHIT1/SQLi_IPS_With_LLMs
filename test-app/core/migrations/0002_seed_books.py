from django.db import migrations


def seed_books(apps, schema_editor):
    Book = apps.get_model('core', 'Book')

    books_data = [
        # Public Books (3)
        {
            "title": "The Great Gatsby",
            "author": "F. Scott Fitzgerald",
            "description": "A classic novel set in the Jazz Age, exploring themes of wealth, love, and the American Dream through the eyes of narrator Nick Carraway and the mysterious millionaire Jay Gatsby.",
            "cover_image": "https://covers.openlibrary.org/b/id/7222246-L.jpg",
            "price": 12.99,
            "published_year": 1925,
            "is_public": True,
        },
        {
            "title": "To Kill a Mockingbird",
            "author": "Harper Lee",
            "description": "A profound exploration of racial injustice in the American South, told through the innocent eyes of Scout Finch as her father, Atticus, defends a Black man falsely accused of crime.",
            "cover_image": "https://covers.openlibrary.org/b/id/8228691-L.jpg",
            "price": 14.99,
            "published_year": 1960,
            "is_public": True,
        },
        {
            "title": "1984",
            "author": "George Orwell",
            "description": "A dystopian masterpiece depicting a totalitarian society where Big Brother watches everyone. Winston Smith struggles against the oppressive Party that controls every aspect of life.",
            "cover_image": "https://covers.openlibrary.org/b/id/7222336-L.jpg",
            "price": 11.99,
            "published_year": 1949,
            "is_public": True,
        },
        # Private Books (3)
        {
            "title": "Confidential Research Notes",
            "author": "Dr. Sarah Mitchell",
            "description": "Internal research documentation containing proprietary algorithms and methodologies for advanced data analysis. Restricted access only.",
            "cover_image": "https://covers.openlibrary.org/b/id/8235822-L.jpg",
            "price": 99.99,
            "published_year": 2024,
            "is_public": False,
        },
        {
            "title": "Internal Security Protocols",
            "author": "FIU Security Team",
            "description": "Comprehensive guide to university security measures, access controls, and emergency procedures. For authorized personnel only.",
            "cover_image": "https://covers.openlibrary.org/b/id/8406786-L.jpg",
            "price": 149.99,
            "published_year": 2023,
            "is_public": False,
        },
        {
            "title": "Executive Strategy Report 2025",
            "author": "Board of Directors",
            "description": "Confidential strategic planning document outlining future initiatives, budget allocations, and organizational restructuring plans.",
            "cover_image": "https://covers.openlibrary.org/b/id/8743251-L.jpg",
            "price": 299.99,
            "published_year": 2025,
            "is_public": False,
        },
    ]

    for book_data in books_data:
        Book.objects.create(**book_data)


def remove_books(apps, schema_editor):
    Book = apps.get_model('core', 'Book')
    Book.objects.all().delete()


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0001_initial'),
    ]

    operations = [
        migrations.RunPython(seed_books, remove_books),
    ]
