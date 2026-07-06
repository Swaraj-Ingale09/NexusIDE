const Skeleton = ({ className = '', variant = 'rect', count = 1 }) => {
  const base = 'animate-pulse rounded bg-surface-soft';
  const variants = {
    rect: '',
    circle: 'rounded-full',
    text: 'h-4 rounded',
    title: 'h-6 rounded w-3/4',
  };

  if (count > 1) {
    return (
      <div className="space-y-2">
        {Array.from({ length: count }).map((_, i) => (
          <div key={i} className={`${base} ${variants[variant]} ${className}`} />
        ))}
      </div>
    );
  }

  return <div className={`${base} ${variants[variant]} ${className}`} />;
};

export const StatCardSkeleton = () => (
  <div className="bg-surface border border-hairline rounded-xl p-4">
    <div className="flex items-start justify-between mb-2">
      <Skeleton className="w-9 h-9" variant="circle" />
    </div>
    <Skeleton className="h-7 w-20 mb-1" />
    <Skeleton className="h-3 w-16" />
  </div>
);

export const TableSkeleton = ({ rows = 5, cols = 6 }) => (
  <div className="bg-surface border border-hairline rounded-xl overflow-hidden">
    <div className="px-4 py-3 border-b border-hairline bg-surface-soft/50">
      <div className="flex gap-4">
        {Array.from({ length: cols }).map((_, i) => (
          <Skeleton key={i} className="h-3 flex-1" />
        ))}
      </div>
    </div>
    {Array.from({ length: rows }).map((_, r) => (
      <div key={r} className="px-4 py-3 border-b border-hairline/30">
        <div className="flex gap-4">
          {Array.from({ length: cols }).map((_, c) => (
            <Skeleton key={c} className="h-3 flex-1" />
          ))}
        </div>
      </div>
    ))}
  </div>
);

export const CardSkeleton = ({ count = 3 }) => (
  <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
    {Array.from({ length: count }).map((_, i) => (
      <div key={i} className="bg-surface border border-hairline rounded-xl p-5">
        <div className="flex items-center gap-3 mb-3">
          <Skeleton className="w-8 h-8" variant="circle" />
          <Skeleton className="h-4 w-24" />
        </div>
        <Skeleton className="h-4 w-full mb-2" />
        <Skeleton className="h-4 w-3/4" />
      </div>
    ))}
  </div>
);

export const DashboardSkeleton = () => (
  <div className="space-y-6">
    <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
      {Array.from({ length: 4 }).map((_, i) => <StatCardSkeleton key={i} />)}
    </div>
    <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
      <div className="bg-surface border border-hairline rounded-xl p-5">
        <Skeleton className="h-4 w-32 mb-4" />
        <Skeleton className="h-[120px] w-full" />
      </div>
      <div className="bg-surface border border-hairline rounded-xl p-5">
        <Skeleton className="h-4 w-32 mb-4" />
        <div className="space-y-3">
          {Array.from({ length: 4 }).map((_, i) => <Skeleton key={i} className="h-3 w-full" />)}
        </div>
      </div>
    </div>
  </div>
);

export const PageSkeleton = () => (
  <div className="max-w-[1400px] mx-auto px-4 md:px-6 py-6 space-y-6">
    <Skeleton className="h-8 w-48" variant="title" />
    <DashboardSkeleton />
  </div>
);

export default Skeleton;
