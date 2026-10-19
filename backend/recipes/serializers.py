from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer

from .models import FavoriteRecipe, Ingredient, RecipeCache, ShoppingListItem
from .normalization import normalize_name

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
    recipe = RecipeCacheSerializer(read_only=True)

    class Meta:
        model = FavoriteRecipe
        fields = ["id", "recipe", "notes", "created_at"]
        read_only_fields = ["id", "recipe", "created_at"]


class FavoriteCreateSerializer(serializers.Serializer):
    external_id = serializers.CharField(max_length=50)
    notes = serializers.CharField(allow_blank=True, required=False, default="")


class SuggestionsQuerySerializer(serializers.Serializer):
    ingredients = serializers.CharField(required=False, allow_blank=True, default="")
    category = serializers.CharField(required=False, allow_blank=True, default="")
    max_missing = serializers.IntegerField(required=False, min_value=0, allow_null=True, default=None)
    search = serializers.CharField(required=False, allow_blank=True, default="")


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
    ingredients = serializers.ListField(child=serializers.CharField(max_length=100), min_length=1, max_length=60)
    max_results = serializers.IntegerField(min_value=1, max_value=10, default=5)
    diet = serializers.CharField(allow_blank=True, required=False, default="", max_length=100)
    avoid = serializers.ListField(child=serializers.CharField(max_length=100), required=False, default=list, max_length=30)
