/**
 * REST-клиент бэкенда «Сириус.Еда».
 *
 * Адрес API берётся из окружения (.env.local), поэтому кит работает с любым
 * бэкендом: поменяйте API_URL / NEXT_PUBLIC_API_URL — и код трогать не нужно.
 *
 * Базовый контракт (Приложение А методички):
 *   GET /menu/items      — список блюд;
 *   GET /menu/items/{id} — одно блюдо или 404.
 */

// Серверный адрес API. Переменные без NEXT_PUBLIC видны только на сервере
// Next.js и не попадают в клиентский бандл.
export const API_URL =
  process.env.API_URL ?? process.env.NEXT_PUBLIC_API_URL ?? "http://127.0.0.1:8000";

// Адрес API, доступный в браузере. Нужен только CSR-страницам (задание на 10 баллов).
export const PUBLIC_API_URL = process.env.NEXT_PUBLIC_API_URL ?? API_URL;

const REVALIDATE_SECONDS = 60;

export type MenuItem = {
  id: number;
  name: string;
  price: number;
  is_available?: boolean;
  category?: string | null;
};

export async function getMenuItems(): Promise<MenuItem[]> {
  const response = await fetch(`${API_URL}/menu/items`, {
    next: { revalidate: REVALIDATE_SECONDS },
  });
  if (!response.ok) {
    throw new Error(`REST API вернул HTTP ${response.status}`);
  }
  return response.json();
}

export async function getMenuItem(id: number | string): Promise<MenuItem | null> {
  const numericId = Number(id);
  if (!Number.isInteger(numericId) || numericId <= 0) return null;

  const response = await fetch(`${API_URL}/menu/items/${numericId}`, {
    next: { revalidate: REVALIDATE_SECONDS },
  });
  if (response.status === 404) return null;
  if (!response.ok) {
    throw new Error(`REST API вернул HTTP ${response.status}`);
  }
  return response.json();
}

export function formatPrice(price: number): string {
  return new Intl.NumberFormat("ru-RU", {
    style: "currency",
    currency: "RUB",
    maximumFractionDigits: 0,
  }).format(price);
}
