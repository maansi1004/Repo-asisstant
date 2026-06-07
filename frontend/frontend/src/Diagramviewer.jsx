import { useEffect, useRef, useState } from "react"

export default function DiagramViewer({ apiBase, repoLoaded }) {
  const [diagram, setDiagram] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState("")
  const [mermaidReady, setMermaidReady] = useState(false)
  const containerRef = useRef()

  // Load mermaid.js once on component mount
  useEffect(() => {
    if (window.mermaid) {
      setMermaidReady(true)
      return
    }
    const script = document.createElement("script")
    script.src = "https://cdn.jsdelivr.net/npm/mermaid@10/dist/mermaid.min.js"
    script.onload = () => {
      window.mermaid.initialize({
        startOnLoad: false,
        theme: "default",
        flowchart: {
          curve: "basis",
          padding: 20,
          htmlLabels: true
        },
        themeVariables: {
          primaryColor: "#dbeafe",
          primaryBorderColor: "#93c5fd",
          primaryTextColor: "#1e3a5f",
          secondaryColor: "#fef9c3",
          secondaryBorderColor: "#fcd34d",
          tertiaryColor: "#dcfce7",
          tertiaryBorderColor: "#86efac",
          edgeLabelBackground: "#f9fafb",
          fontFamily: "system-ui, -apple-system, sans-serif",
          fontSize: "14px"
        }
      })
      setMermaidReady(true)
    }
    script.onerror = () => setError("Failed to load Mermaid library")
    document.head.appendChild(script)
  }, [])

  // Render diagram whenever mermaid is ready and diagram data changes
  useEffect(() => {
    if (!diagram || !mermaidReady || !containerRef.current) return
    renderDiagram()
  }, [diagram, mermaidReady])

  async function renderDiagram() {
    if (!containerRef.current) return
    try {
      const id = "mermaid-" + Date.now()
      const { svg } = await window.mermaid.render(id, diagram.mermaid_code)
      containerRef.current.innerHTML = svg

      // Make SVG fill container width
      const svgEl = containerRef.current.querySelector("svg")
      if (svgEl) {
        svgEl.style.width = "100%"
        svgEl.style.height = "auto"
        svgEl.style.maxWidth = "100%"
        svgEl.removeAttribute("width")
        svgEl.removeAttribute("height")
      }
    } catch (e) {
      console.error("Mermaid render error:", e)
      containerRef.current.innerHTML = `
        <div style="padding:1rem;background:#fef2f2;border-radius:8px;border:1px solid #fecaca">
          <p style="color:#dc2626;font-size:13px;margin:0 0 8px">Diagram render failed. Raw Mermaid code:</p>
          <pre style="font-size:11px;color:#374151;overflow:auto;margin:0">${diagram.mermaid_code}</pre>
        </div>`
    }
  }

  async function loadDiagram() {
    if (!repoLoaded) return
    setLoading(true)
    setError("")
    setDiagram(null)
    if (containerRef.current) containerRef.current.innerHTML = ""

    try {
      const res = await fetch(`${apiBase}/diagram`)
      if (!res.ok) throw new Error(`Server returned ${res.status}`)
      const data = await res.json()
      if (!data.mermaid_code) throw new Error("No diagram code returned")
      setDiagram(data)
    } catch (e) {
      setError(`Failed to load diagram: ${e.message}`)
    } finally {
      setLoading(false)
    }
  }

  function copyMermaidCode() {
    if (!diagram) return
    navigator.clipboard.writeText(diagram.mermaid_code)
      .then(() => alert("Mermaid code copied to clipboard!"))
      .catch(() => alert("Copy failed — check browser permissions"))
  }

  function downloadSVG() {
    const svgEl = containerRef.current?.querySelector("svg")
    if (!svgEl) return alert("No diagram to download yet")

    const svgData = new XMLSerializer().serializeToString(svgEl)
    const blob = new Blob([svgData], { type: "image/svg+xml;charset=utf-8" })
    const url = URL.createObjectURL(blob)
    const a = document.createElement("a")
    a.href = url
    a.download = "architecture-diagram.svg"
    document.body.appendChild(a)
    a.click()
    document.body.removeChild(a)
    URL.revokeObjectURL(url)
  }

  function downloadPNG() {
    const svgEl = containerRef.current?.querySelector("svg")
    if (!svgEl) return alert("No diagram to download yet")

    const canvas = document.createElement("canvas")
    const svgRect = svgEl.getBoundingClientRect()
    canvas.width = svgRect.width * 2   // 2x for retina
    canvas.height = svgRect.height * 2
    canvas.style.width = svgRect.width + "px"
    canvas.style.height = svgRect.height + "px"

    const ctx = canvas.getContext("2d")
    ctx.scale(2, 2)
    ctx.fillStyle = "#ffffff"
    ctx.fillRect(0, 0, canvas.width, canvas.height)

    const img = new Image()
    const svgData = new XMLSerializer().serializeToString(svgEl)
    const svgBlob = new Blob([svgData], { type: "image/svg+xml;charset=utf-8" })
    const url = URL.createObjectURL(svgBlob)

    img.onload = () => {
      ctx.drawImage(img, 0, 0)
      URL.revokeObjectURL(url)
      const pngUrl = canvas.toDataURL("image/png")
      const a = document.createElement("a")
      a.href = pngUrl
      a.download = "architecture-diagram.png"
      document.body.appendChild(a)
      a.click()
      document.body.removeChild(a)
    }
    img.src = url
  }

  return (
    <div style={{ marginTop: "1.5rem" }}>

      {/* Generate button */}
      <button
        onClick={loadDiagram}
        disabled={loading || !repoLoaded}
        style={{
          padding: "10px 20px",
          borderRadius: 8,
          border: "none",
          background: (!repoLoaded || loading) ? "#e5e7eb" : "#6366f1",
          color: (!repoLoaded || loading) ? "#9ca3af" : "#fff",
          cursor: (!repoLoaded || loading) ? "not-allowed" : "pointer",
          fontSize: 14,
          fontWeight: 500,
          display: "flex",
          alignItems: "center",
          gap: 8
        }}
      >
        {loading ? (
          <>
            <Spinner size={16} color="#9ca3af" />
            Generating diagram...
          </>
        ) : (
          "Generate Architecture Diagram"
        )}
      </button>

      {/* Error */}
      {error && (
        <p style={{
          color: "#dc2626", fontSize: 13,
          marginTop: 8, padding: "8px 12px",
          background: "#fef2f2", borderRadius: 6
        }}>
          {error}
        </p>
      )}

      {/* Diagram card */}
      {diagram && (
        <div style={{
          marginTop: "1rem",
          border: "1px solid #e5e7eb",
          borderRadius: 12,
          overflow: "hidden",
          background: "#fff"
        }}>

          {/* Toolbar */}
          <div style={{
            padding: "0.75rem 1rem",
            background: "#f9fafb",
            borderBottom: "1px solid #e5e7eb",
            display: "flex",
            alignItems: "center",
            gap: 8,
            flexWrap: "wrap"
          }}>
            <span style={{
              fontSize: 14,
              fontWeight: 600,
              color: "#111",
              flex: 1
            }}>
              Architecture Diagram
            </span>
            <button onClick={copyMermaidCode} style={btnStyle}>
              Copy Mermaid
            </button>
            <button onClick={downloadSVG} style={btnStyle}>
              Download SVG
            </button>
            <button onClick={downloadPNG} style={btnStyle}>
              Download PNG
            </button>
          </div>

          {/* Diagram render area */}
          <div style={{
            padding: "1.5rem",
            overflowX: "auto",
            minHeight: 200,
            background: "#fff"
          }}>
            <div ref={containerRef} />
          </div>

          {/* Description */}
          {diagram.description && (
            <div style={{
              padding: "0.75rem 1rem",
              background: "#f9fafb",
              borderTop: "1px solid #e5e7eb",
              fontSize: 13,
              color: "#6b7280",
              lineHeight: 1.6
            }}>
              {diagram.description}
            </div>
          )}

          {/* Mermaid source code (collapsible) */}
          <details>
            <summary style={{
              padding: "0.6rem 1rem",
              cursor: "pointer",
              fontSize: 12,
              color: "#9ca3af",
              background: "#f9fafb",
              borderTop: "1px solid #e5e7eb",
              userSelect: "none"
            }}>
              View Mermaid source code
            </summary>
            <pre style={{
              margin: 0,
              padding: "1rem",
              background: "#1e1e1e",
              color: "#d4d4d4",
              fontSize: 12,
              lineHeight: 1.6,
              overflowX: "auto",
              fontFamily: "monospace"
            }}>
              {diagram.mermaid_code}
            </pre>
          </details>
        </div>
      )}
    </div>
  )
}

const btnStyle = {
  padding: "5px 12px",
  borderRadius: 6,
  border: "1px solid #d1d5db",
  background: "#fff",
  cursor: "pointer",
  fontSize: 12,
  color: "#374151"
}

function Spinner({ size = 18, color = "#6366f1" }) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none">
      <circle cx="12" cy="12" r="10" stroke={color} strokeWidth="3" strokeOpacity="0.25" />
      <path d="M12 2a10 10 0 0 1 10 10" stroke={color} strokeWidth="3" strokeLinecap="round">
        <animateTransform attributeName="transform" type="rotate"
          from="0 12 12" to="360 12 12" dur="0.8s" repeatCount="indefinite" />
      </path>
    </svg>
  )
}
