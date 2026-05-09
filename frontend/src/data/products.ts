import type { Product } from "../api/types";

export const demoProducts: Product[] = [
  {
    id: "shoe_123",
    name: "StormRunner GTX",
    price: 139,
    description: "Waterproof trail running shoe with grippy lugs and wide-fit support.",
    waterproof: true,
    delivery_promise: "Arrives by Friday",
    variants: [
      { id: "shoe_123_105_wide", label: "10.5 Wide", size: "10.5", fit: "wide", in_stock: true },
      { id: "shoe_123_105_regular", label: "10.5 Regular", size: "10.5", fit: "regular", in_stock: true }
    ]
  },
  {
    id: "shoe_456",
    name: "RidgeLite Flow",
    price: 119,
    description: "Lightweight trail shoe for dry conditions and fast daily runs.",
    waterproof: false,
    delivery_promise: "Arrives next week",
    variants: [
      { id: "shoe_456_105_wide", label: "10.5 Wide", size: "10.5", fit: "wide", in_stock: true }
    ]
  }
];
