import { useState } from "react"

const TABS = ["Risk", "Churn", "Ownership", "Coupling"]

export default function GitIntelPanel({ apiBase }) {
  const [activeTab, setActiveTab] = useState("Risk")
  const [data, setData] = useState({})
  const [loading, setLoading] = useState({})
  const [error, setError] = useState({})

  async function loadTab(tab) {
    setActiveTab(tab)
    if (data[tab]) return

    const endpoints = {
      Risk: "/git/risk",
      Churn: "/git/churn",
      Ownership: "/git/ownership",
      Coupling: "/git/coupling",
    }

    setLoading(p => ({ ...p, [tab]: true }))
    try {
      const res = await fetch(`${apiBase}${endpoints[tab]}`)
      const json = await res.json()
      if (!res.ok) throw new Error(json.detail || "Failed")
      setData(p => ({ ...p, [tab]: json }))
    } catch (e) {
      setError(p => ({ ...p, [tab]: e.message }))
    } finally {
      setLoading(p => ({ ...p, [tab]: false }))
    }
  }

  // Load Risk tab on first render
  useState(() => { loadTab("Risk") }, [])

  return (
    <div>
      {/* Sub-tabs */}
      <div style={{ display: "flex", gap: 4, marginBottom: "1.25rem", borderBottom: "1px solid rgba(255,255,255,0.06)", paddingBottom: "0.75rem" }}>
        {TABS.map(tab => (
          <button
            key={tab}
            onClick={() => loadTab(tab)}
            style={{
              padding: "6px 16px", borderRadius: 8, border: "none",
              background: activeTab === tab ? "rgba(99,102,241,0.2)" : "transparent",
              color: activeTab === tab ? "#818cf8" : "#475569",
              cursor: "pointer", fontSize: 13, fontWeight: activeTab === tab ? 600 : 400,
              transition: "all 0.15s"
            }}
          >
            {tab}
          </button>
        ))}
      </div>

      {/* Tab content */}
      {loading[activeTab] && <LoadingState />}
      {error[activeTab] && <ErrorState message={error[activeTab]} />}

      {!loading[activeTab] && !error[activeTab] && data[activeTab] && (
        <>
          {activeTab === "Risk" && <RiskTab data={data.Risk} />}
          {activeTab === "Churn" && <ChurnTab data={data.Churn} />}
          {activeTab === "Ownership" && <OwnershipTab data={data.Ownership} />}
          {activeTab === "Coupling" && <CouplingTab data={data.Coupling} />}
        </>
      )}
    </div>
  )
}

// ── Risk Tab ──────────────────────────────────────────────────

