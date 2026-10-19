"""Vistas de la API. Solo validan la petición y delegan en services/."""

from django.db import IntegrityError, transaction
from rest_framework import mixins, status, viewsets
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.exceptions import NotFound, ValidationError
from rest_framework.generics import CreateAPIView
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.views import APIView
from rest_framework_simplejwt.views import TokenObtainPairView

from .models import FavoriteRecipe, Ingredient, ShoppingListItem
from .normalization import normalize_name
from .serializers import (
    AIRecipeInputSerializer,
    AISuggestionsInputSerializer,
    FavoriteCreateSerializer,
    FavoriteSerializer,
    IngredientSerializer,
    LoginSerializer,
    RegisterSerializer,
    ShoppingListItemSerializer,
    SuggestionsQuerySerializer,
    UserSerializer,
)
from .services import ai as ai_service
from .services.images import attach_images
from .catalog import to_english
from .services.localization import localize_recipe, localize_summaries
from .services.matching import calculate_match, with_spanish_names
from .services.recipes import get_recipe, save_recipe
from .services.suggestions import build_suggestions, parse_ingredients
from .services.translation import translate_strings


@api_view(["GET"])
@permission_classes([AllowAny])
def health(request):
    """Comprobación de que la API responde. No toca la base de datos ni servicios externos."""
    return Response({"status": "ok"})


# --- Autenticación ---


class RegisterView(CreateAPIView):
    serializer_class = RegisterSerializer
    permission_classes = [AllowAny]


class LoginView(TokenObtainPairView):
    serializer_class = LoginSerializer


class MeView(APIView):
    def get(self, request):
        return Response(UserSerializer(request.user).data)


# --- Despensa ---


class OwnedViewSet(viewsets.GenericViewSet):
    """Cada usuario solo ve y modifica sus propios datos."""

    def get_queryset(self):
        return self.queryset.model.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)


class IngredientViewSet(
    OwnedViewSet, mixins.ListModelMixin, mixins.CreateModelMixin, mixins.UpdateModelMixin, mixins.DestroyModelMixin
):
    queryset = Ingredient.objects.all()
    serializer_class = IngredientSerializer
    http_method_names = ["get", "post", "patch", "delete", "head", "options"]


# --- Lista de la compra ---


class ShoppingListViewSet(
    OwnedViewSet, mixins.ListModelMixin, mixins.CreateModelMixin, mixins.UpdateModelMixin, mixins.DestroyModelMixin
):
    queryset = ShoppingListItem.objects.all()
    serializer_class = ShoppingListItemSerializer
    http_method_names = ["get", "post", "patch", "delete", "head", "options"]

    def create(self, request, *args, **kwargs):
        """Si el producto ya está pendiente en la lista no se duplica: se actualiza la cantidad."""
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        clave = normalize_name(serializer.validated_data["name"])
        existente = self.get_queryset().filter(normalized_name=clave, bought=False).first()
        if existente:
            cantidad = serializer.validated_data.get("quantity")
            if cantidad:
                existente.quantity = cantidad
                existente.save(update_fields=["quantity"])
            return Response(self.get_serializer(existente).data, status=status.HTTP_200_OK)
        self.perform_create(serializer)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    @action(detail=False, methods=["post"], url_path="clear-bought")
    def clear_bought(self, request):
        eliminados, _ = self.get_queryset().filter(bought=True).delete()
        return Response({"deleted": eliminados})


# --- Recetas ---


class RecipeSuggestionsView(APIView):
    def get(self, request):
        consulta = SuggestionsQuerySerializer(data=request.query_params)
        consulta.is_valid(raise_exception=True)
        datos = consulta.validated_data
        pantry = parse_ingredients(datos["ingredients"])
        if not pantry and not datos["search"].strip():
            raise ValidationError({"ingredients": "Indica al menos un ingrediente."})
        busqueda = datos["search"].strip()
        if busqueda and datos["lang"] == "es":
            # TheMealDB busca por título en inglés: la búsqueda en español se traduce primero
            traducida = translate_strings([busqueda], "es", "en").get(busqueda)
            busqueda = traducida or to_english(busqueda)
        resultado = build_suggestions(
            pantry,
            category=datos["category"],
            max_missing=datos["max_missing"],
            search=busqueda,
        )
        resultado["results"] = localize_summaries(resultado["results"], datos["lang"])
        return Response(resultado)


