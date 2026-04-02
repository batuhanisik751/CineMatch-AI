import { useRef, useState } from "react";
import { importRatings } from "../api/ratings";
import type { ImportResponse } from "../api/types";
import Modal from "./Modal";

interface ImportRatingsModalProps {
  isOpen: boolean;
  onClose: () => void;
  userId: number;
  onSuccess: () => void;
}

type Source = "auto" | "letterboxd" | "imdb";
type Step = "select" | "uploading" | "results";

export default function ImportRatingsModal({
  isOpen,
  onClose,
  userId,
  onSuccess,
}: ImportRatingsModalProps) {
  const [step, setStep] = useState<Step>("select");
  const [file, setFile] = useState<File | null>(null);
  const [source, setSource] = useState<Source>("auto");
  const [result, setResult] = useState<ImportResponse | null>(null);
  const [error, setError] = useState("");
  const [showNotFound, setShowNotFound] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const reset = () => {
    setStep("select");
    setFile(null);
    setSource("auto");
    setResult(null);
    setError("");
    setShowNotFound(false);
  };

  const handleClose = () => {
    reset();
    onClose();
  };

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const f = e.target.files?.[0];
    if (f) {
      if (!f.name.endsWith(".csv")) {
        setError("Please select a CSV file.");
        return;
      }
      setFile(f);
      setError("");
    }
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    const f = e.dataTransfer.files[0];
    if (f) {
      if (!f.name.endsWith(".csv")) {
        setError("Please select a CSV file.");
        return;
      }
      setFile(f);
      setError("");
    }
  };

  const handleImport = async () => {
    if (!file) return;
    setStep("uploading");
    setError("");
    try {
      const res = await importRatings(userId, file, source);
      setResult(res);
      setStep("results");
      onSuccess();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Import failed");
      setStep("select");
    }
  };

  return (
    <Modal isOpen={isOpen} title="Import Ratings" onClose={handleClose}>
      {step === "select" && (
        <div className="space-y-5">
          {/* Drop zone */}
          <div
            onClick={() => fileInputRef.current?.click()}
            onDragOver={(e) => e.preventDefault()}
            onDrop={handleDrop}
            className="border-2 border-dashed border-outline-variant/30 rounded-xl p-8 text-center cursor-pointer hover:border-primary/50 hover:bg-primary/5 transition-all"
          >
            <span className="material-symbols-outlined text-4xl text-on-surface-variant/50 mb-2 block">
              upload_file
            </span>
            {file ? (
              <div>
                <p className="text-on-surface font-bold">{file.name}</p>
                <p className="text-on-surface-variant text-sm mt-1">
                  {(file.size / 1024).toFixed(1)} KB
                </p>
              </div>
            ) : (
              <div>
                <p className="text-on-surface-variant font-body">
                  Drop a CSV file here or click to browse
                </p>
                <p className="text-on-surface-variant/50 text-xs mt-1">
                  Supports Letterboxd and IMDb exports
                </p>
              </div>
            )}
            <input
              ref={fileInputRef}
              type="file"
              accept=".csv"
              onChange={handleFileChange}
              className="hidden"
            />
          </div>

          {/* Source selector */}
          <div>
            <p className="text-sm font-bold text-on-surface-variant mb-2">Source Format</p>
            <div className="flex gap-2">
              {(["auto", "letterboxd", "imdb"] as const).map((s) => (
                <button
                  key={s}
                  onClick={() => setSource(s)}
                  className={`px-4 py-2 rounded-full text-sm font-bold transition-all ${
                    source === s
                      ? "bg-primary text-on-primary"
                      : "bg-surface-container-low text-on-surface-variant hover:bg-surface-container"
                  }`}
                >
                  {s === "auto" ? "Auto-detect" : s === "letterboxd" ? "Letterboxd" : "IMDb"}
                </button>
              ))}
            </div>
          </div>

          {error && (
            <div className="flex items-center gap-2 text-error text-sm">
              <span className="material-symbols-outlined text-base">error</span>
              {error}
            </div>
          )}

          <button
            onClick={handleImport}
            disabled={!file}
            className="w-full py-3 rounded-xl font-bold text-sm transition-all bg-primary text-on-primary hover:bg-primary/90 disabled:opacity-40 disabled:cursor-not-allowed"
          >
            Import Ratings
          </button>
        </div>
      )}

      {step === "uploading" && (
        <div className="flex flex-col items-center gap-4 py-8">
          <div className="w-12 h-12 border-4 border-primary-container/20 border-t-primary-container rounded-full animate-spin" />
          <p className="text-on-surface-variant font-body">Importing ratings...</p>
        </div>
      )}

      {step === "results" && result && (
        <div className="space-y-5">
          {/* Summary counts */}
          <div className="grid grid-cols-3 gap-3">
            <div className="p-4 rounded-xl bg-surface-container-low text-center">
              <p className="text-2xl font-headline font-black text-primary">{result.imported}</p>
              <p className="text-xs text-on-surface-variant mt-1">Imported</p>
            </div>
            <div className="p-4 rounded-xl bg-surface-container-low text-center">
              <p className="text-2xl font-headline font-black text-tertiary">{result.updated}</p>
              <p className="text-xs text-on-surface-variant mt-1">Updated</p>
            </div>
            <div className="p-4 rounded-xl bg-surface-container-low text-center">
              <p className="text-2xl font-headline font-black text-on-surface-variant/50">{result.not_found}</p>
              <p className="text-xs text-on-surface-variant mt-1">Not Found</p>
            </div>
          </div>

          <p className="text-sm text-on-surface-variant">
            Source detected: <span className="font-bold text-on-surface capitalize">{result.source}</span>
            {" \u00b7 "}
            {result.total_rows} total rows processed
          </p>

          {/* Not-found expandable list */}
          {result.not_found > 0 && (
            <div>
              <button
                onClick={() => setShowNotFound(!showNotFound)}
                className="flex items-center gap-1 text-sm text-on-surface-variant hover:text-on-surface transition-colors"
              >
                <span className="material-symbols-outlined text-base">
                  {showNotFound ? "expand_less" : "expand_more"}
                </span>
                {showNotFound ? "Hide" : "Show"} unmatched movies ({result.not_found})
              </button>
              {showNotFound && (
                <div className="mt-2 max-h-40 overflow-y-auto space-y-1">
                  {result.results
                    .filter((r) => r.status === "not_found")
                    .map((r, i) => (
                      <p key={i} className="text-xs text-on-surface-variant/70 py-1 px-2 rounded bg-surface-container-low">
                        {r.title}{r.year ? ` (${r.year})` : ""}
                      </p>
                    ))}
                </div>
              )}
            </div>
          )}

          <button
            onClick={handleClose}
            className="w-full py-3 rounded-xl font-bold text-sm bg-primary text-on-primary hover:bg-primary/90 transition-all"
          >
            Done
          </button>
        </div>
      )}
    </Modal>
  );
}
