// Refrescos LATAM catalog — sodas and stores across Latin America.
// Stores and products with descriptive labels that embed their ID for form dropdowns.

export interface CatalogItem {
  id: number;
  name: string; // short name
  desc: string; // description shown in the dropdown (includes the id)
  price?: number; // suggested unit price (soda products in USD)
}

// "Stores" are LATAM countries with distribution centers.
export const STORES: CatalogItem[] = [
  { id: 1, name: "Chile", desc: "1 · Chile" },
  { id: 2, name: "Perú", desc: "2 · Perú" },
  { id: 3, name: "Argentina", desc: "3 · Argentina" },
  { id: 4, name: "México", desc: "4 · México" },
  { id: 5, name: "Colombia", desc: "5 · Colombia" },
  { id: 6, name: "Brasil", desc: "6 · Brasil" },
];

// Refrescos LATAM: iconic sodas across the region (Coca-Cola, local brands, etc.)
export const PRODUCTS: CatalogItem[] = [
  { id: 100, name: "Coca-Cola 2.5L", desc: "100 · Coca-Cola 2.5L", price: 2.99 },
  { id: 205, name: "Inca Kola 2L", desc: "205 · Inca Kola 2L", price: 2.49 },
  { id: 312, name: "Guaraná 1.5L", desc: "312 · Guaraná 1.5L", price: 1.99 },
  { id: 418, name: "Fanta Naranja 1L", desc: "418 · Fanta Naranja 1L", price: 1.49 },
  { id: 523, name: "Sprite Limón 2L", desc: "523 · Sprite Limón 2L", price: 2.49 },
];