function RiskTab({ data }) {
  const stats = data.repo_stats || {}
  const risk = data.risk_ranking || []
  const reading = data.reading_order || []

  const sevColor = { high: "#ef4444", medium: "#f59e0b", low: "#10b981" }
  const sevBg = { high: "rgba(239,68,68,0.08)", medium: "rgba(245,158,11,0.08)", low: "rgba(16,185,129,0.08)" }
  const sevBorder = { high: "rgba(239,68,68,0.25)", medium: "rgba(245,158,11,0.25)", low: "rgba(16,185,129,0.25)" }

  return (
    <div>
      {/* Repo stats banner */}
      <div style={{
        display: "flex", gap: "1rem", flexWrap: "wrap",
        marginBottom: "1.5rem", padding: "0.75rem 1rem",
        background: "rgba(255,255,255,0.02)",
        border: "1px solid rgba(255,255,255,0.06)",
        borderRadius: 10
      }}>
        {[
          { label: "Commits", value: stats.total_commits_analyzed },
          { label: "Authors", value: stats.total_authors },
          { label: "Files tracked", value: stats.total_files_tracked },
          { label: "Most active", value: stats.most_active_author },
        ].map(s => (
          <div key={s.label} style={{ flex: 1, minWidth: 100 }}>
            <div style={{ fontSize: 11, color: "#475569", fontWeight: 600, letterSpacing: "0.08em", marginBottom: 2 }}>
              {s.label.toUpperCase()}
            </div>
            <div style={{ fontSize: 14, color: "#e2e8f0", fontWeight: 600 }}>
              {s.value || "—"}
            </div>
          </div>
        ))}
      </div>

      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "1.5rem" }}>
        {/* Risk ranking */}
        <div>
          <SectionLabel>Risk Ranking</SectionLabel>
          <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
            {risk.filter(r => !r.is_doc_file).slice(0, 10).map((r, i) => (
              <div key={i} style={{
                padding: "0.6rem 0.75rem",
                background: sevBg[r.risk_level],
                border: `1px solid ${sevBorder[r.risk_level]}`,
                borderLeft: `3px solid ${sevColor[r.risk_level]}`,
                borderRadius: 8
              }}>
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 3 }}>
                  <span style={{ fontSize: 12, fontFamily: "monospace", color: "#e2e8f0", fontWeight: 500 }}>
                    {r.file.split("/").pop().split("\\").pop()}
                  </span>
                  <span style={{
                    fontSize: 10, fontWeight: 700, padding: "1px 6px", borderRadius: 4,
                    background: sevBg[r.risk_level], color: sevColor[r.risk_level]
                  }}>
                    {r.risk_level.toUpperCase()}
                  </span>
                </div>
                <div style={{ fontSize: 11, color: "#475569" }}>{r.reason}</div>
                <div style={{ fontSize: 11, color: "#334155", marginTop: 2 }}>
                  Owner: {r.owner} · {r.ownership_status}
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Reading order */}
        <div>
          <SectionLabel>Recommended Reading Order</SectionLabel>
          <div style={{
            padding: "0.75rem",
            background: "rgba(99,102,241,0.05)",
            border: "1px solid rgba(99,102,241,0.15)",
            borderRadius: 10,
            marginBottom: "1rem"
          }}>
            <div style={{ fontSize: 12, color: "#818cf8", marginBottom: 8 }}>
              Start here as a new developer →
            </div>
            {reading.slice(0, 8).map((r, i) => (
              <div key={i} style={{
                display: "flex", gap: 10, alignItems: "center",
                padding: "5px 0",
                borderBottom: i < reading.length - 1 ? "1px solid rgba(255,255,255,0.04)" : "none"
              }}>
                <span style={{
                  width: 20, height: 20, borderRadius: "50%",
                  background: "rgba(99,102,241,0.2)",
                  color: "#818cf8", fontSize: 11, fontWeight: 700,
                  display: "flex", alignItems: "center", justifyContent: "center",
                  flexShrink: 0
                }}>{i + 1}</span>
                <div>
                  <div style={{ fontSize: 12, fontFamily: "monospace", color: "#c7d2fe" }}>
                    {r.file.split("/").pop().split("\\").pop()}
                  </div>
                  <div style={{ fontSize: 11, color: "#334155" }}>
                    {r.commits} commits · {r.reason}
                  </div>
                </div>
              </div>
            ))}
          </div>

          {/* Author breakdown */}
          <SectionLabel>Top Contributors</SectionLabel>
          <div style={{ display: "flex", flexDirection: "column", gap: 4 }}>
            {Object.entries(stats.authors || {}).slice(0, 6).map(([author, count]) => {
              const total = stats.total_commits_analyzed || 1
              const pct = Math.round(count / total * 100)
              return (
                <div key={author}>
                  <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 3 }}>
                    <span style={{ fontSize: 12, color: "#94a3b8" }}>{author}</span>
                    <span style={{ fontSize: 12, color: "#475569" }}>{count} commits ({pct}%)</span>
                  </div>
                  <div style={{ height: 4, background: "rgba(255,255,255,0.05)", borderRadius: 2 }}>
                    <div style={{
                      width: `${pct}%`, height: "100%",
                      background: "linear-gradient(90deg, #6366f1, #8b5cf6)",
                      borderRadius: 2, transition: "width 0.5s ease"
                    }} />
                  </div>
                </div>
              )
            })}
          </div>
        </div>
      </div>
    </div>
  )
}

