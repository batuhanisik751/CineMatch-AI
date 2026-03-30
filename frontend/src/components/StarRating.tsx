interface Props {
  value: number;
  onChange?: (val: number) => void;
  readonly?: boolean;
  size?: string;
}

export default function StarRating({
  value,
  onChange,
  readonly = false,
  size = "text-2xl",
}: Props) {
  const stars = [];
  for (let i = 1; i <= 10; i++) {
    const filled = value >= i;
    stars.push(
      <span
        key={i}
        className={`material-symbols-outlined ${size} text-primary cursor-pointer hover:scale-110 transition-transform`}
        style={{ fontVariationSettings: `'FILL' ${filled ? 1 : 0}` }}
        onClick={() => !readonly && onChange?.(i)}
      >
        star
      </span>
    );
  }

  return <div className="flex gap-0.5">{stars}</div>;
}
