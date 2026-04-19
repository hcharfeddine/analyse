'use client';

import React from 'react';

/**
 * Loading spinner component
 */
export const LoadingSpinner: React.FC<{ message?: string }> = ({
  message = 'Processing data...',
}) => (
  <div className="flex flex-col items-center justify-center h-full w-full bg-background/80 backdrop-blur-sm z-50">
    <div className="relative flex items-center justify-center w-16 h-16 mb-6">
      <div className="absolute inset-0 rounded-full border-2 border-primary/20"></div>
      <div className="absolute inset-0 rounded-full border-t-2 border-primary animate-spin"></div>
      <div className="w-2 h-2 bg-accent rounded-full animate-pulse"></div>
    </div>
    <p className="text-muted text-xs uppercase tracking-widest mono-text">{message}</p>
  </div>
);

/**
 * Error state component
 */
export const ErrorState: React.FC<{ error: string; onRetry?: () => void }> = ({
  error,
  onRetry,
}) => (
  <div className="flex items-center justify-center h-full w-full bg-[#0d070b] p-6">
    <div className="max-w-md w-full bg-black/40 border border-red-500/20 rounded-xl p-8 text-center backdrop-blur-md shadow-[0_0_40px_rgba(239,68,68,0.05)]">
      <div style={{width: '48px', height: '48px', flexShrink: 0}} className="bg-red-500/10 rounded-full flex items-center justify-center mx-auto mb-6">
        <svg width="24" height="24" style={{width: '24px', height: '24px', flexShrink: 0, color: '#ef4444'}} fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z"></path></svg>
      </div>
      <h3 className="text-lg font-medium text-white mb-2 tracking-tight">
        System Error
      </h3>
      <p className="text-red-300/80 text-sm mb-8 leading-relaxed">{error}</p>
      {onRetry && (
        <button
          onClick={onRetry}
          className="inline-flex items-center justify-center px-6 py-2.5 rounded-lg bg-white/5 hover:bg-white/10 border border-white/10 text-white text-sm font-medium transition-all"
        >
          Initialize Retry
        </button>
      )}
    </div>
  </div>
);

/**
 * Empty state component
 */
export const EmptyState: React.FC<{ message: string }> = ({
  message
}) => (
  <div className="flex items-center justify-center h-full w-full text-center p-6">
    <div className="max-w-sm">
      <div style={{width: '64px', height: '64px', flexShrink: 0}} className="bg-white/5 rounded-full flex items-center justify-center mx-auto mb-6 border border-white/10">
        <svg width="32" height="32" style={{width: '32px', height: '32px', flexShrink: 0, color: 'var(--color-muted)', opacity: 0.5}} fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="1.5" d="M20 13V6a2 2 0 00-2-2H6a2 2 0 00-2 2v7m16 0v5a2 2 0 01-2 2H6a2 2 0 01-2-2v-5m16 0h-2.586a1 1 0 00-.707.293l-2.414 2.414a1 1 0 01-.707.293h-3.172a1 1 0 01-.707-.293l-2.414-2.414A1 1 0 006.586 13H4"></path></svg>
      </div>
      <p className="text-muted text-sm tracking-wide">{message}</p>
    </div>
  </div>
);

/**
 * Skeleton loader for papers list
 */
export const PaperSkeleton: React.FC = () => (
  <div className="space-y-3">
    {[...Array(4)].map((_, i) => (
      <div key={i} className="bg-black/20 border border-white/5 rounded-xl h-24 p-4 space-y-3 relative overflow-hidden group">
        <div className="absolute inset-0 shimmer opacity-50"></div>
        <div className="bg-white/10 h-4 rounded w-3/4"></div>
        <div className="bg-white/5 h-3 rounded w-1/2 mt-4"></div>
      </div>
    ))}
  </div>
);

/**
 * Skeleton loader for graph
 */
export const GraphSkeleton: React.FC = () => (
  <div className="w-full h-full bg-[#030712] relative overflow-hidden flex items-center justify-center">
    <div className="absolute inset-0 opacity-[0.03]" style={{ backgroundImage: 'radial-gradient(circle at center, #ffffff 1px, transparent 1px)', backgroundSize: '24px 24px' }}></div>
    <div className="text-center z-10">
      <div className="relative w-20 h-20 mx-auto mb-6">
        <div className="absolute inset-0 rounded-full border border-primary/20 animate-[ping_2s_cubic-bezier(0,0,0.2,1)_infinite]"></div>
        <div className="absolute inset-2 rounded-full border border-secondary/30 animate-[ping_2s_cubic-bezier(0,0,0.2,1)_infinite_0.5s]"></div>
        <div className="absolute inset-0 flex items-center justify-center">
          <div className="w-2 h-2 rounded-full bg-accent"></div>
        </div>
      </div>
      <p className="text-primary/70 text-xs uppercase tracking-[0.2em] mono-text">Compiling Network</p>
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
    {label && (
      <div className="flex justify-between items-end mb-2">
        <p className="text-[10px] text-muted uppercase tracking-wider mono-text">{label}</p>
        <p className="text-[10px] text-primary font-medium mono-text">{Math.round(progress)}%</p>
      </div>
    )}
    <div className="h-1 bg-white/10 rounded-full overflow-hidden">
      <div
        className="h-full bg-gradient-to-r from-primary to-accent transition-all duration-500 ease-out"
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
    top: 'bottom-full mb-2.5 left-1/2 -translate-x-1/2',
    bottom: 'top-full mt-2.5 left-1/2 -translate-x-1/2',
    left: 'right-full mr-2.5 top-1/2 -translate-y-1/2',
    right: 'left-full ml-2.5 top-1/2 -translate-y-1/2',
  };

  return (
    <div className="relative group inline-flex">
      {children}
      <div
        className={`absolute ${positionClasses[position]} opacity-0 group-hover:opacity-100 transition-opacity duration-200 pointer-events-none bg-[#1a202c] border border-white/10 text-white/90 text-[10px] mono-text uppercase tracking-wider rounded-md px-3 py-1.5 whitespace-nowrap z-50 shadow-xl`}
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
  variant?: 'primary' | 'secondary' | 'success' | 'warning' | 'danger' | 'outline';
}> = ({ text, variant = 'primary' }) => {
  const variantClasses = {
    primary: 'bg-primary/10 text-primary border border-primary/20',
    secondary: 'bg-secondary/10 text-secondary border border-secondary/20',
    success: 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/20',
    warning: 'bg-amber-500/10 text-amber-400 border border-amber-500/20',
    danger: 'bg-red-500/10 text-red-400 border border-red-500/20',
    outline: 'bg-transparent text-muted border border-white/10',
  };

  return (
    <span className={`inline-flex px-2 py-0.5 rounded text-[10px] uppercase tracking-wider mono-text font-medium ${variantClasses[variant]}`}>
      {text}
    </span>
  );
};