// ── Churn Tab ─────────────────────────────────────────────────

function ChurnTab({ data }) {
  const churn = data.churn || []
  const maxScore = Math.max(...churn.map(c => c.churn_score), 1)

  return (
    <div>
      <div style={{ fontSize: 13, color: "#475569", marginBottom: "1rem" }}>
        Files sorted by churn score — high churn = frequently changing = higher bug risk
      </div>
      <div style={{ overflowX: "auto" }}>
        <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 13 }}>
          <thead>
            <tr style={{ borderBottom: "1px solid rgba(255,255,255,0.08)" }}>
              {["File", "Commits", "Churn Score", "Last Changed", "Active Days"].map(h => (
                <th key={h} style={{
                  textAlign: "left", padding: "6px 10px", fontSize: 11,
                  color: "#475569", fontWeight: 600, letterSpacing: "0.06em"
                }}>{h}</th>
              ))}
            </tr>
          </thead>
          <tbody>
        {churn.filter(row => !row.is_config_file).slice(0, 20).map((row, i) => {
              const barWidth = Math.round(row.churn_score / maxScore * 100)
              const isHigh = row.churn_score > maxScore * 0.6
              return (
                <tr key={i} style={{
                  borderBottom: "1px solid rgba(255,255,255,0.04)",
                  background: i % 2 === 0 ? "rgba(255,255,255,0.01)" : "transparent"
                }}>
                  <td style={{ padding: "7px 10px", fontFamily: "monospace", color: "#c7d2fe", fontSize: 12 }}>
                    {row.file.split("/").pop().split("\\").pop()}
                    <div style={{ fontSize: 10, color: "#334155" }}>{row.file}</div>
                  </td>
                  <td style={{ padding: "7px 10px", color: "#94a3b8" }}>{row.commits}</td>
                  <td style={{ padding: "7px 10px" }}>
                    <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
                      <div style={{ width: 60, height: 4, background: "rgba(255,255,255,0.05)", borderRadius: 2 }}>
                        <div style={{
                          width: `${barWidth}%`, height: "100%", borderRadius: 2,
                          background: isHigh ? "#ef4444" : "#6366f1"
                        }} />
                      </div>
                      <span style={{ color: isHigh ? "#ef4444" : "#94a3b8", fontSize: 12 }}>
                        {row.churn_score}
                      </span>
                    </div>
                  </td>
                  <td style={{ padding: "7px 10px", color: "#475569", fontSize: 12 }}>
                    {row.days_since_last_change === 0 ? "Today" :
                     row.days_since_last_change === 1 ? "Yesterday" :
                     `${row.days_since_last_change}d ago`}
                  </td>
                  <td style={{ padding: "7px 10px", color: "#475569", fontSize: 12 }}>
                    {row.days_active}d
                  </td>
                </tr>
              )
            })}
          </tbody>
        </table>
      </div>
    </div>
  )
}

// ── Ownership Tab ─────────────────────────────────────────────

