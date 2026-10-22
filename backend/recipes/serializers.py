from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer

from .models import Dish, FavoriteRecipe, Ingredient, MealPlan, RecipeCache, ShoppingListItem
from .normalization import normalize_name
from .services.ai import MEAL_TYPES, StepField, normalize_difficulty, normalize_meal_type
from .services.localization import localize_recipe
from .services.recipes import recipe_to_dict

User = get_user_model()


# --- Autenticación ---


class RegisterSerializer(serializers.ModelSerializer):
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True, style={"input_type": "password"})

    class Meta:
        model = User
        fields = ["id", "email", "username", "password"]
        read_only_fields = ["id"]

    def validate_email(self, value):
        if User.objects.filter(email__iexact=value).exists():
            raise serializers.ValidationError("Ya existe una cuenta con este correo.")
        return value

    def validate_username(self, value):
        if User.objects.filter(username__iexact=value).exists():
            raise serializers.ValidationError("Este nombre de usuario ya está en uso.")
        return value

    def validate(self, attrs):
        # La validación de contraseña necesita el usuario para detectar «contraseña = tu nombre»
        validate_password(attrs["password"], User(username=attrs.get("username", ""), email=attrs.get("email", "")))
        return attrs

    def create(self, validated_data):
        return User.objects.create_user(**validated_data)


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ["id", "email", "username"]


class DeleteAccountSerializer(serializers.Serializer):
    """Para borrar la cuenta hay que repetir la contraseña (un token robado no basta)."""

    password = serializers.CharField(write_only=True, style={"input_type": "password"})

    def validate_password(self, value):
        if not self.context["request"].user.check_password(value):
            raise serializers.ValidationError("La contraseña no es correcta.")
        return value


