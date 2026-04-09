'use client';

import React from 'react';

/**
 * Loading spinner component
 */
export const LoadingSpinner: React.FC<{ message?: string }> = ({
  message = 'Loading...',
}) => (
  <div className="flex items-center justify-center h-full w-full">
    <div className="text-center">
      <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary mx-auto mb-4"></div>
      <p className="text-muted text-sm">{message}</p>
    </div>
  </div>
);

/**
 * Error state component
 */
export const ErrorState: React.FC<{ error: string; onRetry?: () => void }> = ({
  error,
  onRetry,
}) => (
  <div className="flex items-center justify-center h-full w-full bg-red-50 dark:bg-red-950 p-4">
    <div className="text-center">
      <h3 className="text-lg font-semibold text-red-900 dark:text-red-100 mb-2">
        Error
      </h3>
      <p className="text-red-700 dark:text-red-200 text-sm mb-4">{error}</p>
      {onRetry && (
        <button
          onClick={onRetry}
          className="text-sm text-red-600 dark:text-red-400 hover:underline"
        >
          Try Again
        </button>
      )}
    </div>
  </div>
);

/**
 * Empty state component
 */
export const EmptyState: React.FC<{ message: string; icon?: string }> = ({
  message,
  icon = '📭',
}) => (
  <div className="flex items-center justify-center h-full w-full text-center p-4">
    <div>
      <div className="text-4xl mb-2">{icon}</div>
      <p className="text-muted text-sm">{message}</p>
    </div>
  </div>
);

/**
 * Skeleton loader for papers list
 */
export const PaperSkeleton: React.FC = () => (
  <div className="space-y-2 animate-pulse">
    {[...Array(3)].map((_, i) => (
      <div key={i} className="bg-muted/20 rounded h-16 p-3 space-y-2">
        <div className="bg-muted/30 h-4 rounded w-3/4"></div>
        <div className="bg-muted/30 h-3 rounded w-1/2"></div>
      </div>
    ))}
  </div>
);

/**
 * Skeleton loader for graph
 */
export const GraphSkeleton: React.FC = () => (
  <div className="w-full h-full bg-muted/10 animate-pulse flex items-center justify-center">
    <div className="text-center">
      <div className="inline-block p-4 bg-muted/20 rounded-lg">
        <div className="w-12 h-12 bg-muted/30 rounded-full mx-auto mb-2 animate-spin"></div>
        <p className="text-muted text-sm">Rendering network...</p>
      </div>
    </div>
  </div>
);

/**
 * Progress bar component
 */
export const ProgressBar: React.FC<{ progress: number; label?: string }> = ({
  progress,
  label,
}) => (
  <div className="w-full">
    {label && <p className="text-xs text-muted mb-1">{label}</p>}
    <div className="h-2 bg-muted/20 rounded-full overflow-hidden">
      <div
        className="h-full bg-primary transition-all duration-300"
        style={{ width: `${Math.min(progress, 100)}%` }}
      ></div>
    </div>
  </div>
);

/**
 * Tooltip component
 */
export const Tooltip: React.FC<{
  text: string;
  children: React.ReactNode;
  position?: 'top' | 'bottom' | 'left' | 'right';
}> = ({ text, children, position = 'top' }) => {
  const positionClasses = {
    top: 'bottom-full mb-2',
    bottom: 'top-full mt-2',
    left: 'right-full mr-2',
    right: 'left-full ml-2',
  };

  return (
    <div className="relative group inline-block">
      {children}
      <div
        className={`absolute ${positionClasses[position]} hidden group-hover:block bg-foreground text-background text-xs rounded px-2 py-1 whitespace-nowrap z-10`}
      >
        {text}
      </div>
    </div>
  );
};

/**
 * Badge component
 */
export const Badge: React.FC<{
  text: string;
  variant?: 'primary' | 'secondary' | 'success' | 'warning' | 'danger';
}> = ({ text, variant = 'primary' }) => {
  const variantClasses = {
    primary: 'bg-primary/20 text-primary',
    secondary: 'bg-secondary/20 text-secondary',
    success: 'bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200',
    warning: 'bg-yellow-100 text-yellow-800 dark:bg-yellow-900 dark:text-yellow-200',
    danger: 'bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-200',
  };

  return (
    <span className={`inline-block px-2 py-1 rounded text-xs font-medium ${variantClasses[variant]}`}>
      {text}
    </span>
  );
};
