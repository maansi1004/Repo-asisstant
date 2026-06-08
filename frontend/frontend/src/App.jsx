import { useState, useRef, useEffect } from "react"
import DiagramViewer from "./DiagramViewer"

const API = "http://localhost:8000"

const FEATURES = [
  {
    id: "summary",
    icon: "◈",
    title: "Repository Summary",
    description: "Instantly detects tech stack, architecture patterns, main features, and entry points. No manual reading required.",
    endpoint: "/summary",
    color: "#3b82f6",
    glow: "rgba(59,130,246,0.15)"
  },
  {
    id: "security",
    icon: "⬡",
    title: "Security Scanner",
    description: "Rule-based scanner detects hardcoded secrets, SQL injection risks, missing .env files, and weak password hashing.",
    endpoint: "/security",
    color: "#ef4444",
    glow: "rgba(239,68,68,0.15)"
  },
  {
    id: "dependencies",
    icon: "⬢",
    title: "Dependency Detection",
    description: "Identifies 50+ frameworks and libraries across frontend, backend, database, auth, and deployment layers.",
    endpoint: "/dependencies",
    color: "#10b981",
    glow: "rgba(16,185,129,0.15)"
  },
  {
    id: "onboard",
    icon: "◎",
    title: "Onboarding Assistant",
    description: "Generates a day-by-day learning path for new developers — prerequisites, key files, and first tasks.",
    endpoint: "/onboard",
    color: "#f59e0b",
    glow: "rgba(245,158,11,0.15)"
  },
  {
    id: "diagram",
    icon: "◇",
    title: "Architecture Diagram",
    description: "Auto-generates interactive Mermaid diagrams with actual filenames grouped by layer with labeled relationships.",
    endpoint: "/diagram",
    color: "#8b5cf6",
    glow: "rgba(139,92,246,0.15)",
    isDiagram: true
  },
  {
    id: "qa",
    icon: "◉",
    title: "Codebase Q&A",
    description: "Semantic search over your entire codebase. Ask in plain English, get answers with exact file and function references.",
    color: "#06b6d4",
    glow: "rgba(6,182,212,0.15)",
    isQA: true
  },
]

const SUGGESTED = [
  "Where is authentication handled?",
  "What should a new developer read first?",
  "What are the main modules?",
  "Explain the data flow from input to output",
  "Which files are most complex?",
  "How does the database connect?",
]

