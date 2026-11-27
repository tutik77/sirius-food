import type { Metadata } from "next";

import { DishCard } from "@/components/DishCard";
import { getMenuItems } from "@/lib/api";

export const revalidate = 60;

const description = "Меню кампуса «Сириус.Еды»: блюда, цены и наличие. HTML собирается на сервере.";

export const metadata: Metadata = {
  title: "Меню",
  description,
  openGraph: { title: "Меню · Сириус.Еда", description, type: "website", url: "/menu" },
};

export default async function MenuPage() {
  const items = await getMenuItems();

  return (
    <main className="page-shell">
      <section className="menu-section">
        <div className="section-heading">
          <div>
            <p className="eyebrow">
              <span className="eyebrow-dot" />
              Server-side rendering · ISR 60 с
            </p>
            <h2>Меню</h2>
            <p className="section-description">Данные получены из REST API на сервере Next.js и уже лежат в HTML.</p>
          </div>
          <div className="menu-count">
            <strong>{items.length}</strong>
            <span>блюд<br />в меню</span>
          </div>
        </div>

        {items.length === 0 ? (
          <section className="empty-state">
            <span aria-hidden="true">🍽️</span>
            <h3>Меню пока пустое</h3>
            <p>Добавьте блюда через POST /menu/items или scripts/seed_menu.py.</p>
          </section>
        ) : (
          <div className="dish-grid">
            {items.map((item) => (
              <DishCard key={item.id} item={item} />
            ))}
          </div>
        )}
      </section>
    </main>
  );
}
