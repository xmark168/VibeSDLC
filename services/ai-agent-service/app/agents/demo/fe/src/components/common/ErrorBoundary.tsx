import React, { Component, ErrorInfo, ReactNode } from 'react';

interface ErrorBoundaryProps {
  children: ReactNode;
  fallback?: ReactNode;
}

interface ErrorBoundaryState {
  hasError: boolean;
  error: Error | null;
}

export class ErrorBoundary extends Component<ErrorBoundaryProps, ErrorBoundaryState> {
  constructor(props: ErrorBoundaryProps) {
    super(props);
    this.state = { hasError: false, error: null };
  }

  static getDerivedStateFromError(error: Error): ErrorBoundaryState {
    return { hasError: true, error };
  }

  componentDidCatch(error: Error, errorInfo: ErrorInfo) {
    // You can log the error to an error reporting service here
    // console.error('Uncaught error:', error, errorInfo);
  }

  render() {
    const { hasError, error } = this.state;
    const { fallback, children } = this.props;

    if (hasError) {
      if (fallback) {
        return <>{fallback}</>;
      }
      return (
        <div className="flex flex-col items-center justify-center min-h-[200px] text-center p-4 bg-red-50 text-red-700 rounded">
          <h2 className="text-xl font-bold mb-2">Something went wrong.</h2>
          {error && <pre className="whitespace-pre-wrap text-sm">{error.message}</pre>}
        </div>
      );
    }

    return children;
  }
}
