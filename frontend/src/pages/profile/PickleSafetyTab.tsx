import { useEffect, useState } from "react";
import { getPickleSafetyStatus } from "../../api/pickleSafety";
import type { PickleArtifactStatus, PickleSafetyResponse } from "../../api/types";

const STATUS_CONFIG: Record<
  PickleArtifactStatus["status"],
  { color: string; bg: string; icon: string; label: string }
> = {
  verified: {
    color: "text-green-400",
    bg: "bg-green-500/15",
    icon: "check_circle",
    label: "Verified",
  },
  mismatch: {
    color: "text-red-400",
    bg: "bg-red-500/15",
    icon: "cancel",
    label: "Mismatch",
  },
  missing_checksum: {
    color: "text-amber-400",
    bg: "bg-amber-500/15",
    icon: "warning",
    label: "No Checksum",
  },
  missing_artifact: {
    color: "text-gray-400",
    bg: "bg-gray-500/15",
    icon: "help_outline",
    label: "Missing File",
  },
};

function StatusBadge({ status }: { status: PickleArtifactStatus["status"] }) {
  const cfg = STATUS_CONFIG[status];
  return (
    <span
      className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium ${cfg.bg} ${cfg.color}`}
    >
      <span className="material-symbols-outlined text-xs">{cfg.icon}</span>
      {cfg.label}
    </span>
  );
}

function StatRow({ label, value }: { label: string; value: string | number }) {
  return (
    <div className="flex justify-between items-center py-2 border-b border-white/5 last:border-0">
      <span className="text-sm text-on-surface-variant">{label}</span>
      <span className="text-sm font-medium text-on-surface font-mono">{value}</span>
    </div>
  );
}

function formatBytes(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

function truncateHash(hash: string | null): string {
  if (!hash) return "N/A";
  return `${hash.slice(0, 16)}...`;
}

export default function PickleSafetyTab() {
  const [data, setData] = useState<PickleSafetyResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  function fetchData() {
    setLoading(true);
    setError("");
    getPickleSafetyStatus()
      .then(setData)
      .catch(() => setError("Failed to load pickle safety status"))
      .finally(() => setLoading(false));
  }

  useEffect(() => {
    fetchData();
  }, []);

  return (
    <>
      <header className="mb-10">
        <h1 className="text-5xl md:text-6xl font-extrabold font-headline text-on-surface">
          Pickle Integrity
        </h1>
        <p className="mt-3 text-on-surface-variant text-lg">
          SHA-256 checksum verification status for ML model artifacts
        </p>
      </header>

      {/* Refresh button */}
      <div className="mb-6 flex justify-end">
        <button
          onClick={fetchData}
          disabled={loading}
          className="inline-flex items-center gap-2 px-4 py-2 rounded-lg bg-surface-container text-on-surface text-sm border border-white/10 hover:border-primary/40 transition-colors disabled:opacity-30"
        >
          <span className={`material-symbols-outlined text-sm ${loading ? "animate-spin" : ""}`}>
            refresh
          </span>
          Refresh
        </button>
      </div>

      {/* Loading */}
      {loading && !data && (
        <div className="flex justify-center py-20">
          <span className="material-symbols-outlined text-4xl text-on-surface-variant animate-spin">
            progress_activity
          </span>
        </div>
      )}

      {/* Error */}
      {error && (
        <div className="glass-card p-6 text-error text-center">{error}</div>
      )}

      {/* Data */}
      {data && (
        <>
          {/* Overall status card */}
          <div className="glass-card p-6 rounded-2xl mb-6">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-3">
                <span className="material-symbols-outlined text-2xl text-primary">
                  verified_user
                </span>
                <h2 className="text-lg font-bold text-on-surface">Overall Status</h2>
              </div>
              <div className="flex items-center gap-4">
                <span
                  className={`inline-flex items-center gap-1 px-3 py-1 rounded-full text-sm font-medium ${
                    data.all_verified
                      ? "bg-green-500/15 text-green-400"
                      : "bg-red-500/15 text-red-400"
                  }`}
                >
                  <span className="material-symbols-outlined text-sm">
                    {data.all_verified ? "check_circle" : "cancel"}
                  </span>
                  {data.all_verified ? "All Verified" : "Issues Found"}
                </span>
                <span className="text-xs text-on-surface-variant">
                  Checked {new Date(data.checked_at).toLocaleString()}
                </span>
              </div>
            </div>
          </div>

          {/* Artifact cards */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            {data.artifacts.map((artifact) => (
              <div key={artifact.file_name} className="glass-card p-6 rounded-2xl">
                <div className="flex items-center gap-3 mb-4">
                  <span className="material-symbols-outlined text-2xl text-primary">
                    verified_user
                  </span>
                  <h2 className="text-lg font-bold text-on-surface">{artifact.file_name}</h2>
                  <div className="ml-auto">
                    <StatusBadge status={artifact.status} />
                  </div>
                </div>
                <StatRow label="Expected Hash" value={truncateHash(artifact.expected_hash)} />
                <StatRow label="Actual Hash" value={truncateHash(artifact.actual_hash)} />
                <StatRow
                  label="File Size"
                  value={artifact.file_size_bytes != null ? formatBytes(artifact.file_size_bytes) : "N/A"}
                />
                <StatRow
                  label="Last Modified"
                  value={
                    artifact.last_modified
                      ? new Date(artifact.last_modified).toLocaleString()
                      : "N/A"
                  }
                />
              </div>
            ))}
          </div>
        </>
      )}
    </>
  );
}
