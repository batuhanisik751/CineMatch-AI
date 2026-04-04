import { useEffect, useState } from "react";
import { getAuditLogs } from "../../api/audit";
import type { AuditLogListResponse, AuditLogEntry } from "../../api/types";

const ACTION_LABELS: Record<string, { label: string; icon: string }> = {
  "auth.login": { label: "Login", icon: "login" },
  "auth.login_failed": { label: "Login Failed", icon: "lock" },
  "auth.register": { label: "Account Created", icon: "person_add" },
  "auth.forbidden": { label: "Access Denied", icon: "block" },
  "data.import": { label: "Data Import", icon: "upload_file" },
  "data.export": { label: "Data Export", icon: "download" },
  "rate_limit.exceeded": { label: "Rate Limited", icon: "speed" },
};

const ACTION_OPTIONS = [
  { value: "", label: "All Actions" },
  { value: "auth.login", label: "Login" },
  { value: "auth.login_failed", label: "Login Failed" },
  { value: "auth.register", label: "Account Created" },
  { value: "auth.forbidden", label: "Access Denied" },
  { value: "data.import", label: "Data Import" },
  { value: "data.export", label: "Data Export" },
  { value: "rate_limit.exceeded", label: "Rate Limited" },
];

const PAGE_SIZE = 20;

