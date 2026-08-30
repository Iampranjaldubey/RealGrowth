import { Component, type ErrorInfo, type ReactNode } from "react";

interface Props {
  children: ReactNode;
}

interface State {
  error: Error | null;
}

export class ErrorBoundary extends Component<Props, State> {
  state: State = { error: null };

  static getDerivedStateFromError(error: Error): State {
    return { error };
  }

  componentDidCatch(error: Error, info: ErrorInfo): void {
    console.error("ErrorBoundary caught an error", error, info);
  }

  render() {
    if (this.state.error) {
      return (
        <div className="glass-card glass-card--center" style={{ padding: 40 }}>
          <div style={{ fontSize: 40 }}>⚠️</div>
          <h3 style={{ color: "var(--accent-danger)" }}>Something went wrong</h3>
          <p>{this.state.error.message || "An unexpected error occurred."}</p>
          <button type="button" className="btn btn-primary" onClick={() => window.location.reload()}>
            Refresh page
          </button>
        </div>
      );
    }
    return this.props.children;
  }
}