export default function App() {
  const [repoInfo, setRepoInfo] = useState(null)
  const [uploading, setUploading] = useState(false)
  const [uploadError, setUploadError] = useState("")
  const [dragOver, setDragOver] = useState(false)
  const [activeFeature, setActiveFeature] = useState(null)
  const [featureData, setFeatureData] = useState({})
  const [featureLoading, setFeatureLoading] = useState({})
  const [question, setQuestion] = useState("")
  const [answer, setAnswer] = useState(null)
  const [asking, setAsking] = useState(false)
  const [askError, setAskError] = useState("")
  const [mounted, setMounted] = useState(false)
  const fileRef = useRef()

  useEffect(() => {
    setTimeout(() => setMounted(true), 100)
  }, [])

  async function handleUpload(file) {
    if (!file || !file.name.endsWith(".zip")) {
      setUploadError("Please select a .zip file")
      return
    }
    setUploading(true)
    setUploadError("")
    setRepoInfo(null)
    setFeatureData({})
    setAnswer(null)
    setActiveFeature(null)

    const form = new FormData()
    form.append("file", file)

    try {
      const res = await fetch(`${API}/upload`, { method: "POST", body: form })
      const data = await res.json()
      if (!res.ok) throw new Error(data.detail || "Upload failed")
      setRepoInfo(data)
    } catch (e) {
      setUploadError(e.message)
    } finally {
      setUploading(false)
    }
  }

  async function loadFeature(feature) {
    if (feature.isQA || feature.isDiagram) {
      setActiveFeature(feature.id)
      return
    }
    setActiveFeature(feature.id)
    if (featureData[feature.id]) return

    setFeatureLoading(p => ({ ...p, [feature.id]: true }))
    try {
      const res = await fetch(`${API}${feature.endpoint}`)
      const data = await res.json()
      setFeatureData(p => ({ ...p, [feature.id]: data }))
    } catch (e) {
      setFeatureData(p => ({ ...p, [feature.id]: { error: e.message } }))
    } finally {
      setFeatureLoading(p => ({ ...p, [feature.id]: false }))
    }
  }

  async function handleAsk() {
    if (!question.trim()) return
    setAsking(true)
    setAskError("")
    setAnswer(null)
    try {
      const res = await fetch(`${API}/ask`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ question }),
      })
      const data = await res.json()
      if (!res.ok) throw new Error(data.detail || "Something went wrong")
      setAnswer(data)
    } catch (e) {
      setAskError(e.message)
    } finally {
      setAsking(false)
    }
  }

  function onDrop(e) {
    e.preventDefault()
    setDragOver(false)
    handleUpload(e.dataTransfer.files[0])
  }

  return (
    <div style={{
      minHeight: "100vh",
      background: "#080810",
      color: "#e2e8f0",
      fontFamily: "'DM Sans', 'Segoe UI', sans-serif",
    }}>
      {/* Ambient background */}
      <div style={{
        position: "fixed", inset: 0, pointerEvents: "none", zIndex: 0,
        background: "radial-gradient(ellipse 80% 50% at 50% -20%, rgba(99,102,241,0.12), transparent)",
      }} />

      <div style={{ position: "relative", zIndex: 1, maxWidth: 1100, margin: "0 auto", padding: "0 1.5rem" }}>

        {/* Header */}
        <header style={{
          padding: "2rem 0 1rem",
          display: "flex", alignItems: "center", justifyContent: "space-between",
          borderBottom: "1px solid rgba(255,255,255,0.06)"
        }}>
          <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
            <div style={{
              width: 36, height: 36, borderRadius: 10,
              background: "linear-gradient(135deg, #6366f1, #8b5cf6)",
              display: "flex", alignItems: "center", justifyContent: "center",
              fontSize: 18, fontWeight: 700, color: "#fff"
            }}>◈</div>
            <div>
              <div style={{ fontSize: 17, fontWeight: 700, color: "#f1f5f9", letterSpacing: "-0.3px" }}>
                Code Intel
              </div>
              <div style={{ fontSize: 11, color: "#64748b", letterSpacing: "0.05em" }}>
                REPOSITORY INTELLIGENCE
              </div>
            </div>
          </div>
          <div style={{
            fontSize: 12, color: "#475569", padding: "5px 12px",
            border: "1px solid rgba(255,255,255,0.08)", borderRadius: 20
          }}>
            Powered by Gemini + ChromaDB
          </div>
        </header>

        {/* Hero */}
        <section style={{
          padding: "4rem 0 3rem", textAlign: "center",
          opacity: mounted ? 1 : 0,
          transform: mounted ? "translateY(0)" : "translateY(16px)",
          transition: "all 0.6s ease"
        }}>
          <div style={{
            display: "inline-block", fontSize: 11, fontWeight: 600,
            letterSpacing: "0.15em", color: "#818cf8",
            padding: "5px 14px", borderRadius: 20,
            border: "1px solid rgba(129,140,248,0.3)",
            background: "rgba(99,102,241,0.08)", marginBottom: "1.5rem"
          }}>
            SEMANTIC RAG · CODEBASE INTELLIGENCE
          </div>

          <h1 style={{
            fontSize: "clamp(2.2rem, 5vw, 3.5rem)", fontWeight: 800,
            lineHeight: 1.1, margin: "0 0 1rem",
            letterSpacing: "-1.5px", color: "#f8fafc"
          }}>
            Chat with your{" "}
            <span style={{
              background: "linear-gradient(135deg, #818cf8, #a78bfa, #c084fc)",
              WebkitBackgroundClip: "text", WebkitTextFillColor: "transparent"
            }}>code.</span>
            <br />
            Map repos <span style={{
              background: "linear-gradient(135deg, #38bdf8, #818cf8)",
              WebkitBackgroundClip: "text", WebkitTextFillColor: "transparent"
            }}>instantly.</span>
          </h1>

          <p style={{
            fontSize: 16, color: "#94a3b8", maxWidth: 520,
            margin: "0 auto 2.5rem", lineHeight: 1.7
          }}>
            Upload any GitHub repository as a ZIP. Get instant answers, security scans,
            architecture diagrams, and onboarding guides.
          </p>

          {/* Upload zone */}
          <div
            onClick={() => !uploading && fileRef.current.click()}
            onDragOver={(e) => { e.preventDefault(); setDragOver(true) }}
            onDragLeave={() => setDragOver(false)}
            onDrop={onDrop}
            style={{
              maxWidth: 480, margin: "0 auto",
              border: `1.5px dashed ${dragOver ? "#818cf8" : repoInfo ? "#10b981" : "rgba(255,255,255,0.12)"}`,
              borderRadius: 16, padding: "2rem 1.5rem",
              cursor: uploading ? "wait" : "pointer",
              background: dragOver ? "rgba(99,102,241,0.08)" : repoInfo ? "rgba(16,185,129,0.06)" : "rgba(255,255,255,0.02)",
              transition: "all 0.2s",
            }}
          >
            <input ref={fileRef} type="file" accept=".zip"
              style={{ display: "none" }}
              onChange={(e) => handleUpload(e.target.files[0])} />

            {uploading ? (
              <div style={{ textAlign: "center" }}>
                <div style={{ fontSize: 28, marginBottom: 8 }}>
                  <PulseRing />
                </div>
                <p style={{ color: "#818cf8", fontSize: 14, margin: 0 }}>
                  Indexing repository...
                </p>
              </div>
            ) : repoInfo ? (
              <div style={{ textAlign: "center" }}>
                <div style={{ fontSize: 24, marginBottom: 6 }}>✓</div>
                <p style={{ color: "#10b981", fontWeight: 600, margin: "0 0 4px", fontSize: 15 }}>
                  {repoInfo.total_files} files · {repoInfo.total_chunks} chunks indexed
                </p>
                <p style={{ color: "#475569", fontSize: 12, margin: 0 }}>
                  Click to upload a different repo
                </p>
              </div>
            ) : (
              <div style={{ textAlign: "center" }}>
                <div style={{ fontSize: 28, marginBottom: 8, opacity: 0.6 }}>⬆</div>
                <p style={{ color: "#e2e8f0", fontWeight: 500, margin: "0 0 4px", fontSize: 15 }}>
                  Drop your repo .zip here
                </p>
                <p style={{ color: "#475569", fontSize: 12, margin: 0 }}>
                  or click to browse · any GitHub repository
                </p>
              </div>
            )}
          </div>

          {uploadError && (
            <p style={{ color: "#f87171", fontSize: 13, marginTop: 8 }}>{uploadError}</p>
          )}
        </section>

        {/* Feature cards */}
        <section style={{ paddingBottom: "3rem" }}>
          <div style={{
            fontSize: 12, fontWeight: 600, letterSpacing: "0.1em",
            color: "#475569", marginBottom: "1.25rem", textTransform: "uppercase"
          }}>
            {repoInfo ? "Explore Your Repository" : "Features"}
          </div>

          <div style={{
            display: "grid",
            gridTemplateColumns: "repeat(auto-fill, minmax(300px, 1fr))",
            gap: "1rem"
          }}>
            {FEATURES.map((feature, i) => (
              <FeatureCard
                key={feature.id}
                feature={feature}
                active={activeFeature === feature.id}
                locked={!repoInfo}
                loading={featureLoading[feature.id]}
                onClick={() => repoInfo && loadFeature(feature)}
                delay={i * 60}
                mounted={mounted}
              />
            ))}
          </div>
        </section>

        {/* Feature panel */}
        {activeFeature && repoInfo && (
          <section style={{
            marginBottom: "3rem",
            border: "1px solid rgba(255,255,255,0.08)",
            borderRadius: 16, overflow: "hidden",
            background: "rgba(255,255,255,0.02)"
          }}>
            {/* Panel header */}
            <div style={{
              padding: "1rem 1.25rem",
              borderBottom: "1px solid rgba(255,255,255,0.06)",
              display: "flex", alignItems: "center", justifyContent: "space-between",
              background: "rgba(255,255,255,0.02)"
            }}>
              <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
                <span style={{ fontSize: 18, color: FEATURES.find(f => f.id === activeFeature)?.color }}>
                  {FEATURES.find(f => f.id === activeFeature)?.icon}
                </span>
                <span style={{ fontWeight: 600, fontSize: 15, color: "#f1f5f9" }}>
                  {FEATURES.find(f => f.id === activeFeature)?.title}
                </span>
              </div>
              <button
                onClick={() => setActiveFeature(null)}
                style={{
                  background: "none", border: "none", color: "#475569",
                  cursor: "pointer", fontSize: 18, lineHeight: 1
                }}
              >×</button>
            </div>

            {/* Panel content */}
            <div style={{ padding: "1.5rem" }}>

              {/* Q&A panel */}
              {activeFeature === "qa" && (
                <div>
                  <div style={{ display: "flex", flexWrap: "wrap", gap: 6, marginBottom: "1rem" }}>
                    {SUGGESTED.map(q => (
                      <button key={q} onClick={() => setQuestion(q)} style={{
                        fontSize: 12, padding: "5px 12px", borderRadius: 20,
                        border: "1px solid rgba(255,255,255,0.1)",
                        background: "rgba(255,255,255,0.04)",
                        cursor: "pointer", color: "#94a3b8",
                        transition: "all 0.15s"
                      }}
                        onMouseOver={e => { e.target.style.borderColor = "#818cf8"; e.target.style.color = "#c7d2fe" }}
                        onMouseOut={e => { e.target.style.borderColor = "rgba(255,255,255,0.1)"; e.target.style.color = "#94a3b8" }}
                      >{q}</button>
                    ))}
                  </div>

                  <div style={{ display: "flex", gap: 8 }}>
                    <input
                      value={question}
                      onChange={e => setQuestion(e.target.value)}
                      onKeyDown={e => e.key === "Enter" && !asking && handleAsk()}
                      placeholder="Ask anything about this codebase..."
                      style={{
                        flex: 1, padding: "10px 14px", borderRadius: 10,
                        border: "1px solid rgba(255,255,255,0.1)",
                        background: "rgba(255,255,255,0.05)",
                        color: "#f1f5f9", fontSize: 14, outline: "none"
                      }}
                    />
                    <button onClick={handleAsk} disabled={asking || !question.trim()} style={{
                      padding: "10px 20px", borderRadius: 10, border: "none",
                      background: asking ? "rgba(99,102,241,0.4)" : "#6366f1",
                      color: "#fff", fontWeight: 600, fontSize: 14,
                      cursor: asking ? "wait" : "pointer"
                    }}>
                      {asking ? "..." : "Ask"}
                    </button>
                  </div>

                  {askError && (
                    <p style={{ color: "#f87171", fontSize: 13, marginTop: 8 }}>{askError}</p>
                  )}

                  {answer && (
                    <div style={{
                      marginTop: "1rem", borderRadius: 12,
                      border: "1px solid rgba(255,255,255,0.08)",
                      overflow: "hidden"
                    }}>
                      {answer.direct_answer && (
                        <div style={{
                          padding: "0.75rem 1rem",
                          background: "rgba(99,102,241,0.1)",
                          borderBottom: "1px solid rgba(255,255,255,0.06)",
                          fontSize: 14, color: "#c7d2fe", fontWeight: 500
                        }}>
                          {answer.direct_answer}
                        </div>
                      )}
                      <div style={{ padding: "1rem", fontSize: 14, lineHeight: 1.8, color: "#cbd5e1", whiteSpace: "pre-wrap" }}>
                        {answer.answer}
                      </div>
                      {answer.code_evidence && answer.code_evidence.length > 0 && (
                        <div style={{
                          padding: "0.75rem 1rem",
                          background: "rgba(0,0,0,0.3)",
                          borderTop: "1px solid rgba(255,255,255,0.06)"
                        }}>
                          <div style={{ fontSize: 11, color: "#475569", marginBottom: 8, fontWeight: 600, letterSpacing: "0.08em" }}>
                            CODE EVIDENCE
                          </div>
                          {answer.code_evidence.map((ev, i) => (
                            <pre key={i} style={{
                              margin: "0 0 8px", padding: "0.75rem",
                              background: "rgba(0,0,0,0.4)",
                              borderRadius: 8, fontSize: 12, color: "#94a3b8",
                              overflowX: "auto", whiteSpace: "pre-wrap"
                            }}>{ev}</pre>
                          ))}
                        </div>
                      )}
                      {answer.files_used && answer.files_used.length > 0 && (
                        <div style={{
                          padding: "0.75rem 1rem",
                          borderTop: "1px solid rgba(255,255,255,0.06)",
                          display: "flex", flexWrap: "wrap", gap: 6
                        }}>
                          {answer.files_used.map(f => (
                            <span key={f} style={{
                              fontSize: 11, padding: "2px 8px", borderRadius: 4,
                              background: "rgba(99,102,241,0.15)",
                              color: "#818cf8", fontFamily: "monospace"
                            }}>{f.split("\\").pop()}</span>
                          ))}
                        </div>
                      )}
                      {answer.follow_up_questions && answer.follow_up_questions.length > 0 && (
                        <div style={{
                          padding: "0.75rem 1rem",
                          borderTop: "1px solid rgba(255,255,255,0.06)"
                        }}>
                          <div style={{ fontSize: 11, color: "#475569", marginBottom: 8, fontWeight: 600, letterSpacing: "0.08em" }}>
                            EXPLORE FURTHER
                          </div>
                          <div style={{ display: "flex", flexWrap: "wrap", gap: 6 }}>
                            {answer.follow_up_questions.map((q, i) => (
                              <button key={i} onClick={() => setQuestion(q)} style={{
                                fontSize: 12, padding: "4px 10px", borderRadius: 6,
                                border: "1px solid rgba(255,255,255,0.08)",
                                background: "rgba(255,255,255,0.03)",
                                color: "#64748b", cursor: "pointer"
                              }}>{q}</button>
                            ))}
                          </div>
                        </div>
                      )}
                    </div>
                  )}
                </div>
              )}

              {/* Diagram panel */}
              {activeFeature === "diagram" && (
                <DiagramViewer apiBase={API} repoLoaded={!!repoInfo} darkMode />
              )}

              {/* Data panels */}
              {!["qa", "diagram"].includes(activeFeature) && (
                <FeatureDataPanel
                  featureId={activeFeature}
                  data={featureData[activeFeature]}
                  loading={featureLoading[activeFeature]}
                />
              )}
            </div>
          </section>
        )}

        {/* File list */}
        {repoInfo && (
          <section style={{ marginBottom: "3rem" }}>
            <details>
              <summary style={{
                cursor: "pointer", fontSize: 12, color: "#475569",
                fontWeight: 600, letterSpacing: "0.08em", userSelect: "none",
                textTransform: "uppercase"
              }}>
                {repoInfo.files?.length} indexed files
              </summary>
              <div style={{
                marginTop: 8, maxHeight: 200, overflowY: "auto",
                background: "rgba(255,255,255,0.02)",
                border: "1px solid rgba(255,255,255,0.06)",
                borderRadius: 10, padding: "0.75rem"
              }}>
                {repoInfo.files?.map(f => (
                  <div key={f} style={{
                    padding: "2px 0", fontSize: 12,
                    fontFamily: "monospace", color: "#475569"
                  }}>{f}</div>
                ))}
              </div>
            </details>
          </section>
        )}

      </div>
    </div>
  )
}

