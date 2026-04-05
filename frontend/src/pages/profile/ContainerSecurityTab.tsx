import { useEffect, useState } from "react";
import { getContainerSecurityStatus } from "../../api/containerSecurity";
import type { ContainerSecurityResponse } from "../../api/types";

function StatusBadge({ ok, label }: { ok: boolean; label: string }) {
  return (
    <span
      className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium ${
        ok ? "bg-green-500/15 text-green-400" : "bg-red-500/15 text-red-400"
      }`}
    >
      <span className="material-symbols-outlined text-xs">
        {ok ? "check_circle" : "cancel"}
      </span>
      {label}
    </span>
  );
}

function StatRow({ label, value }: { label: string; value: string | number }) {
  return (
    <div className="flex justify-between items-center py-2 border-b border-white/5 last:border-0">
      <span className="text-sm text-on-surface-variant">{label}</span>
      <span className="text-sm font-medium text-on-surface">{value}</span>
    </div>
  );
}

export default function ContainerSecurityTab() {
  const [data, setData] = useState<ContainerSecurityResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  function fetchData() {
    setLoading(true);
    setError("");
    getContainerSecurityStatus()
      .then(setData)
      .catch(() => setError("Failed to load container security status"))
      .finally(() => setLoading(false));
  }

  useEffect(() => {
    fetchData();
  }, []);

  return (
    <>
      <header className="mb-10">
        <h1 className="text-5xl md:text-6xl font-extrabold font-headline text-on-surface">
          Container Security
        </h1>
        <p className="mt-3 text-on-surface-variant text-lg">
          Docker container runtime security posture
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

      {/* Data cards */}
      {data && (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          {/* Runtime Info Card */}
          <div className="glass-card p-6 rounded-2xl">
            <div className="flex items-center gap-3 mb-4">
              <span className="material-symbols-outlined text-2xl text-primary">
                deployed_code
              </span>
              <h2 className="text-lg font-bold text-on-surface">Runtime</h2>
              <div className="ml-auto">
                <StatusBadge
                  ok={!data.runtime.running_as_root}
                  label={data.runtime.running_as_root ? "Root" : "Non-root"}
                />
              </div>
            </div>
            <StatRow label="User" value={data.runtime.current_user} />
            <StatRow label="UID" value={data.runtime.current_uid} />
            <StatRow label="GID" value={data.runtime.current_gid} />
          </div>

          {/* Filesystem Card */}
          <div className="glass-card p-6 rounded-2xl">
            <div className="flex items-center gap-3 mb-4">
              <span className="material-symbols-outlined text-2xl text-primary">
                folder_managed
              </span>
              <h2 className="text-lg font-bold text-on-surface">Filesystem</h2>
              <div className="ml-auto">
                <StatusBadge
                  ok={!data.filesystem.root_writable}
                  label={data.filesystem.root_writable ? "Writable" : "Read-only"}
                />
              </div>
            </div>
            <StatRow
              label="Root Filesystem"
              value={data.filesystem.root_writable ? "Writable" : "Read-only"}
            />
            <StatRow
              label="/tmp Mount"
              value={data.filesystem.tmp_writable ? "Writable (tmpfs)" : "Not writable"}
            />
          </div>

          {/* Image Info Card */}
          <div className="glass-card p-6 rounded-2xl">
            <div className="flex items-center gap-3 mb-4">
              <span className="material-symbols-outlined text-2xl text-primary">
                inventory_2
              </span>
              <h2 className="text-lg font-bold text-on-surface">Image</h2>
              <div className="ml-auto">
                <StatusBadge
                  ok={data.image.multi_stage_build}
                  label={data.image.multi_stage_build ? "Multi-stage" : "Single-stage"}
                />
              </div>
            </div>
            <StatRow label="Base Image" value={data.image.base_image} />
            <StatRow label="Python Version" value={data.image.python_version} />
          </div>

          {/* Security Checks Card (full-width) */}
          <div className="glass-card p-6 rounded-2xl md:col-span-2">
            <div className="flex items-center gap-3 mb-4">
              <span className="material-symbols-outlined text-2xl text-primary">
                policy
              </span>
              <h2 className="text-lg font-bold text-on-surface">Security Checks</h2>
              <div className="ml-auto">
                <StatusBadge
                  ok={data.all_passed}
                  label={data.all_passed ? "All Passed" : "Issues Found"}
                />
              </div>
            </div>
            {data.checks.map((check) => (
              <div
                key={check.name}
                className="flex items-start gap-3 py-3 border-b border-white/5 last:border-0"
              >
                <span
                  className={`material-symbols-outlined text-lg mt-0.5 ${
                    check.passed ? "text-green-400" : "text-red-400"
                  }`}
                >
                  {check.passed ? "check_circle" : "cancel"}
                </span>
                <div className="flex-1 min-w-0">
                  <p className="text-sm font-medium text-on-surface">{check.name}</p>
                  <p className="text-xs text-on-surface-variant mt-0.5">{check.detail}</p>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </>
  );
}