class RecipeDetailView(APIView):
    """Receta normalizada. Con `?ingredients=` añade cuánto coincide con la despensa."""

    def get(self, request, external_id):
        receta = get_recipe(external_id, save=True)
        if receta is None:
            raise NotFound("No se encontró la receta.")
        pantry = parse_ingredients(request.query_params.get("ingredients", ""))
        coincidencia = None
        if pantry:
            coincidencia = calculate_match(pantry, receta["ingredients"])
            coincidencia["missing"] = with_spanish_names(receta["ingredients"], coincidencia["missing_ingredients"])
        lang = request.query_params.get("lang", "")
        if lang:
            return Response(localize_recipe(receta, lang, coincidencia))
        respuesta = dict(receta)
        if coincidencia is not None:
            respuesta["match"] = coincidencia
        return Response(respuesta)


# --- Favoritos ---


class FavoriteViewSet(
    OwnedViewSet, mixins.ListModelMixin, mixins.CreateModelMixin, mixins.UpdateModelMixin, mixins.DestroyModelMixin
):
    queryset = FavoriteRecipe.objects.select_related("recipe")
    serializer_class = FavoriteSerializer
    http_method_names = ["get", "post", "patch", "delete", "head", "options"]

    def create(self, request, *args, **kwargs):
        entrada = FavoriteCreateSerializer(data=request.data)
        entrada.is_valid(raise_exception=True)
        receta = get_recipe(entrada.validated_data["external_id"], save=False)
        if receta is None:
            raise NotFound("No se encontró la receta.")
        guardada = save_recipe(receta)
        try:
            with transaction.atomic():
                favorito = FavoriteRecipe.objects.create(
                    user=request.user, recipe=guardada, notes=entrada.validated_data["notes"]
                )
        except IntegrityError:
            raise ValidationError({"detail": "Esta receta ya está en tus favoritos."}) from None
        return Response(FavoriteSerializer(favorito, context={"request": request}).data, status=status.HTTP_201_CREATED)


# --- IA ---


class AIBaseView(APIView):
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "ai"


class AISuggestionsView(AIBaseView):
    def post(self, request):
        entrada = AISuggestionsInputSerializer(data=request.data)
        entrada.is_valid(raise_exception=True)
        d = entrada.validated_data
        servicio = ai_service.get_ai_service()
        resultado = servicio.suggest_recipes(
            d["ingredients"],
            {"max_results": d["max_results"], "diet": d["diet"], "avoid": d["avoid"], "meal_type": d["meal_type"]},
        )
        # Foto orientativa de Wikipedia cuando el plato tiene artículo propio (si no, `image` es null)
        resultado["suggestions"] = attach_images(resultado["suggestions"])
        return Response(resultado)


class AIAdaptRecipeView(AIBaseView):
    def post(self, request):
        entrada = AIRecipeInputSerializer(data=request.data)
        entrada.is_valid(raise_exception=True)
        resultado = ai_service.get_ai_service().adapt_recipe(
            entrada.validated_data["recipe"], entrada.validated_data["available_ingredients"]
        )
        return Response(resultado)


class AIShoppingListView(AIBaseView):
    def post(self, request):
        entrada = AIRecipeInputSerializer(data=request.data)
        entrada.is_valid(raise_exception=True)
        resultado = ai_service.get_ai_service().generate_shopping_list(
            entrada.validated_data["recipe"], entrada.validated_data["available_ingredients"]
        )
        return Response(resultado)

