from django.urls import path
from . import views

urlpatterns = [
    path("", views.race_list, name="race_list"),
    path("<int:race_id>/", views.race_detail, name="race_detail"),
    # path("<int:race_id>/reviews/", views.race_reviews, name="race_reviews"), 
    # path("<int:race_id>/reviews/<int:review_id>/", views.race_review, name="race_review"),
    # path("open/top6/", views.race_top6, name="race_top6"),
    # path("<int:race_id>/favorite/", views.race_favorite, name="race_favorite"),
]