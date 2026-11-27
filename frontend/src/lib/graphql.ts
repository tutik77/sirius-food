/**
 * ОПЦИОНАЛЬНО. Этот клиент нужен только для бонусного задания на 9 баллов
 * (вариант Б: GraphQL BFF). В базовой части он не используется.
 *
 * Чтобы переключить витрину на GraphQL:
 *  1. Реализуйте GraphQL BFF на бэкенде (эндпоинт /graphql).
 *  2. Замените импорты из @/lib/api на функции из этого файла.
 */

import type { MenuItem } from "@/lib/api";

export const GRAPHQL_URL =
  process.env.NEXT_PUBLIC_GRAPHQL_URL ?? "http://127.0.0.1:8000/graphql";

type GraphQLResponse<T> = {
  data?: T;
  errors?: { message: string }[];
};

async function graphqlRequest<T>(
  query: string,
  variables: Record<string, unknown> = {},
): Promise<T> {
  const response = await fetch(GRAPHQL_URL, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Accept: "application/json",
    },
    body: JSON.stringify({ query, variables }),
    next: { revalidate: 60 },
  });

  if (!response.ok) {
    throw new Error(`GraphQL BFF вернул HTTP ${response.status}`);
  }

  const payload = (await response.json()) as GraphQLResponse<T>;
  if (payload.errors?.length) {
    throw new Error(payload.errors.map((error) => error.message).join("; "));
  }
  if (!payload.data) {
    throw new Error("GraphQL BFF вернул пустой ответ");
  }
  return payload.data;
}

const MENU_QUERY = /* GraphQL */ `
  query Menu {
    menu {
      id
      name
      price
    }
  }
`;

const MENU_ITEM_QUERY = /* GraphQL */ `
  query MenuItem($id: Int!) {
    menuItem(id: $id) {
      id
      name
      price
    }
  }
`;

export async function getMenuItemsGraphQL(): Promise<MenuItem[]> {
  const data = await graphqlRequest<{ menu: MenuItem[] }>(MENU_QUERY);
  return data.menu;
}

export async function getMenuItemGraphQL(
  id: number | string,
): Promise<MenuItem | null> {
  const numericId = Number(id);
  if (!Number.isInteger(numericId) || numericId <= 0) return null;

  const data = await graphqlRequest<{ menuItem: MenuItem | null }>(
    MENU_ITEM_QUERY,
    { id: numericId },
  );
  return data.menuItem;
}