// Feature card component
function FeatureCard({ feature, active, locked, loading, onClick, delay, mounted }) {
  const [hovered, setHovered] = useState(false)

  return (
    <div
      onClick={onClick}
      onMouseEnter={() => setHovered(true)}
      onMouseLeave={() => setHovered(false)}
      style={{
        borderRadius: 14,
        border: `1px solid ${active ? feature.color + "40" : hovered && !locked ? "rgba(255,255,255,0.12)" : "rgba(255,255,255,0.06)"}`,
        background: active ? feature.glow : hovered && !locked ? "rgba(255,255,255,0.03)" : "rgba(255,255,255,0.02)",
        padding: "1.25rem",
        cursor: locked ? "not-allowed" : "pointer",
        opacity: mounted ? (locked ? 0.4 : 1) : 0,
        transform: mounted ? "translateY(0)" : "translateY(12px)",
        transition: `all 0.4s ease ${delay}ms`,
        position: "relative",
        overflow: "hidden"
      }}
    >
      {/* Glow effect on active */}
      {active && (
        <div style={{
          position: "absolute", top: 0, left: 0, right: 0, height: 2,
          background: `linear-gradient(90deg, transparent, ${feature.color}, transparent)`
        }} />
      )}

      <div style={{ display: "flex", alignItems: "flex-start", gap: 12 }}>
        <div style={{
          fontSize: 22, color: feature.color,
          opacity: locked ? 0.5 : 1,
          flexShrink: 0, marginTop: 2
        }}>
          {loading ? <MiniSpinner color={feature.color} /> : feature.icon}
        </div>
        <div style={{ flex: 1 }}>
          <div style={{
            fontSize: 14, fontWeight: 600, color: "#f1f5f9",
            marginBottom: 6, letterSpacing: "-0.2px"
          }}>
            {feature.title}
          </div>
          <div style={{
            fontSize: 12, color: "#64748b", lineHeight: 1.6
          }}>
            {feature.description}
          </div>
        </div>
      </div>

      {/* Active indicator */}
      {active && (
        <div style={{
          marginTop: 10, paddingTop: 10,
          borderTop: "1px solid rgba(255,255,255,0.06)",
          fontSize: 11, color: feature.color,
          fontWeight: 600, letterSpacing: "0.08em"
        }}>
          ▼ OPEN BELOW
        </div>
      )}
    </div>
  )
}

