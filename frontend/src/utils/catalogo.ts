import type { CategoriaIngrediente } from '@/types/api'

/** Etiquetas e iconos de las categorías de ingredientes. El orden es el de las listas agrupadas. */
export const CATEGORIAS: {
  valor: Exclude<CategoriaIngrediente, ''>
  etiqueta: string
  icono: string
}[] = [
  { valor: 'verdura', etiqueta: 'Verduras', icono: 'mdi-carrot' },
  { valor: 'fruta', etiqueta: 'Frutas', icono: 'mdi-food-apple' },
  { valor: 'carne', etiqueta: 'Carnes y huevos', icono: 'mdi-food-steak' },
  { valor: 'pescado', etiqueta: 'Pescados y mariscos', icono: 'mdi-fish' },
  { valor: 'lacteo', etiqueta: 'Lácteos', icono: 'mdi-cheese' },
  { valor: 'cereal', etiqueta: 'Cereales y pasta', icono: 'mdi-grain' },
  { valor: 'legumbre', etiqueta: 'Legumbres', icono: 'mdi-seed' },
  { valor: 'especia', etiqueta: 'Especias y básicos', icono: 'mdi-shaker-outline' },
  { valor: 'bebida', etiqueta: 'Bebidas', icono: 'mdi-cup-water' },
  { valor: 'otro', etiqueta: 'Otros', icono: 'mdi-basket-outline' },
]

export function etiquetaCategoria(valor: CategoriaIngrediente): string {
  return CATEGORIAS.find((c) => c.valor === valor)?.etiqueta ?? 'Otros'
}

/** Agrupa elementos por categoría respetando el orden de CATEGORIAS; lo sin categoría va a «Otros». */
export function agruparPorCategoria<T extends { category: CategoriaIngrediente }>(items: T[]) {
  return CATEGORIAS.map((cat) => ({
    ...cat,
    items: items.filter((i) => (i.category || 'otro') === cat.valor),
  })).filter((grupo) => grupo.items.length > 0)
}

/** Sugerencias del autocompletado al añadir ingredientes. */
export const INGREDIENTES_FRECUENTES = [
  'pollo',
  'arroz',
  'ajo',
  'cebolla',
  'tomate',
  'huevo',
  'patata',
  'pasta',
  'zanahoria',
  'pimiento',
  'leche',
  'queso',
  'mantequilla',
  'aceite de oliva',
  'sal',
  'pimienta',
  'limón',
  'atún',
  'ternera',
  'cerdo',
  'salmón',
  'champiñones',
  'espinacas',
  'calabacín',
  'garbanzos',
  'lentejas',
  'harina',
  'azúcar',
  'nata',
  'yogur',
]

/** Categorías de TheMealDB para el filtro de la pantalla de inicio. */
export const CATEGORIAS_RECETA = [
  'Beef',
  'Breakfast',
  'Chicken',
  'Dessert',
  'Goat',
  'Lamb',
  'Miscellaneous',
  'Pasta',
  'Pork',
  'Seafood',
  'Side',
  'Starter',
  'Vegan',
  'Vegetarian',
]
