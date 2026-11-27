import Link from "next/link";

import { formatPrice, type MenuItem } from "@/lib/api";
import { presentDish } from "@/lib/presentation";
import { AddToCartButton } from "@/components/AddToCartButton";
import { DishArtwork } from "@/components/DishArtwork";

export function DishCard({ item }: { item: MenuItem }) {
  const art = presentDish(item);
  const category = item.category ?? "Меню";

  return (
    <article className="dish-card">
      <Link
        className="dish-card__art-link"
        href={`/menu/${item.id}`}
        aria-label={`Подробнее: ${item.name}`}
      >
        <DishArtwork emoji={art.emoji} tone={art.tone} category={category} />
      </Link>
      <div className="dish-card__content">
        <div className="dish-card__meta">
          <span>{category}</span>
          <span className="dish-card__id">#{item.id}</span>
        </div>
        <Link href={`/menu/${item.id}`} className="dish-card__title-link">
          <h3 className="dish-card__title">{item.name}</h3>
        </Link>
        <div className="dish-card__bottom">
          <strong className="dish-card__price">{formatPrice(item.price)}</strong>
          <AddToCartButton available={item.is_available !== false} />
        </div>
      </div>
    </article>
  );
}