// Feature data renderer
function FeatureDataPanel({ featureId, data, loading }) {
  if (loading) return (
    <div style={{ textAlign: "center", padding: "2rem", color: "#475569" }}>
      <PulseRing /> Loading...
    </div>
  )
  if (!data) return null
  if (data.error) return (
    <p style={{ color: "#f87171", fontSize: 13 }}>Error: {data.error}</p>
  )

  if (featureId === "summary") return <SummaryPanel data={data} />
  if (featureId === "security") return <SecurityPanel data={data} />
  if (featureId === "dependencies") return <DepsPanel data={data} />
  if (featureId === "onboard") return <OnboardPanel data={data} />
  return <pre style={{ fontSize: 12, color: "#64748b", overflowX: "auto" }}>{JSON.stringify(data, null, 2)}</pre>
}

function SummaryPanel({ data }) {
  return (
    <div>
      <h2 style={{ fontSize: 20, fontWeight: 700, color: "#f1f5f9", margin: "0 0 4px" }}>
        {data.project_name}
      </h2>
      <p style={{ color: "#64748b", fontSize: 14, margin: "0 0 1.5rem" }}>{data.one_liner}</p>

      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "1rem", marginBottom: "1.5rem" }}>
        {Object.entries(data.tech_stack || {}).map(([cat, techs]) => techs.length > 0 && (
          <div key={cat} style={{
            padding: "0.75rem 1rem",
            background: "rgba(255,255,255,0.03)",
            border: "1px solid rgba(255,255,255,0.06)",
            borderRadius: 10
          }}>
            <div style={{ fontSize: 11, color: "#475569", fontWeight: 600, letterSpacing: "0.08em", marginBottom: 6, textTransform: "uppercase" }}>
              {cat}
            </div>
            <div style={{ display: "flex", flexWrap: "wrap", gap: 4 }}>
              {techs.map(t => (
                <span key={t} style={{
                  fontSize: 12, padding: "2px 8px", borderRadius: 4,
                  background: "rgba(99,102,241,0.15)", color: "#818cf8"
                }}>{t}</span>
              ))}
            </div>
          </div>
        ))}
      </div>

      {data.main_features && (
        <div>
          <div style={{ fontSize: 11, color: "#475569", fontWeight: 600, letterSpacing: "0.08em", marginBottom: 8, textTransform: "uppercase" }}>
            Main Features
          </div>
          {data.main_features.map((f, i) => (
            <div key={i} style={{ fontSize: 13, color: "#94a3b8", padding: "4px 0", display: "flex", gap: 8 }}>
              <span style={{ color: "#475569" }}>•</span> {f}
            </div>
          ))}
        </div>
      )}

      {data.for_beginners && (
        <div style={{
          marginTop: "1rem", padding: "0.75rem 1rem",
          background: "rgba(16,185,129,0.06)",
          border: "1px solid rgba(16,185,129,0.15)",
          borderRadius: 10, fontSize: 13, color: "#6ee7b7"
        }}>
          💡 {data.for_beginners}
        </div>
      )}
    </div>
  )
}

