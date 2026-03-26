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
  for (let i = 1; i <= 5; i++) {
    const filled = value >= i;
    const half = !filled && value >= i - 0.5;
    stars.push(
      <span
        key={i}
        className={`material-symbols-outlined ${size} text-primary cursor-pointer hover:scale-110 transition-transform`}
        style={{ fontVariationSettings: `'FILL' ${filled || half ? 1 : 0}` }}
        onClick={() => !readonly && onChange?.(i)}
        onContextMenu={(e) => {
          e.preventDefault();
          if (!readonly) onChange?.(i - 0.5);
        }}
      >
        {half ? "star_half" : "star"}
      </span>
    );
  }

  return <div className="flex gap-1">{stars}</div>;
}
