from django.urls import path
from rest_framework.routers import SimpleRouter
from rest_framework_simplejwt.views import TokenRefreshView

from . import views

router = SimpleRouter()
router.register("ingredients", views.IngredientViewSet, basename="ingredient")
router.register("shopping-list", views.ShoppingListViewSet, basename="shopping-list")
router.register("favorites", views.FavoriteViewSet, basename="favorite")

urlpatterns = [
    path("health/", views.health, name="health"),
    path("auth/register/", views.RegisterView.as_view(), name="register"),
    path("auth/login/", views.LoginView.as_view(), name="login"),
    path("auth/token/refresh/", TokenRefreshView.as_view(), name="token-refresh"),
    path("auth/me/", views.MeView.as_view(), name="me"),
    path("recipes/suggestions/", views.RecipeSuggestionsView.as_view(), name="recipe-suggestions"),
    path("recipes/<str:external_id>/", views.RecipeDetailView.as_view(), name="recipe-detail"),
    path("ai/suggestions/", views.AISuggestionsView.as_view(), name="ai-suggestions"),
    path("ai/adapt-recipe/", views.AIAdaptRecipeView.as_view(), name="ai-adapt-recipe"),
    path("ai/shopping-list/", views.AIShoppingListView.as_view(), name="ai-shopping-list"),
    *router.urls,
]