class LoginSerializer(TokenObtainPairSerializer):
    """Acepta `email` o `username` junto con la contraseña."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["username"].required = False
        self.fields["email"] = serializers.EmailField(required=False, write_only=True)

    def validate(self, attrs):
        email = attrs.pop("email", None)
        if email:
            usuario = User.objects.filter(email__iexact=email).first()
            attrs["username"] = usuario.username if usuario else ""
        if not attrs.get("username"):
            raise serializers.ValidationError({"detail": "Indica tu correo o tu nombre de usuario."})
        return super().validate(attrs)


# --- Despensa y lista de la compra ---


class _OwnedNameMixin:
    """Valida el nombre: no vacío tras normalizar y sin repetidos por usuario."""

    model: type
    duplicate_message = "Ya lo tienes."

    def validate_name(self, value):
        value = value.strip()
        clave = normalize_name(value)
        if not clave:
            raise serializers.ValidationError("El nombre no puede estar vacío.")
        usuario = self.context["request"].user
        repetidos = self.model.objects.filter(user=usuario, normalized_name=clave)
        if self.instance is not None:
            repetidos = repetidos.exclude(pk=self.instance.pk)
        if repetidos.exists():
            raise serializers.ValidationError(self.duplicate_message)
        return value


class IngredientSerializer(_OwnedNameMixin, serializers.ModelSerializer):
    model = Ingredient
    duplicate_message = "Este ingrediente ya está en tu despensa."

    class Meta:
        model = Ingredient
        fields = ["id", "name", "normalized_name", "category", "quantity", "in_pantry", "created_at"]
        read_only_fields = ["id", "normalized_name", "created_at"]
        extra_kwargs = {"category": {"required": False}, "quantity": {"required": False, "allow_blank": True}}


class ShoppingListItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = ShoppingListItem
        fields = ["id", "name", "normalized_name", "quantity", "category", "bought", "created_at"]
        read_only_fields = ["id", "normalized_name", "created_at"]
        extra_kwargs = {"category": {"required": False}, "quantity": {"required": False, "allow_blank": True}}

    def validate_name(self, value):
        value = value.strip()
        if not normalize_name(value):
            raise serializers.ValidationError("El nombre no puede estar vacío.")
        return value


# --- Recetas y favoritos ---


class RecipeIngredientSerializer(serializers.Serializer):
    ingredient = serializers.CharField()
    measure = serializers.CharField(allow_blank=True, required=False, default="")


class RecipeCacheSerializer(serializers.ModelSerializer):
    class Meta:
        model = RecipeCache
        fields = ["external_id", "source", "title", "image", "category", "area", "instructions", "ingredients"]


class FavoriteSerializer(serializers.ModelSerializer):
    """Con `?lang=es` en la petición, la receta se devuelve traducida al español."""

    recipe = RecipeCacheSerializer(read_only=True)

    class Meta:
        model = FavoriteRecipe
        fields = ["id", "recipe", "notes", "created_at"]
        read_only_fields = ["id", "recipe", "created_at"]

    def to_representation(self, instance):
        datos = super().to_representation(instance)
        datos["recipe"] = recipe_to_dict(instance.recipe)  # incluye lo extra de las recetas de la IA
        peticion = self.context.get("request")
        lang = peticion.query_params.get("lang", "") if peticion is not None else ""
        if lang:
            datos["recipe"] = localize_recipe(datos["recipe"], lang)
        return datos


class _RecipeIngredientIn(serializers.Serializer):
    name = serializers.CharField(max_length=120)
    quantity = serializers.CharField(allow_blank=True, required=False, default="", max_length=60)


class _AIImageSerializer(serializers.Serializer):
    url = serializers.URLField(max_length=500)
    credit = serializers.CharField(allow_blank=True, required=False, default="", max_length=100)
    page = serializers.URLField(allow_blank=True, required=False, default="", max_length=500)

    def validate_url(self, value):
        if not value.startswith("https://"):
            raise serializers.ValidationError("La imagen debe ser https.")
        return value


class AISavedRecipeSerializer(serializers.Serializer):
    """Una receta propuesta por la IA que el usuario quiere guardar en su recetario."""

    title = serializers.CharField(max_length=200)
    description = serializers.CharField(allow_blank=True, required=False, default="", max_length=500)
    meal_type = serializers.CharField(allow_blank=True, required=False, default="otro", max_length=40)
    servings = serializers.IntegerField(min_value=1, max_value=100, required=False, allow_null=True, default=None)
    estimated_minutes = serializers.IntegerField(min_value=0, max_value=3000, required=False, allow_null=True, default=None)
    difficulty = serializers.CharField(allow_blank=True, required=False, default="", max_length=20)
    ingredients = serializers.ListField(child=_RecipeIngredientIn(), min_length=1, max_length=60)
    steps = serializers.ListField(child=StepField(), min_length=1, max_length=40)
    tips = serializers.ListField(child=serializers.CharField(max_length=500), required=False, default=list, max_length=20)
    prep_minutes = serializers.IntegerField(min_value=0, max_value=3000, required=False, allow_null=True, default=None)
    cook_minutes = serializers.IntegerField(min_value=0, max_value=3000, required=False, allow_null=True, default=None)
    image = _AIImageSerializer(required=False, allow_null=True, default=None)

    def validate_meal_type(self, value):
        return normalize_meal_type(value)

    def validate_difficulty(self, value):
        return normalize_difficulty(value)


class FavoriteCreateSerializer(serializers.Serializer):
    """O bien `external_id` (receta de TheMealDB) o bien `recipe` (receta de la IA)."""

    external_id = serializers.CharField(max_length=50, required=False)
    recipe = AISavedRecipeSerializer(required=False)
    notes = serializers.CharField(allow_blank=True, required=False, default="")

    def validate(self, attrs):
        if bool(attrs.get("external_id")) == bool(attrs.get("recipe")):
            raise serializers.ValidationError("Indica `external_id` o `recipe`, pero no los dos.")
        return attrs


class SuggestionsQuerySerializer(serializers.Serializer):
    ingredients = serializers.CharField(required=False, allow_blank=True, default="")
    category = serializers.CharField(required=False, allow_blank=True, default="")
    max_missing = serializers.IntegerField(required=False, min_value=0, allow_null=True, default=None)
    search = serializers.CharField(required=False, allow_blank=True, default="")
    lang = serializers.ChoiceField(choices=["es"], required=False, allow_blank=True, default="")


# --- IA: entradas ---


class AIRecipeInputSerializer(serializers.Serializer):
    recipe = serializers.DictField()
    available_ingredients = serializers.ListField(child=serializers.CharField(max_length=100), max_length=100)

    def validate_recipe(self, value):
        if not str(value.get("title", "")).strip():
            raise serializers.ValidationError("La receta necesita un título.")
        if not isinstance(value.get("ingredients"), list):
            raise serializers.ValidationError("La receta necesita una lista de ingredientes.")
        return value


class AISuggestionsInputSerializer(serializers.Serializer):
    """Ideas a partir de los ingredientes, de una búsqueda concreta («lasaña») o de ambas cosas."""

    ingredients = serializers.ListField(child=serializers.CharField(max_length=100), required=False, default=list, max_length=60)
    query = serializers.CharField(allow_blank=True, required=False, default="", max_length=120)
    max_results = serializers.IntegerField(min_value=1, max_value=10, default=5)
    meal_type = serializers.ChoiceField(choices=MEAL_TYPES, required=False, allow_blank=True, default="")
    diet = serializers.CharField(allow_blank=True, required=False, default="", max_length=100)
    avoid = serializers.ListField(child=serializers.CharField(max_length=100), required=False, default=list, max_length=30)

    def validate(self, attrs):
        if not attrs["ingredients"] and not attrs["query"].strip():
            raise serializers.ValidationError("Indica ingredientes o escribe qué receta buscas.")
        return attrs


class AIMealPlanInputSerializer(serializers.Serializer):
    goal = serializers.ChoiceField(choices=["mantener el peso", "bajar de peso", "ganar músculo", "comer más sano"], required=False, default="mantener el peso")
    meals = serializers.ListField(
        child=serializers.ChoiceField(choices=["desayuno", "almuerzo", "merienda", "cena"]),
        required=False,
        min_length=2,
        max_length=4,
        default=lambda: ["desayuno", "almuerzo", "merienda", "cena"],
    )
    calories = serializers.IntegerField(required=False, allow_null=True, min_value=1000, max_value=5000, default=None)
    diet = serializers.CharField(allow_blank=True, required=False, default="", max_length=100)
    avoid = serializers.ListField(child=serializers.CharField(max_length=100), required=False, default=list, max_length=30)
    use_pantry = serializers.BooleanField(required=False, default=False)


class MealPlanSerializer(serializers.ModelSerializer):
    class Meta:
        model = MealPlan
        fields = ["id", "title", "options", "days", "notes", "created_at"]
        read_only_fields = fields


class DishSerializer(serializers.ModelSerializer):
    class Meta:
        model = Dish
        fields = [
            "id", "name_es", "name_en", "description", "country", "meal_type", "diets", "ingredients", "steps",
            "calories", "image", "image_credit", "image_license", "reviewed", "source",
        ]
        read_only_fields = fields
