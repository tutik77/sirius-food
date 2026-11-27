"use client";

import { useEffect, useState } from "react";

import { DishCard } from "@/components/DishCard";
import { PUBLIC_API_URL, type MenuItem } from "@/lib/api";

export default function MenuCsrPage() {
  const [items, setItems] = useState<MenuItem[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetch(`${PUBLIC_API_URL}/menu/items`, { cache: "no-store" })
      .then((response) => {
        if (!response.ok) throw new Error(`REST API вернул HTTP ${response.status}`);
        return response.json();
      })
      .then(setItems)
      .catch((e: Error) => setError(e.message));
  }, []);

  return (
    <main className="page-shell csr-page">
      <section className="csr-banner">
        <div>
          <p className="eyebrow eyebrow--light">
            <span className="eyebrow-dot" />
            Client-side rendering
          </p>
          <h1>Меню <em>в браузере</em></h1>
          <p>Сервер отдаёт пустой каркас, блюда загружает JavaScript после гидратации.</p>
        </div>
        <div className="csr-banner__status">
          <strong>{items ? items.length : "…"}</strong>
          <span>{items ? "блюд загружено" : "загрузка"}</span>
          <i />
        </div>
      </section>

      <div className="csr-explainer">
        <span className="csr-explainer__icon" aria-hidden="true">ℹ</span>
        <p>Откройте Ctrl+U: в HTML этой страницы блюд нет. Сравните с <a href="/menu">/menu</a> (SSR).</p>
        {!items && !error && <span className="loading-inline">Загружаем меню…</span>}
        {error && <span className="error-inline">{error}</span>}
      </div>

      {items && (
        <div className="dish-grid csr-grid">
          {items.map((item) => (
            <DishCard key={item.id} item={item} />
          ))}
        </div>
      )}
    </main>
  );
}
