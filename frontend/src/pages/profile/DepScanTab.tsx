import { useEffect, useState } from "react";
import { getDepScanStatus } from "../../api/depScan";
import type { DepScanResponse } from "../../api/types";

function StatusBadge({ status, label }: { status: "pass" | "warning" | "fail" | string; label: string }) {
  const colors: Record<string, string> = {
    pass: "bg-green-500/15 text-green-400",
    warning: "bg-amber-500/15 text-amber-400",
    fail: "bg-red-500/15 text-red-400",
  };
  const icons: Record<string, string> = {
    pass: "check_circle",
    warning: "warning",
    fail: "cancel",
  };
  return (
    <span
      className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium ${colors[status] ?? colors.fail}`}
    >
      <span className="material-symbols-outlined text-xs">
        {icons[status] ?? "error"}
      </span>
      {label}
    </span>
  );
}

function SeverityBadge({ level }: { level: string }) {
  const colors: Record<string, string> = {
    LOW: "bg-blue-500/15 text-blue-400",
    MEDIUM: "bg-amber-500/15 text-amber-400",
    HIGH: "bg-red-500/15 text-red-400",
  };
  return (
    <span className={`inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium ${colors[level] ?? "bg-white/10 text-on-surface-variant"}`}>
      {level}
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

export default function DepScanTab() {
  const [data, setData] = useState<DepScanResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  function fetchData() {
    setLoading(true);
    setError("");
    getDepScanStatus()
      .then(setData)
      .catch(() => setError("Failed to load dependency scan results"))
      .finally(() => setLoading(false));
  }

  useEffect(() => {
    fetchData();
  }, []);

  return (
    <>
      <header className="mb-10">
        <h1 className="text-5xl md:text-6xl font-extrabold font-headline text-on-surface">
          Dependency Scan
        </h1>
        <p className="mt-3 text-on-surface-variant text-lg">
          Vulnerability scanning for Python dependencies and static analysis
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
          {loading ? "Scanning..." : "Re-scan"}
        </button>
      </div>

      {/* Loading */}
      {loading && !data && (
        <div className="flex flex-col items-center justify-center py-20 gap-3">
          <span className="material-symbols-outlined text-4xl text-on-surface-variant animate-spin">
            progress_activity
          </span>
          <p className="text-sm text-on-surface-variant">Running dependency scan — this may take a moment...</p>
        </div>
      )}

      {/* Error */}
      {error && (
        <div className="glass-card p-6 text-error text-center">{error}</div>
      )}

      {/* Data cards */}
      {data && (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          {/* Summary Card (full-width) */}
          <div className="glass-card p-6 rounded-2xl md:col-span-2">
            <div className="flex items-center gap-3 mb-4">
              <span className="material-symbols-outlined text-2xl text-primary">
                security
              </span>
              <h2 className="text-lg font-bold text-on-surface">Scan Summary</h2>
              <div className="ml-auto">
                <StatusBadge
                  status={data.summary.overall_status}
                  label={
                    data.summary.overall_status === "pass"
                      ? "All Clear"
                      : data.summary.overall_status === "warning"
                        ? "Warnings"
                        : "Issues Found"
                  }
                />
              </div>
            </div>
            <StatRow label="Total Dependencies" value={data.summary.total_dependencies} />
            <StatRow label="Vulnerable Dependencies" value={data.summary.vulnerable_dependencies} />
            <StatRow label="Bandit Issues" value={data.summary.bandit_issues} />
            <StatRow label="Scanned At" value={new Date(data.scanned_at).toLocaleString()} />
          </div>

          {/* pip-audit Card */}
          <div className="glass-card p-6 rounded-2xl md:col-span-2">
            <div className="flex items-center gap-3 mb-4">
              <span className="material-symbols-outlined text-2xl text-primary">
                bug_report
              </span>
              <h2 className="text-lg font-bold text-on-surface">pip-audit — Known Vulnerabilities</h2>
              <div className="ml-auto">
                {data.pip_audit.available ? (
                  <StatusBadge
                    status={data.pip_audit.vulnerable_count === 0 ? "pass" : "fail"}
                    label={
                      data.pip_audit.vulnerable_count === 0
                        ? "No Vulnerabilities"
                        : `${data.pip_audit.vulnerable_count} Found`
                    }
                  />
                ) : (
                  <span className="text-xs text-on-surface-variant">Not available</span>
                )}
              </div>
            </div>

            {!data.pip_audit.available && (
              <p className="text-sm text-on-surface-variant py-2">
                pip-audit is not installed. Install with: <code className="text-primary">pip install pip-audit</code>
              </p>
            )}

            {data.pip_audit.error && data.pip_audit.available && (
              <p className="text-sm text-error py-2">{data.pip_audit.error}</p>
            )}

            {data.pip_audit.available && !data.pip_audit.error && data.pip_audit.vulnerabilities.length === 0 && (
              <p className="text-sm text-green-400 py-2">No known vulnerabilities found in {data.pip_audit.dependency_count} dependencies.</p>
            )}

            {data.pip_audit.vulnerabilities.map((v, i) => (
              <div
                key={`${v.vuln_id}-${i}`}
                className="flex items-start gap-3 py-3 border-b border-white/5 last:border-0"
              >
                <span className="material-symbols-outlined text-lg mt-0.5 text-red-400">
                  error
                </span>
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2 flex-wrap">
                    <span className="text-sm font-medium text-on-surface">
                      {v.name} {v.version}
                    </span>
                    <span className="text-xs font-mono text-amber-400">{v.vuln_id}</span>
                  </div>
                  <p className="text-xs text-on-surface-variant mt-0.5">{v.description}</p>
                  {v.fix_versions.length > 0 && (
                    <p className="text-xs text-green-400 mt-1">
                      Fix: upgrade to {v.fix_versions.join(", ")}
                    </p>
                  )}
                </div>
              </div>
            ))}
          </div>

          {/* Bandit Card */}
          <div className="glass-card p-6 rounded-2xl md:col-span-2">
            <div className="flex items-center gap-3 mb-4">
              <span className="material-symbols-outlined text-2xl text-primary">
                shield
              </span>
              <h2 className="text-lg font-bold text-on-surface">Bandit — Static Security Analysis</h2>
              <div className="ml-auto flex items-center gap-2">
                {data.bandit.available ? (
                  <>
                    {Object.entries(data.bandit.severity_counts)
                      .filter(([, count]) => count > 0)
                      .map(([level, count]) => (
                        <span key={level} className="text-xs text-on-surface-variant">
                          <SeverityBadge level={level} /> {count}
                        </span>
                      ))}
                    {data.bandit.results.length === 0 && (
                      <StatusBadge status="pass" label="Clean" />
                    )}
                  </>
                ) : (
                  <span className="text-xs text-on-surface-variant">Not available</span>
                )}
              </div>
            </div>

            {!data.bandit.available && (
              <p className="text-sm text-on-surface-variant py-2">
                bandit is not installed. Install with: <code className="text-primary">pip install bandit</code>
              </p>
            )}

            {data.bandit.error && data.bandit.available && (
              <p className="text-sm text-error py-2">{data.bandit.error}</p>
            )}

            {data.bandit.available && !data.bandit.error && data.bandit.results.length === 0 && (
              <p className="text-sm text-green-400 py-2">No security issues found by static analysis.</p>
            )}

            {data.bandit.results.map((r, i) => (
              <div
                key={`${r.test_id}-${r.filename}-${r.line_number}-${i}`}
                className="flex items-start gap-3 py-3 border-b border-white/5 last:border-0"
              >
                <span className={`material-symbols-outlined text-lg mt-0.5 ${
                  r.issue_severity === "HIGH" ? "text-red-400" :
                  r.issue_severity === "MEDIUM" ? "text-amber-400" : "text-blue-400"
                }`}>
                  {r.issue_severity === "HIGH" ? "error" : r.issue_severity === "MEDIUM" ? "warning" : "info"}
                </span>
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2 flex-wrap">
                    <span className="text-xs font-mono text-on-surface-variant">
                      {r.filename}:{r.line_number}
                    </span>
                    <span className="text-xs font-mono text-primary">{r.test_id}</span>
                    <SeverityBadge level={r.issue_severity} />
                  </div>
                  <p className="text-sm text-on-surface mt-0.5">{r.issue_text}</p>
                  <p className="text-xs text-on-surface-variant mt-0.5">Confidence: {r.issue_confidence}</p>
                </div>
              </div>
            ))}
          </div>

          {/* Safety Card */}
          {data.safety.available && (
            <div className="glass-card p-6 rounded-2xl md:col-span-2">
              <div className="flex items-center gap-3 mb-4">
                <span className="material-symbols-outlined text-2xl text-primary">
                  health_and_safety
                </span>
                <h2 className="text-lg font-bold text-on-surface">Safety — Dependency Check</h2>
                <div className="ml-auto">
                  <StatusBadge
                    status={data.safety.vulnerabilities.length === 0 ? "pass" : "fail"}
                    label={
                      data.safety.vulnerabilities.length === 0
                        ? "No Issues"
                        : `${data.safety.vulnerabilities.length} Found`
                    }
                  />
                </div>
              </div>

              {data.safety.error && (
                <p className="text-sm text-error py-2">{data.safety.error}</p>
              )}

              {!data.safety.error && data.safety.vulnerabilities.length === 0 && (
                <p className="text-sm text-green-400 py-2">No vulnerabilities found by safety check.</p>
              )}

              {data.safety.vulnerabilities.map((v, i) => (
                <div
                  key={`safety-${v.vuln_id}-${i}`}
                  className="flex items-start gap-3 py-3 border-b border-white/5 last:border-0"
                >
                  <span className="material-symbols-outlined text-lg mt-0.5 text-red-400">
                    error
                  </span>
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 flex-wrap">
                      <span className="text-sm font-medium text-on-surface">
                        {v.name} {v.version}
                      </span>
                      <span className="text-xs font-mono text-amber-400">{v.vuln_id}</span>
                    </div>
                    <p className="text-xs text-on-surface-variant mt-0.5">{v.description}</p>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}
    </>
  );
}
