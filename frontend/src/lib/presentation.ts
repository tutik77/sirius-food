import type { MenuItem } from "@/lib/api";

/**
 * Детерминированный подбор оформления карточки: одна и та же категория всегда
 * получает один и тот же тон и эмодзи. Работает с любыми данными бэкенда,
 * поэтому кит не зависит от конкретных названий блюд.
 */

const TONES = [
  "tomato", "chili", "cream", "gold", "orange", "rose", "sea", "spice",
  "lime", "butter", "leaf", "mint", "berry", "coffee", "citrus", "latte",
  "espresso", "smoothie", "pastry", "honey", "sage",
];

const EMOJI = [
  "🍕", "🍔", "🍣", "🍜", "🍝", "🥗", "🍰", "☕", "🥐", "🥞",
  "🍽️", "🥪", "🍲", "🧀", "🍤", "🥙", "🍩", "🧃", "🍮", "🥧",
];

function hash(text: string): number {
  let h = 0;
  for (const ch of text) {
    h = (h * 31 + ch.charCodeAt(0)) >>> 0;
  }
  return h;
}

export type DishPresentation = {
  emoji: string;
  tone: string;
};

export function presentDish(item: MenuItem): DishPresentation {
  const key = item.category ?? item.name;
  const h = hash(key);
  return {
    emoji: EMOJI[h % EMOJI.length],
    tone: TONES[h % TONES.length],
  };
}
