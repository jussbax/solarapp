import { Component, type ReactNode } from 'react'

/**
 * Keeps one broken card from blanking the whole page. Results saved by an older
 * version of the app can miss fields the current view expects; the fallback says
 * so and the rest of the page keeps working.
 */
export default class ErrorBoundary extends Component<{ children: ReactNode; title?: string; onRecalculate?: () => void }, { error: Error | null }> {
  state = { error: null as Error | null }

  static getDerivedStateFromError(error: Error) {
    return { error }
  }

  componentDidUpdate(prev: { children: ReactNode }) {
    if (prev.children !== this.props.children && this.state.error) this.setState({ error: null })
  }

  render() {
    if (!this.state.error) return this.props.children
    return (
      <div className="banner warn">
        {this.props.title ?? 'This part'} could not be shown. The results were probably saved by an older version of the app.{' '}
        {this.props.onRecalculate ? (
          <button type="button" className="small" onClick={this.props.onRecalculate} style={{ marginLeft: 6 }}>
            Save and compute
          </button>
        ) : (
          'Save and compute to refresh them.'
        )}
        <div className="muted" style={{ marginTop: 4, fontSize: 12 }}>{String(this.state.error.message)}</div>
      </div>
    )
  }
}
