"use client";

import { useState } from "react";

export function AddToCartButton({
  available = true,
}: {
  available?: boolean;
}) {
  const [added, setAdded] = useState(false);

  return (
    <button
      className={`add-button${added ? " add-button--added" : ""}`}
      type="button"
      disabled={!available}
      aria-pressed={added}
      onClick={() => setAdded((value) => !value)}
    >
      <span aria-hidden="true">{!available ? "—" : added ? "✓" : "+"}</span>
      {!available ? "Нет в наличии" : added ? "Добавлено" : "В корзину"}
    </button>
  );
}
