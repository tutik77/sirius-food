import type { Metadata } from "next";
import Link from "next/link";
import { notFound } from "next/navigation";

import { AddToCartButton } from "@/components/AddToCartButton";
import { DishArtwork } from "@/components/DishArtwork";
import { formatPrice, getMenuItem } from "@/lib/api";
import { presentDish } from "@/lib/presentation";

export const revalidate = 60;

type PageProps = {
  params: Promise<{ id: string }>;
};

export async function generateMetadata({ params }: PageProps): Promise<Metadata> {
  const { id } = await params;
  const item = await getMenuItem(id);
  if (!item) {
    return { title: "Блюдо не найдено" };
  }

  const description = `${item.name} за ${formatPrice(item.price)} в столовой «Сириус.Еды».`;
  return {
    title: item.name,
    description,
    openGraph: { title: `${item.name} · Сириус.Еда`, description, type: "article", url: `/menu/${item.id}` },
  };
}

export default async function MenuItemPage({ params }: PageProps) {
  const { id } = await params;
  const item = await getMenuItem(id);
  if (!item) notFound();

  const art = presentDish(item);
  const category = item.category ?? "Меню";
  const available = item.is_available !== false;

  return (
    <main className="page-shell detail-page">
      <div className="breadcrumbs">
        <Link href="/menu">Меню</Link>
        <span aria-hidden="true">/</span>
        <span>{item.name}</span>
      </div>

      <article className="detail-card">
        <div className="detail-card__art">
          <DishArtwork emoji={art.emoji} tone={art.tone} category={category} />
        </div>
        <div className="detail-card__info">
          <p className="eyebrow">
            <span className="eyebrow-dot" />
            {category} · #{item.id}
          </p>
          <h1>{item.name}</h1>
          <p className="detail-card__description">
            {available ? "Есть в наличии, можно заказать прямо сейчас." : "Сейчас нет в наличии."}
          </p>
          <div className="detail-price-row">
            <div>
              <span className="detail-price-label">Цена</span>
              <strong className="detail-price">{formatPrice(item.price)}</strong>
            </div>
          </div>
          <AddToCartButton available={available} />
        </div>
      </article>

      <Link href="/menu" className="back-link">← Назад к меню</Link>
    </main>
  );
}
