from django.urls import path

from core import views

urlpatterns = [
    path("", views.home, name="home"),
    path("book/<int:book_id>/", views.book_detail, name="book_detail"),
    path("register/", views.register, name="register"),
    path("security/", views.security, name="security"),
    path("security/toggle/", views.security_toggle, name="security_toggle"),
]
