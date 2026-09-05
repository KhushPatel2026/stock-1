import { Component, type ReactNode } from "react"

interface Props { children: ReactNode }
interface State { error: Error | null }

export default class ErrorBoundary extends Component<Props, State> {
  state: State = { error: null }
  static getDerivedStateFromError(error: Error): State { return { error } }
  componentDidCatch(error: Error) { console.error("UI error:", error) }
  render() {
    if (this.state.error) {
      return (
        <div style={{ padding: 24, fontFamily: "monospace" }}>
          <h2 style={{ color: "crimson" }}>Something went wrong</h2>
          <pre style={{ whiteSpace: "pre-wrap" }}>{this.state.error.message}</pre>
          <p style={{ color: "#888" }}>Check the browser console for the full stack trace.</p>
        </div>
      )
    }
    return this.props.children
  }
}
