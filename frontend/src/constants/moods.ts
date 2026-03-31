export const MOOD_PRESETS = [
  {
    label: "Feel-Good",
    query: "heartwarming uplifting feel-good movies that make you smile",
    icon: "sentiment_very_satisfied",
  },
  {
    label: "Mind-Bending",
    query: "mind-bending complex twist psychological thriller",
    icon: "psychology",
  },
  {
    label: "Dark & Gritty",
    query: "dark gritty intense crime drama noir",
    icon: "dark_mode",
  },
  {
    label: "Lighthearted",
    query: "lighthearted fun comedy entertaining easy watch",
    icon: "sunny",
  },
  {
    label: "Epic Adventure",
    query: "epic adventure grand journey quest fantasy action",
    icon: "landscape",
  },
  {
    label: "Cozy Night In",
    query: "cozy romantic comfort movie relaxing charming",
    icon: "local_fire_department",
  },
  {
    label: "Edge of Your Seat",
    query: "suspenseful tense thriller edge of your seat gripping",
    icon: "bolt",
  },
  {
    label: "Tearjerker",
    query: "emotional tearjerker sad moving drama that makes you cry",
    icon: "water_drop",
  },
  {
    label: "Nostalgic",
    query: "nostalgic retro classic beloved timeless movies from the past",
    icon: "hourglass_bottom",
  },
] as const;

export type MoodPreset = (typeof MOOD_PRESETS)[number];
