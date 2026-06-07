
import { useState, useRef } from "react"
import DiagramViewer from "./DiagramViewer"

const API = "http://localhost:8000"

const SUGGESTED = [
  "Where is authentication handled?",
  "What should a new developer read first?",
  "What are the main modules in this codebase?",
  "Explain the data flow from input to output",
]

export default function App() {
  const [repoInfo, setRepoInfo] = useState(null)
  const [uploading, setUploading] = useState(false)
  const [uploadError, setUploadError] = useState("")
  const [question, setQuestion] = useState("")
  const [answer, setAnswer] = useState(null)
  const [asking, setAsking] = useState(false)
  const [askError, setAskError] = useState("")
  const [dragOver, setDragOver] = useState(false)
  const fileRef = useRef()

  async function handleUpload(file) {
    if (!file || !file.name.endsWith(".zip")) {
      setUploadError("Please select a .zip file")
      return
    }
    setUploading(true)
    setUploadError("")
    setAnswer(null)
    setRepoInfo(null)

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
    const file = e.dataTransfer.files[0]
    if (file) handleUpload(file)
  }

  return (
    <div style={{ maxWidth: 720, margin: "0 auto", padding: "2rem 1rem", fontFamily: "system-ui, sans-serif" }}>

      <div style={{ marginBottom: "2rem" }}>
        <h1 style={{ fontSize: 26, fontWeight: 600, margin: 0, color: "#111" }}>
          Code Intel
        </h1>
        <p style={{ color: "#666", marginTop: 4, fontSize: 15 }}>
          Upload any GitHub repo as a zip and ask questions about it
        </p>
      </div>

      {/* Upload zone */}
      <div
        onClick={() => fileRef.current.click()}
        onDragOver={(e) => { e.preventDefault(); setDragOver(true) }}
        onDragLeave={() => setDragOver(false)}
        onDrop={onDrop}
        style={{
          border: `2px dashed ${dragOver ? "#6366f1" : repoInfo ? "#22c55e" : "#d1d5db"}`,
          borderRadius: 12,
          padding: "2rem",
          textAlign: "center",
          cursor: uploading ? "not-allowed" : "pointer",
          background: dragOver ? "#f0f0ff" : repoInfo ? "#f0fdf4" : "#fafafa",
          transition: "all 0.2s",
          marginBottom: "1rem"
        }}
      >
        <input
          ref={fileRef}
          type="file"
          accept=".zip"
          style={{ display: "none" }}
          onChange={(e) => handleUpload(e.target.files[0])}
        />

        {uploading ? (
          <div>
            <Spinner />
            <p style={{ color: "#6366f1", marginTop: 8 }}>Reading files...</p>
          </div>
        ) : repoInfo ? (
          <div>
            <div style={{ fontSize: 28 }}>✓</div>
            <p style={{ color: "#16a34a", fontWeight: 500, margin: "4px 0" }}>
              {repoInfo.total_files} files loaded
            </p>
            <p style={{ color: "#888", fontSize: 13, margin: 0 }}>
              Click to upload a different repo
            </p>
          </div>
        ) : (
          <div>
            <div style={{ fontSize: 32, marginBottom: 8 }}>📁</div>
            <p style={{ color: "#374151", fontWeight: 500, margin: 0 }}>
              Drop your repo .zip here
            </p>
            <p style={{ color: "#9ca3af", fontSize: 13, margin: "4px 0 0" }}>
              or click to browse
            </p>
          </div>
        )}
      </div>

      {uploadError && (
        <p style={{ color: "#dc2626", fontSize: 14, marginBottom: "1rem" }}>{uploadError}</p>
      )}

      {/* File list */}
      {repoInfo && (
        <details style={{ marginBottom: "1.5rem" }}>
          <summary style={{ cursor: "pointer", color: "#6366f1", fontSize: 13, userSelect: "none" }}>
            View {repoInfo.files.length} files in repo
          </summary>
          <div style={{
            background: "#f9fafb", borderRadius: 8, padding: "0.75rem 1rem",
            marginTop: 8, maxHeight: 200, overflowY: "auto",
            border: "1px solid #e5e7eb", fontSize: 13, color: "#374151"
          }}>
            {repoInfo.files.map(f => (
              <div key={f} style={{ padding: "2px 0", fontFamily: "monospace" }}>{f}</div>
            ))}
          </div>
        </details>
      )}

      {/* Diagram viewer — shows after upload */}
      {repoInfo && (
        <DiagramViewer
          apiBase={API}
          repoLoaded={!!repoInfo}
        />
      )}

      {/* Suggested questions */}
      {repoInfo && (
        <div style={{ marginBottom: "1rem", marginTop: "1.5rem" }}>
          <p style={{ fontSize: 13, color: "#6b7280", marginBottom: 8 }}>Suggested questions:</p>
          <div style={{ display: "flex", flexWrap: "wrap", gap: 8 }}>
            {SUGGESTED.map(q => (
              <button
                key={q}
                onClick={() => setQuestion(q)}
                style={{
                  fontSize: 13, padding: "6px 12px", borderRadius: 20,
                  border: "1px solid #d1d5db", background: "#fff",
                  cursor: "pointer", color: "#374151",
                  transition: "all 0.15s"
                }}
                onMouseOver={e => e.target.style.borderColor = "#6366f1"}
                onMouseOut={e => e.target.style.borderColor = "#d1d5db"}
              >
                {q}
              </button>
            ))}
          </div>
        </div>
      )}

      {/* Question input */}
      <div style={{ display: "flex", gap: 8, marginBottom: "1rem" }}>
        <input
          value={question}
          onChange={e => setQuestion(e.target.value)}
          onKeyDown={e => e.key === "Enter" && !asking && repoInfo && handleAsk()}
          placeholder={repoInfo ? "Ask anything about this codebase..." : "Upload a repo first"}
          disabled={!repoInfo || asking}
          style={{
            flex: 1, padding: "10px 14px", borderRadius: 8,
            border: "1px solid #d1d5db", fontSize: 15,
            background: repoInfo ? "#fff" : "#f9fafb",
            color: "#111", outline: "none"
          }}
        />
        <button
          onClick={handleAsk}
          disabled={!repoInfo || asking || !question.trim()}
          style={{
            padding: "10px 20px", borderRadius: 8, border: "none",
            background: (!repoInfo || asking || !question.trim()) ? "#e5e7eb" : "#6366f1",
            color: (!repoInfo || asking || !question.trim()) ? "#9ca3af" : "#fff",
            fontWeight: 500, fontSize: 15, cursor:
              (!repoInfo || asking || !question.trim()) ? "not-allowed" : "pointer",
            transition: "all 0.15s", minWidth: 80
          }}
        >
          {asking ? <Spinner size={16} color="#fff" /> : "Ask"}
        </button>
      </div>

      {askError && (
        <p style={{ color: "#dc2626", fontSize: 14, marginBottom: "1rem" }}>{askError}</p>
      )}

      {/* Loading state */}
      {asking && (
        <div style={{
          padding: "1.5rem", borderRadius: 12, background: "#f9fafb",
          border: "1px solid #e5e7eb", color: "#6b7280", fontSize: 15
        }}>
          <Spinner /> Thinking...
        </div>
      )}

      {/* Answer */}
      {answer && !asking && (
        <div style={{ borderRadius: 12, border: "1px solid #e5e7eb", overflow: "hidden" }}>
          <div style={{ padding: "1rem 1.25rem", background: "#fff" }}>
            <p style={{ margin: 0, fontSize: 15, lineHeight: 1.7, color: "#111", whiteSpace: "pre-wrap" }}>
              {answer.answer}
            </p>
          </div>
          {answer.files_used && answer.files_used.length > 0 && (
            <div style={{
              padding: "0.75rem 1.25rem", background: "#f9fafb",
              borderTop: "1px solid #e5e7eb"
            }}>
              <p style={{ margin: "0 0 6px", fontSize: 12, color: "#9ca3af", fontWeight: 500 }}>
                FILES REFERENCED ({answer.files_used.length} of {answer.total_files_in_repo})
              </p>
              <div style={{ display: "flex", flexWrap: "wrap", gap: 6 }}>
                {answer.files_used.map(f => (
                  <span key={f} style={{
                    fontSize: 12, padding: "2px 8px", borderRadius: 4,
                    background: "#ede9fe", color: "#4c1d95", fontFamily: "monospace"
                  }}>
                    {f}
                  </span>
                ))}
              </div>
            </div>
          )}
        </div>
      )}

    </div>  
  )
}

function Spinner({ size = 18, color = "#6366f1" }) {
  return (
    <span style={{ display: "inline-block", verticalAlign: "middle" }}>
      <svg width={size} height={size} viewBox="0 0 24 24" fill="none">
        <circle cx="12" cy="12" r="10" stroke={color} strokeWidth="3" strokeOpacity="0.25" />
        <path d="M12 2a10 10 0 0 1 10 10" stroke={color} strokeWidth="3" strokeLinecap="round">
          <animateTransform attributeName="transform" type="rotate"
            from="0 12 12" to="360 12 12" dur="0.8s" repeatCount="indefinite" />
        </path>
      </svg>
    </span>
  )
}