function OwnershipTab({ data }) {
  const ownership = data.ownership || {}
  const [selected, setSelected] = useState(null)

  const files = Object.entries(ownership)
  const selectedData = selected ? ownership[selected] : null

  const statusColor = {
    sole_owner: "#10b981",
    clear_owner: "#3b82f6",
    primary_owner: "#f59e0b",
    shared: "#ef4444"
  }

  const statusLabel = {
    sole_owner: "Sole Owner",
    clear_owner: "Clear Owner",
    primary_owner: "Primary Owner",
    shared: "Shared"
  }

  return (
    <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "1.5rem" }}>
      {/* File list */}
      <div>
        <SectionLabel>Files — click to inspect</SectionLabel>
        <div style={{ display: "flex", flexDirection: "column", gap: 4, maxHeight: 400, overflowY: "auto" }}>
          {files.map(([filepath, info]) => (
            <div
              key={filepath}
              onClick={() => setSelected(filepath)}
              style={{
                padding: "8px 10px", borderRadius: 8, cursor: "pointer",
                border: `1px solid ${selected === filepath ? statusColor[info.ownership_status] + "40" : "rgba(255,255,255,0.06)"}`,
                background: selected === filepath ? statusColor[info.ownership_status] + "10" : "rgba(255,255,255,0.02)",
                transition: "all 0.15s"
              }}
            >
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                <span style={{ fontSize: 12, fontFamily: "monospace", color: "#c7d2fe" }}>
                  {filepath.split("/").pop().split("\\").pop()}
                </span>
                <span style={{
                  fontSize: 10, fontWeight: 600, padding: "1px 6px", borderRadius: 4,
                  color: statusColor[info.ownership_status],
                  background: statusColor[info.ownership_status] + "15"
                }}>
                  {statusLabel[info.ownership_status]}
                </span>
              </div>
              <div style={{ fontSize: 11, color: "#475569", marginTop: 2 }}>
                {info.owner} · {info.num_authors} author{info.num_authors !== 1 ? "s" : ""}
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Detail panel */}
      <div>
        <SectionLabel>Author Breakdown</SectionLabel>
        {selectedData ? (
          <div style={{
            padding: "1rem",
            background: "rgba(255,255,255,0.02)",
            border: "1px solid rgba(255,255,255,0.06)",
            borderRadius: 10
          }}>
            <div style={{ marginBottom: "1rem" }}>
              <div style={{ fontSize: 12, fontFamily: "monospace", color: "#818cf8", marginBottom: 4 }}>
                {selected}
              </div>
              <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
                <Badge color={statusColor[selectedData.ownership_status]}>
                  {statusLabel[selectedData.ownership_status]}
                </Badge>
                <Badge color="#475569">{selectedData.total_commits} total commits</Badge>
                <Badge color="#475569">{selectedData.num_authors} authors</Badge>
              </div>
            </div>

            <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
              {Object.entries(selectedData.all_authors).slice(0, 8).map(([author, count]) => {
                const pct = Math.round(count / selectedData.total_commits * 100)
                const isOwner = author === selectedData.owner
                return (
                  <div key={author}>
                    <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 3 }}>
                      <span style={{ fontSize: 12, color: isOwner ? "#e2e8f0" : "#94a3b8", fontWeight: isOwner ? 600 : 400 }}>
                        {isOwner ? "★ " : ""}{author}
                      </span>
                      <span style={{ fontSize: 11, color: "#475569" }}>{count} ({pct}%)</span>
                    </div>
                    <div style={{ height: 4, background: "rgba(255,255,255,0.05)", borderRadius: 2 }}>
                      <div style={{
                        width: `${pct}%`, height: "100%", borderRadius: 2,
                        background: isOwner
                          ? `linear-gradient(90deg, ${statusColor[selectedData.ownership_status]}, ${statusColor[selectedData.ownership_status]}aa)`
                          : "rgba(99,102,241,0.4)"
                      }} />
                    </div>
                  </div>
                )
              })}
            </div>
          </div>
        ) : (
          <div style={{
            padding: "2rem", textAlign: "center",
            color: "#334155", fontSize: 13,
            border: "1px dashed rgba(255,255,255,0.06)", borderRadius: 10
          }}>
            Select a file to see author breakdown
          </div>
        )}
      </div>
    </div>
  )
}

// ── Coupling Tab ──────────────────────────────────────────────