function SecurityPanel({ data }) {
  const sevColor = { HIGH: "#ef4444", MEDIUM: "#f59e0b", LOW: "#64748b" }
  const sevBg = { HIGH: "rgba(239,68,68,0.1)", MEDIUM: "rgba(245,158,11,0.1)", LOW: "rgba(100,116,139,0.1)" }

  return (
    <div>
      <div style={{ display: "flex", alignItems: "center", gap: "1rem", marginBottom: "1.5rem", flexWrap: "wrap" }}>
        <div style={{ textAlign: "center" }}>
          <div style={{
            fontSize: 42, fontWeight: 800, lineHeight: 1,
            color: data.score >= 8 ? "#10b981" : data.score >= 6 ? "#f59e0b" : "#ef4444"
          }}>
            {data.score}
          </div>
          <div style={{ fontSize: 11, color: "#475569", marginTop: 4 }}>/ 10</div>
        </div>
        <div>
          <div style={{ fontSize: 22, fontWeight: 700, color: "#f1f5f9" }}>Grade {data.grade}</div>
          <div style={{ fontSize: 13, color: "#64748b" }}>{data.recommendation}</div>
        </div>
        <div style={{ display: "flex", gap: 8, marginLeft: "auto" }}>
          {Object.entries(data.by_severity || {}).map(([sev, count]) => (
            <div key={sev} style={{
              padding: "4px 12px", borderRadius: 6,
              background: sevBg[sev], color: sevColor[sev],
              fontSize: 12, fontWeight: 600
            }}>
              {count} {sev}
            </div>
          ))}
        </div>
      </div>

      {data.ok_checks && data.ok_checks.length > 0 && (
        <div style={{ marginBottom: "1rem" }}>
          {data.ok_checks.map((ok, i) => (
            <div key={i} style={{ fontSize: 13, color: "#10b981", padding: "3px 0", display: "flex", gap: 8 }}>
              <span>✓</span> {ok}
            </div>
          ))}
        </div>
      )}

      <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
        {data.issues?.map((issue, i) => (
          <div key={i} style={{
            padding: "0.75rem 1rem",
            background: sevBg[issue.severity],
            border: `1px solid ${sevColor[issue.severity]}30`,
            borderLeft: `3px solid ${sevColor[issue.severity]}`,
            borderRadius: 8
          }}>
            <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 4 }}>
              <span style={{ fontSize: 11, fontWeight: 700, color: sevColor[issue.severity] }}>
                {issue.severity}
              </span>
              <span style={{ fontSize: 13, color: "#e2e8f0", fontWeight: 500 }}>
                {issue.message}
              </span>
            </div>
            <div style={{ fontSize: 11, color: "#64748b", fontFamily: "monospace", marginBottom: 4 }}>
              {issue.file}{issue.line > 0 ? ` · line ${issue.line}` : ""}
            </div>
            {issue.evidence && (
              <code style={{ fontSize: 11, color: "#94a3b8", display: "block", marginBottom: 4 }}>
                {issue.evidence}
              </code>
            )}
            <div style={{ fontSize: 11, color: "#475569" }}>Fix: {issue.fix}</div>
          </div>
        ))}
      </div>
    </div>
  )
}

