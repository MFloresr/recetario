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

from .models import FavoriteRecipe, Ingredient, MealPlan, RecipeCache, ShoppingListItem
from .normalization import normalize_name
from .serializers import (
    AIRecipeInputSerializer,
    AIMealPlanInputSerializer,
    AISuggestionsInputSerializer,
    DeleteAccountSerializer,
    FavoriteCreateSerializer,
    FavoriteSerializer,
    IngredientSerializer,
    LoginSerializer,
    MealPlanSerializer,
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
from .services.recipes import AI_SOURCE, get_recipe, is_ai_recipe_of, save_ai_recipe, save_recipe, save_suggestion_for_user
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
    throttle_classes = [ScopedRateThrottle]  # el registro es público: límite por IP
    throttle_scope = "register"


class LoginView(TokenObtainPairView):
    serializer_class = LoginSerializer


class MeView(APIView):
    def get(self, request):
        return Response(UserSerializer(request.user).data)

    def delete(self, request):
        """Borra la cuenta y todos sus datos (despensa, lista de la compra y favoritos) tras confirmar la contraseña."""
        entrada = DeleteAccountSerializer(data=request.data, context={"request": request})
        entrada.is_valid(raise_exception=True)
        RecipeCache.objects.filter(external_id__startswith=f"ai-{request.user.id}-").delete()  # sus recetas de la IA
        request.user.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


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
        propia_ia = external_id.startswith("ai-")
        if propia_ia and not is_ai_recipe_of(external_id, request.user.id):
            raise NotFound("No se encontró la receta.")  # las recetas de la IA son de su dueño
        receta = get_recipe(external_id, save=not propia_ia)
        if receta is None:
            raise NotFound("No se encontró la receta.")
        pantry = parse_ingredients(request.query_params.get("ingredients", ""))
        coincidencia = None
        if pantry and propia_ia:
            coincidencia = calculate_match(pantry, receta["ingredients"], translate=False)
            coincidencia["missing"] = [
                {**i, "name_es": i["ingredient"]} for i in receta["ingredients"] if i["ingredient"] in coincidencia["missing_ingredients"]
            ]
        elif pantry:
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

    def perform_destroy(self, instance):
        # Una receta de la IA solo existe para su dueño: al quitarla de favoritos se borra del todo
        if instance.recipe.source == AI_SOURCE:
            instance.recipe.delete()
        else:
            instance.delete()

    def create(self, request, *args, **kwargs):
        entrada = FavoriteCreateSerializer(data=request.data)
        entrada.is_valid(raise_exception=True)
        if entrada.validated_data.get("recipe"):
            guardada = save_ai_recipe(request.user.id, entrada.validated_data["recipe"])
        else:
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
            {"max_results": d["max_results"], "diet": d["diet"], "avoid": d["avoid"], "meal_type": d["meal_type"], "query": d["query"]},
        )
        # Foto orientativa de Wikipedia cuando el plato tiene artículo propio (si no, `image` es null)
        resultado["suggestions"] = attach_images(resultado["suggestions"])
        # Toda receta generada queda guardada en el recetario del usuario para verla otro día
        for sugerencia in resultado["suggestions"]:
            sugerencia["external_id"] = save_suggestion_for_user(request.user, sugerencia)
            sugerencia["saved"] = sugerencia["external_id"] is not None
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



MAX_PLANES = 5  # se conservan los últimos planes de cada usuario


class AIMealPlanView(AIBaseView):
    """Genera la dieta de la semana, la guarda y la devuelve."""

    def post(self, request):
        entrada = AIMealPlanInputSerializer(data=request.data)
        entrada.is_valid(raise_exception=True)
        d = entrada.validated_data
        despensa = []
        if d["use_pantry"]:
            despensa = list(Ingredient.objects.filter(user=request.user, in_pantry=True).values_list("name", flat=True)[:40])
        resultado = ai_service.get_ai_service().generate_meal_plan({**d, "pantry": despensa})
        opciones = {k: d[k] for k in ("goal", "meals", "calories", "diet", "avoid", "use_pantry")}
        with transaction.atomic():
            plan = MealPlan.objects.create(
                user=request.user,
                title=resultado.get("title") or "Dieta de la semana",
                options=opciones,
                days=resultado["days"],
                notes=resultado.get("notes", ""),
            )
            antiguos = MealPlan.objects.filter(user=request.user).values_list("id", flat=True)[MAX_PLANES:]
            MealPlan.objects.filter(id__in=list(antiguos)).delete()
        return Response(MealPlanSerializer(plan).data, status=status.HTTP_201_CREATED)


class MealPlanViewSet(OwnedViewSet, mixins.ListModelMixin, mixins.RetrieveModelMixin, mixins.DestroyModelMixin):
    queryset = MealPlan.objects.all()
    serializer_class = MealPlanSerializer
