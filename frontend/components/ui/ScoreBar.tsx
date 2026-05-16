export function ScoreBar({ value }: { value: number }) {
  const width = Math.max(0, Math.min(100, Number.isFinite(value) ? value : 0));

  return (
    <div>
      <div className="mb-2 flex items-center justify-between text-xs font-medium text-slate-500">
        <span>Match score</span>
        <span>{width}%</span>
      </div>
      <div className="h-2 rounded-full bg-slate-100">
        <div className="h-2 rounded-full bg-gradient-to-r from-blue-500 to-indigo-500" style={{ width: `${width}%` }} />
      </div>
    </div>
  );
}