function DepsPanel({ data }) {
  const catColors = {
    frontend: "#3b82f6", backend: "#10b981", database: "#f59e0b",
    auth: "#ef4444", realtime: "#8b5cf6", deployment: "#06b6d4",
    testing: "#84cc16", devops: "#f97316", ai: "#ec4899",
    ui: "#a78bfa", config: "#64748b", tooling: "#94a3b8"
  }

  return (
    <div>
      <div style={{ fontSize: 14, color: "#64748b", marginBottom: "1.25rem" }}>
        {data.total_detected} dependencies detected across {data.categories_found?.length} categories
      </div>
      <div style={{ display: "flex", flexDirection: "column", gap: "0.75rem" }}>
        {Object.entries(data.dependencies || {}).map(([cat, items]) => (
          <div key={cat}>
            <div style={{
              fontSize: 11, color: "#475569", fontWeight: 600,
              letterSpacing: "0.08em", marginBottom: 6, textTransform: "uppercase"
            }}>
              {cat}
            </div>
            <div style={{ display: "flex", flexWrap: "wrap", gap: 6 }}>
              {items.map(item => (
                <span key={item} style={{
                  fontSize: 12, padding: "3px 10px", borderRadius: 6,
                  background: `${catColors[cat] || "#475569"}18`,
                  color: catColors[cat] || "#94a3b8",
                  border: `1px solid ${catColors[cat] || "#475569"}30`,
                  fontWeight: 500
                }}>{item}</span>
              ))}
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}

function OnboardPanel({ data }) {
  return (
    <div>
      <p style={{ fontSize: 14, color: "#94a3b8", marginBottom: "1.5rem", lineHeight: 1.7 }}>
        {data.welcome_message}
      </p>

      {data.prerequisites && data.prerequisites.length > 0 && (
        <div style={{ marginBottom: "1.5rem" }}>
          <div style={{ fontSize: 11, color: "#475569", fontWeight: 600, letterSpacing: "0.08em", marginBottom: 8, textTransform: "uppercase" }}>
            Prerequisites
          </div>
          {data.prerequisites.map((p, i) => (
            <div key={i} style={{
              padding: "6px 0", fontSize: 13, color: "#94a3b8",
              display: "flex", gap: 8, borderBottom: "1px solid rgba(255,255,255,0.04)"
            }}>
              <span style={{ color: "#f59e0b", fontWeight: 600 }}>{p.skill}</span>
              <span style={{ color: "#475569" }}>— {p.why}</span>
            </div>
          ))}
        </div>
      )}

      {data.learning_path && (
        <div style={{ marginBottom: "1.5rem" }}>
          <div style={{ fontSize: 11, color: "#475569", fontWeight: 600, letterSpacing: "0.08em", marginBottom: 10, textTransform: "uppercase" }}>
            Learning Path
          </div>
          {data.learning_path.map((day, i) => (
            <div key={i} style={{
              marginBottom: 12, padding: "0.75rem 1rem",
              background: "rgba(255,255,255,0.02)",
              border: "1px solid rgba(255,255,255,0.06)",
              borderLeft: "3px solid #6366f1",
              borderRadius: 8
            }}>
              <div style={{ fontSize: 12, fontWeight: 700, color: "#818cf8", marginBottom: 6 }}>
                Day {day.day} — {day.title}
              </div>
              {day.tasks?.map((task, j) => (
                <div key={j} style={{ fontSize: 12, color: "#64748b", padding: "2px 0", display: "flex", gap: 8 }}>
                  <span>→</span>
                  <span><span style={{ color: "#94a3b8" }}>{task.action}</span> — {task.reason}</span>
                </div>
              ))}
            </div>
          ))}
        </div>
      )}

      {data.first_task_suggestion && (
        <div style={{
          padding: "0.75rem 1rem",
          background: "rgba(99,102,241,0.08)",
          border: "1px solid rgba(99,102,241,0.2)",
          borderRadius: 10, fontSize: 13, color: "#c7d2fe"
        }}>
          🎯 <strong>First task:</strong> {data.first_task_suggestion}
        </div>
      )}
    </div>
  )
}

function PulseRing() {
  return (
    <span style={{ display: "inline-block" }}>
      <svg width="24" height="24" viewBox="0 0 24 24">
        <circle cx="12" cy="12" r="8" fill="none" stroke="#6366f1" strokeWidth="2" strokeOpacity="0.3" />
        <circle cx="12" cy="12" r="8" fill="none" stroke="#6366f1" strokeWidth="2"
          strokeDasharray="12 40" strokeLinecap="round">
          <animateTransform attributeName="transform" type="rotate"
            from="0 12 12" to="360 12 12" dur="1s" repeatCount="indefinite" />
        </circle>
      </svg>
    </span>
  )
}

function MiniSpinner({ color }) {
  return (
    <svg width="20" height="20" viewBox="0 0 24 24" fill="none">
      <circle cx="12" cy="12" r="9" stroke={color} strokeWidth="2.5" strokeOpacity="0.2" />
      <path d="M12 3a9 9 0 0 1 9 9" stroke={color} strokeWidth="2.5" strokeLinecap="round">
        <animateTransform attributeName="transform" type="rotate"
          from="0 12 12" to="360 12 12" dur="0.7s" repeatCount="indefinite" />
      </path>
    </svg>
  )
}
