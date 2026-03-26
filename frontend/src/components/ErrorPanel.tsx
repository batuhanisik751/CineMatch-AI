interface Props {
  message: string;
  onRetry?: () => void;
}

export default function ErrorPanel({ message, onRetry }: Props) {
  return (
    <div className="max-w-2xl mx-auto glass-panel p-8 rounded-xl border border-secondary-container/30">
      <div className="flex items-start gap-4">
        <div className="w-12 h-12 rounded-full bg-secondary-container/20 flex items-center justify-center flex-shrink-0">
          <span className="material-symbols-outlined text-secondary">error</span>
        </div>
        <div>
          <h4 className="text-lg font-headline font-bold text-secondary mb-1">
            Something went wrong
          </h4>
          <p className="text-on-surface-variant text-sm mb-4">{message}</p>
          {onRetry && (
            <button
              onClick={onRetry}
              className="bg-secondary-container text-on-secondary-container px-6 py-2 rounded font-bold text-xs uppercase tracking-widest hover:brightness-110 transition-all"
            >
              Retry
            </button>
          )}
        </div>
      </div>
    </div>
  );
}
