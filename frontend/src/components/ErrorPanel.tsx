const FRIENDLY_MESSAGES: Record<number, string> = {
  400: "The request could not be processed. Please check your input and try again.",
  403: "You don't have permission to access this resource.",
  404: "The page or item you're looking for could not be found.",
  408: "The request timed out. Please try again.",
  413: "The file you uploaded is too large.",
  422: "The data provided is invalid. Please check and try again.",
  429: "Too many requests. Please slow down and try again shortly.",
  500: "Something unexpected happened on our end. Please try again later.",
  502: "Our servers are having trouble right now. Please try again later.",
  503: "This service is temporarily unavailable. Please try again later.",
};

interface Props {
  message: string;
  statusCode?: number;
  onRetry?: () => void;
}

export default function ErrorPanel({ message, statusCode, onRetry }: Props) {
  const displayMessage =
    message ||
    (statusCode ? FRIENDLY_MESSAGES[statusCode] : undefined) ||
    "An unexpected error occurred. Please try again.";

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
          <p className="text-on-surface-variant text-sm mb-4">{displayMessage}</p>
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
