import React from 'react';

class ErrorBoundary extends React.Component {
    constructor(props) {
        super(props);
        this.state = { hasError: false, error: null };
    }

    static getDerivedStateFromError(error) {
        return { hasError: true, error };
    }

    componentDidCatch(error, errorInfo) {
        console.error("ErrorBoundary caught an error", error, errorInfo);
    }

    render() {
        if (this.state.hasError) {
            if (this.props.FallbackComponent) {
                return <this.props.FallbackComponent error={this.state.error} />;
            }
            return (
                <div className="p-4 bg-red-100 border border-red-400 text-red-700 rounded">
                    <h2>Something went wrong.</h2>
                    <details className="whitespace-pre-wrap">
                        {this.state.error && this.state.error.toString()}
                    </details>
                </div>
            );
        }

        return this.props.children;
    }
}

export default ErrorBoundary;
