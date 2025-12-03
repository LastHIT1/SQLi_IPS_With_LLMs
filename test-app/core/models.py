from django.db import models


class Book(models.Model):
    title = models.CharField(max_length=255)
    author = models.CharField(max_length=255)
    description = models.TextField()
    cover_image = models.URLField(max_length=500)
    price = models.DecimalField(max_digits=6, decimal_places=2, default=9.99)
    published_year = models.IntegerField(default=2020)
    is_public = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.title} by {self.author}"
