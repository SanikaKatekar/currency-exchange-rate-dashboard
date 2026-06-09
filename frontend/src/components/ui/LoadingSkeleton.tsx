/** Loading placeholders shown while summary data is being fetched. */
export function LoadingSkeleton() {
  return (
    <div className="space-y-6" aria-live="polite" aria-busy="true">
      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
        {Array.from({ length: 4 }).map((_, index) => (
          <div key={index} className="glass-panel h-32 rounded-3xl skeleton" />
        ))}
      </div>
      <div className="grid gap-6 xl:grid-cols-[1.2fr_0.8fr]">
        <div className="glass-panel h-[22rem] rounded-3xl skeleton" />
        <div className="glass-panel h-[22rem] rounded-3xl skeleton" />
      </div>
    </div>
  );
}
