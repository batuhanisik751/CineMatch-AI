export default function LoadingSpinner({ text = "Loading..." }: { text?: string }) {
  return (
    <div className="flex flex-col items-center justify-center py-20 space-y-4">
      <div className="w-12 h-12 border-4 border-primary-container/20 border-t-primary-container rounded-full animate-spin" />
      <p className="text-on-surface-variant font-label text-sm animate-pulse">{text}</p>
    </div>
  );
}
