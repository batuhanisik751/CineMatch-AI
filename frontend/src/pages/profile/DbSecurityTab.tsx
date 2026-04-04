import { useEffect, useState } from "react";
import { getDbSecurityStatus } from "../../api/dbSecurity";
import type { DbSecurityStatusResponse } from "../../api/types";

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

export default function DbSecurityTab() {
  const [data, setData] = useState<DbSecurityStatusResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  function fetchData() {
    setLoading(true);
    setError("");
    getDbSecurityStatus()
      .then(setData)
      .catch(() => setError("Failed to load database security status"))
      .finally(() => setLoading(false));
  }

  useEffect(() => {
    fetchData();
  }, []);

  return (
    <>
      <header className="mb-10">
        <h1 className="text-5xl md:text-6xl font-extrabold font-headline text-on-surface">
          Database Security
        </h1>
        <p className="mt-3 text-on-surface-variant text-lg">
          Connection security status and pool diagnostics
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
          {/* SSL/TLS Card */}
          <div className="glass-card p-6 rounded-2xl">
            <div className="flex items-center gap-3 mb-4">
              <span className="material-symbols-outlined text-2xl text-primary">
                shield_lock
              </span>
              <h2 className="text-lg font-bold text-on-surface">SSL / TLS</h2>
              <div className="ml-auto">
                <StatusBadge
                  ok={data.ssl.active}
                  label={data.ssl.active ? "Encrypted" : "Not Encrypted"}
                />
              </div>
            </div>
            <StatRow label="Configured Mode" value={data.ssl.configured_mode} />
            <StatRow
              label="Protocol Version"
              value={data.ssl.protocol_version ?? "N/A"}
            />
          </div>

          {/* Statement Timeout Card */}
          <div className="glass-card p-6 rounded-2xl">
            <div className="flex items-center gap-3 mb-4">
              <span className="material-symbols-outlined text-2xl text-primary">
                timer
              </span>
              <h2 className="text-lg font-bold text-on-surface">
                Statement Timeout
              </h2>
              <div className="ml-auto">
                <StatusBadge
                  ok={data.statement_timeout.configured_ms > 0}
                  label={
                    data.statement_timeout.configured_ms > 0
                      ? "Enforced"
                      : "Disabled"
                  }
                />
              </div>
            </div>
            <StatRow
              label="Configured"
              value={
                data.statement_timeout.configured_ms > 0
                  ? `${data.statement_timeout.configured_ms} ms`
                  : "No limit"
              }
            />
            <StatRow label="Active (server)" value={data.statement_timeout.active} />
          </div>

          {/* Connection Info Card */}
          <div className="glass-card p-6 rounded-2xl">
            <div className="flex items-center gap-3 mb-4">
              <span className="material-symbols-outlined text-2xl text-primary">
                database
              </span>
              <h2 className="text-lg font-bold text-on-surface">Connection</h2>
            </div>
            <StatRow label="Database User" value={data.connection.current_user} />
            <StatRow label="Database Name" value={data.connection.current_database} />
          </div>

          {/* Pool Status Card */}
          <div className="glass-card p-6 rounded-2xl">
            <div className="flex items-center gap-3 mb-4">
              <span className="material-symbols-outlined text-2xl text-primary">
                water_drop
              </span>
              <h2 className="text-lg font-bold text-on-surface">
                Connection Pool
              </h2>
              <div className="ml-auto">
                <StatusBadge
                  ok={data.pool.pool_pre_ping}
                  label={data.pool.pool_pre_ping ? "Pre-ping On" : "Pre-ping Off"}
                />
              </div>
            </div>
            <StatRow label="Pool Size" value={data.pool.size} />
            <StatRow label="Available" value={data.pool.checked_in} />
            <StatRow label="In Use" value={data.pool.checked_out} />
            <StatRow label="Overflow" value={data.pool.overflow} />
            <StatRow
              label="Recycle"
              value={data.pool.pool_recycle > 0 ? `${data.pool.pool_recycle}s` : "Disabled"}
            />
          </div>

          {/* pgvector Query Safety Card */}
          <div className="glass-card p-6 rounded-2xl">
            <div className="flex items-center gap-3 mb-4">
              <span className="material-symbols-outlined text-2xl text-primary">
                frame_inspect
              </span>
              <h2 className="text-lg font-bold text-on-surface">
                pgvector Query Safety
              </h2>
              <div className="ml-auto">
                <StatusBadge
                  ok={data.pgvector_query_safety.typed_bindings}
                  label={
                    data.pgvector_query_safety.typed_bindings
                      ? "Typed Bindings"
                      : "String Cast"
                  }
                />
              </div>
            </div>
            <StatRow
              label="Binding Mode"
              value={
                data.pgvector_query_safety.typed_bindings
                  ? "Vector(384) typed"
                  : "str() cast"
              }
            />
            <StatRow
              label="Services Protected"
              value={data.pgvector_query_safety.affected_services.length}
            />
            {data.pgvector_query_safety.affected_services.map((service) => (
              <StatRow key={service} label="" value={service} />
            ))}
          </div>
        </div>
      )}
    </>
  );
}
