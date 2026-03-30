import { MOOD_PRESETS, type MoodPreset } from "../constants/moods";

interface Props {
  onSelect: (mood: MoodPreset) => void;
  activeMood: string | null;
  loading: boolean;
}

export default function MoodPills({ onSelect, activeMood, loading }: Props) {
  return (
    <div className="flex flex-wrap justify-center gap-3 mt-8">
      {MOOD_PRESETS.map((mood) => {
        const isActive = activeMood === mood.label;
        return (
          <button
            key={mood.label}
            onClick={() => onSelect(mood)}
            disabled={loading && !isActive}
            className={`flex items-center gap-2 px-5 py-2.5 rounded-full font-label text-sm font-bold tracking-wide transition-all duration-300 border ${
              isActive
                ? "bg-primary text-on-primary border-primary shadow-[0_0_20px_rgba(255,193,7,0.3)]"
                : "bg-surface-container-low text-on-surface-variant border-outline-variant/20 hover:bg-surface-container hover:border-outline-variant/40"
            } ${loading && !isActive ? "opacity-40 cursor-not-allowed" : "cursor-pointer"}`}
          >
            <span className="material-symbols-outlined text-[18px]">
              {mood.icon}
            </span>
            {mood.label}
          </button>
        );
      })}
    </div>
  );
}
