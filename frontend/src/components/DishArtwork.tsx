export function DishArtwork({
  emoji,
  tone,
  category,
  compact = false,
}: {
  emoji: string;
  tone: string;
  category: string;
  compact?: boolean;
}) {
  return (
    <div
      className={`dish-art dish-art--${tone}${compact ? " dish-art--compact" : ""}`}
      aria-hidden="true"
    >
      <span className="dish-art__spark dish-art__spark--one">✳</span>
      <span className="dish-art__spark dish-art__spark--two">✦</span>
      <span className="dish-art__category">{category}</span>
      <span className="dish-art__plate"><span>{emoji}</span></span>
      <span className="dish-art__shadow" />
    </div>
  );
}