function CouplingTab({ data }) {
  const coupling = data.coupling || []

  const labelColor = { tight: "#ef4444", moderate: "#f59e0b", loose: "#10b981" }
  const maxChanges = Math.max(...coupling.map(c => c.co_changes), 1)

  return (
    <div>
      <div style={{
        padding: "0.75rem 1rem", marginBottom: "1rem",
        background: "rgba(245,158,11,0.06)",
        border: "1px solid rgba(245,158,11,0.15)",
        borderRadius: 8, fontSize: 13, color: "#fcd34d"
      }}>
        ⚠ Coupled files change together frequently. Modifying one likely requires updating the other.
      </div>

      <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
        {coupling.map((pair, i) => {
          const barWidth = Math.round(pair.co_changes / maxChanges * 100)
          const color = labelColor[pair.label]

          return (
            <div key={i} style={{
              padding: "0.75rem 1rem",
              background: "rgba(255,255,255,0.02)",
              border: `1px solid ${color}20`,
              borderLeft: `3px solid ${color}`,
              borderRadius: 8
            }}>
              <div style={{ display: "flex", alignItems: "center", gap: 10, marginBottom: 6, flexWrap: "wrap" }}>
                <span style={{ fontSize: 12, fontFamily: "monospace", color: "#c7d2fe" }}>
                  {pair.file_a.split("/").pop().split("\\").pop()}
                </span>
                <span style={{ color: "#475569", fontSize: 12 }}>↔</span>
                <span style={{ fontSize: 12, fontFamily: "monospace", color: "#c7d2fe" }}>
                  {pair.file_b.split("/").pop().split("\\").pop()}
                </span>
                <span style={{
                  marginLeft: "auto", fontSize: 10, fontWeight: 700,
                  padding: "2px 8px", borderRadius: 4,
                  color, background: color + "15"
                }}>
                  {pair.label.toUpperCase()}
                </span>
              </div>

              <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
                <div style={{ flex: 1, height: 4, background: "rgba(255,255,255,0.05)", borderRadius: 2 }}>
                  <div style={{ width: `${barWidth}%`, height: "100%", background: color, borderRadius: 2 }} />
                </div>
                <span style={{ fontSize: 12, color: "#475569", whiteSpace: "nowrap" }}>
                  {pair.co_changes} co-changes · {pair.strength_percent}% of commits
                </span>
              </div>

              <div style={{ fontSize: 11, color: "#334155", marginTop: 4 }}>
                {pair.file_a} ↔ {pair.file_b}
              </div>
            </div>
          )
        })}
      </div>
    </div>
  )
}

// ── Shared components ─────────────────────────────────────────

function SectionLabel({ children }) {
  return (
    <div style={{
      fontSize: 11, color: "#475569", fontWeight: 600,
      letterSpacing: "0.08em", marginBottom: 10,
      textTransform: "uppercase"
    }}>
      {children}
    </div>
  )
}

function Badge({ color, children }) {
  return (
    <span style={{
      fontSize: 11, padding: "2px 8px", borderRadius: 4,
      color, background: color + "15", fontWeight: 500
    }}>
      {children}
    </span>
  )
}

function LoadingState() {
  return (
    <div style={{ textAlign: "center", padding: "2rem", color: "#475569", fontSize: 13 }}>
      <svg width="20" height="20" viewBox="0 0 24 24" fill="none" style={{ display: "inline-block", marginBottom: 8 }}>
        <circle cx="12" cy="12" r="9" stroke="#6366f1" strokeWidth="2.5" strokeOpacity="0.2" />
        <path d="M12 3a9 9 0 0 1 9 9" stroke="#6366f1" strokeWidth="2.5" strokeLinecap="round">
          <animateTransform attributeName="transform" type="rotate" from="0 12 12" to="360 12 12" dur="0.8s" repeatCount="indefinite" />
        </path>
      </svg>
      <div>Loading git intelligence...</div>
    </div>
  )
}

function ErrorState({ message }) {
  return (
    <div style={{
      padding: "1rem", background: "rgba(239,68,68,0.08)",
      border: "1px solid rgba(239,68,68,0.2)", borderRadius: 8,
      fontSize: 13, color: "#f87171"
    }}>
      {message}
    </div>
  )
}
