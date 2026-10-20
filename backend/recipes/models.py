from django.conf import settings
from django.db import models

from .catalog import CATEGORIES, guess_category
from .normalization import normalize_name

CATEGORY_CHOICES = [(c, c) for c in CATEGORIES]


class Ingredient(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="ingredients")
    name = models.CharField(max_length=100)
    normalized_name = models.CharField(max_length=100, editable=False)
    category = models.CharField(max_length=20, choices=CATEGORY_CHOICES, blank=True)
    quantity = models.CharField(max_length=50, blank=True)
    in_pantry = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["name"]
        constraints = [
            models.UniqueConstraint(fields=["user", "normalized_name"], name="unique_ingredient_per_user"),
        ]

    def save(self, *args, **kwargs):
        self.normalized_name = normalize_name(self.name)
        if not self.category:
            self.category = guess_category(self.normalized_name)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name


class RecipeCache(models.Model):
    external_id = models.CharField(max_length=50, unique=True)
    source = models.CharField(max_length=30, default="themealdb")
    title = models.CharField(max_length=200)
    image = models.URLField(max_length=600, blank=True)  # las fotos de Commons/Openverse superan los 200 caracteres
    category = models.CharField(max_length=100, blank=True)
    area = models.CharField(max_length=100, blank=True)
    instructions = models.TextField(blank=True)
    ingredients = models.JSONField(default=list)  # [{"ingredient": "...", "measure": "..."}]
    raw_data = models.JSONField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.title


class TranslationCache(models.Model):
    """Texto ya traducido. Cada texto se traduce una sola vez, sea cual sea la receta en la que aparezca."""

    direction = models.CharField(max_length=10)  # «en-es» o «es-en»
    source_hash = models.CharField(max_length=40)  # sha1 del texto original
    source = models.TextField()
    translated = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["direction", "source_hash"], name="unique_translation"),
        ]

    def __str__(self):
        return f"{self.direction}: {self.source[:40]}"


class FavoriteRecipe(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="favorites")
    recipe = models.ForeignKey(RecipeCache, on_delete=models.CASCADE, related_name="favorited_by")
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        constraints = [
            models.UniqueConstraint(fields=["user", "recipe"], name="unique_favorite_per_user"),
        ]


class ShoppingListItem(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="shopping_items")
    name = models.CharField(max_length=100)
    normalized_name = models.CharField(max_length=100, editable=False)
    quantity = models.CharField(max_length=50, blank=True)
    category = models.CharField(max_length=20, choices=CATEGORY_CHOICES, blank=True)
    bought = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["bought", "category", "name"]

    def save(self, *args, **kwargs):
        self.normalized_name = normalize_name(self.name)
        if not self.category:
            self.category = guess_category(self.normalized_name)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name


class MealPlan(models.Model):
    """Dieta semanal generada por la IA: 7 días con sus comidas. Se guarda para consultarla otro día."""

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="meal_plans")
    title = models.CharField(max_length=120)
    options = models.JSONField(default=dict)  # lo que se pidió: objetivo, dieta, evitar, comidas, calorías
    days = models.JSONField(default=list)  # [{"day", "meals": [{"type", "title", "description", "calories", "ingredients"}]}]
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at", "-id"]

    def __str__(self):
        return self.title