function formatTimestamp(iso: string): string {
  const d = new Date(iso);
  return d.toLocaleString(undefined, {
    year: "numeric",
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

function ActionBadge({ action }: { action: string }) {
  const info = ACTION_LABELS[action] ?? { label: action, icon: "info" };
  const isFailure =
    action === "auth.login_failed" ||
    action === "auth.forbidden" ||
    action === "rate_limit.exceeded";

  return (
    <span
      className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium ${
        isFailure
          ? "bg-red-500/15 text-red-400"
          : "bg-primary/15 text-primary"
      }`}
    >
      <span className="material-symbols-outlined text-sm">{info.icon}</span>
      {info.label}
    </span>
  );
}

function StatusBadge({ status }: { status: string }) {
  const isSuccess = status === "success";
  return (
    <span
      className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium ${
        isSuccess
          ? "bg-green-500/15 text-green-400"
          : "bg-red-500/15 text-red-400"
      }`}
    >
      <span className="material-symbols-outlined text-xs">
        {isSuccess ? "check_circle" : "cancel"}
      </span>
      {isSuccess ? "Success" : "Failed"}
    </span>
  );
}

function DetailPreview({ detail }: { detail: Record<string, unknown> | null }) {
  if (!detail) return null;
  const entries = Object.entries(detail).slice(0, 3);
  return (
    <div className="flex flex-wrap gap-2 mt-1.5">
      {entries.map(([key, val]) => (
        <span
          key={key}
          className="text-xs text-on-surface-variant/60 bg-surface-variant/20 px-2 py-0.5 rounded"
        >
          {key}: {String(val)}
        </span>
      ))}
    </div>
  );
}

export default function AuditLogTab() {
  const [data, setData] = useState<AuditLogListResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  const [actionFilter, setActionFilter] = useState("");
  const [statusFilter, setStatusFilter] = useState("");
  const [page, setPage] = useState(0);

  useEffect(() => {
    setLoading(true);
    setError("");
    getAuditLogs({
      action: actionFilter || undefined,
      status: statusFilter || undefined,
      offset: page * PAGE_SIZE,
      limit: PAGE_SIZE,
    })
      .then(setData)
      .catch(() => setError("Failed to load audit logs"))
      .finally(() => setLoading(false));
  }, [actionFilter, statusFilter, page]);

  const totalPages = data ? Math.ceil(data.total / PAGE_SIZE) : 0;

  return (
    <>
      <header className="mb-10">
        <h1 className="text-5xl md:text-6xl font-extrabold font-headline text-on-surface">
          Audit Log
        </h1>
        <p className="mt-3 text-on-surface-variant text-lg">
          Your account security activity
        </p>
      </header>

      {/* Filters */}
      <div className="glass-card p-4 rounded-2xl mb-6 flex flex-wrap gap-3 items-center">
        <span className="material-symbols-outlined text-on-surface-variant">
          filter_list
        </span>
        <select
          value={actionFilter}
          onChange={(e) => { setActionFilter(e.target.value); setPage(0); }}
          className="bg-surface-container text-on-surface text-sm rounded-lg px-3 py-2 border border-white/10 focus:border-primary focus:outline-none"
        >
          {ACTION_OPTIONS.map((opt) => (
            <option key={opt.value} value={opt.value}>
              {opt.label}
            </option>
          ))}
        </select>
        <select
          value={statusFilter}
          onChange={(e) => { setStatusFilter(e.target.value); setPage(0); }}
          className="bg-surface-container text-on-surface text-sm rounded-lg px-3 py-2 border border-white/10 focus:border-primary focus:outline-none"
        >
          <option value="">All Statuses</option>
          <option value="success">Success</option>
          <option value="failure">Failed</option>
        </select>
        {(actionFilter || statusFilter) && (
          <button
            onClick={() => { setActionFilter(""); setStatusFilter(""); setPage(0); }}
            className="text-xs text-primary hover:text-primary/80 transition-colors"
          >
            Clear filters
          </button>
        )}
        {data && (
          <span className="ml-auto text-xs text-on-surface-variant">
            {data.total} event{data.total !== 1 ? "s" : ""}
          </span>
        )}
      </div>

      {/* Loading */}
      {loading && (
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

      {/* Log entries */}
      {data && !loading && (
        <>
          {data.logs.length === 0 ? (
            <div className="glass-card p-12 rounded-2xl text-center">
              <span className="material-symbols-outlined text-5xl text-on-surface-variant/30 mb-4 block">
                security
              </span>
              <p className="text-on-surface-variant text-lg">
                No audit events found
              </p>
              <p className="text-on-surface-variant/60 text-sm mt-1">
                Activity will appear here as you use CineMatch
              </p>
            </div>
          ) : (
            <div className="space-y-3">
              {data.logs.map((log: AuditLogEntry) => (
                <div
                  key={log.id}
                  className="glass-card p-4 rounded-2xl border border-white/5 hover:border-white/10 transition-colors"
                >
                  <div className="flex flex-wrap items-center gap-3">
                    <ActionBadge action={log.action} />
                    <StatusBadge status={log.status} />
                    <span className="text-xs text-on-surface-variant/60 ml-auto">
                      {formatTimestamp(log.timestamp)}
                    </span>
                  </div>
                  <div className="mt-2 flex flex-wrap items-center gap-4 text-xs text-on-surface-variant/50">
                    {log.ip_address && (
                      <span className="inline-flex items-center gap-1">
                        <span className="material-symbols-outlined text-xs">language</span>
                        {log.ip_address}
                      </span>
                    )}
                    {log.user_agent && (
                      <span className="truncate max-w-xs" title={log.user_agent}>
                        {log.user_agent.length > 60
                          ? log.user_agent.slice(0, 60) + "..."
                          : log.user_agent}
                      </span>
                    )}
                  </div>
                  <DetailPreview detail={log.detail} />
                </div>
              ))}
            </div>
          )}

          {/* Pagination */}
          {totalPages > 1 && (
            <div className="flex justify-center items-center gap-4 mt-8">
              <button
                onClick={() => setPage((p) => Math.max(0, p - 1))}
                disabled={page === 0}
                className="px-4 py-2 rounded-lg bg-surface-container text-on-surface text-sm border border-white/10 disabled:opacity-30 hover:border-primary/40 transition-colors"
              >
                Previous
              </button>
              <span className="text-sm text-on-surface-variant">
                Page {page + 1} of {totalPages}
              </span>
              <button
                onClick={() => setPage((p) => Math.min(totalPages - 1, p + 1))}
                disabled={page >= totalPages - 1}
                className="px-4 py-2 rounded-lg bg-surface-container text-on-surface text-sm border border-white/10 disabled:opacity-30 hover:border-primary/40 transition-colors"
              >
                Next
              </button>
            </div>
          )}
        </>
      )}
    </>
  );
}
