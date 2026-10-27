export function Pagination({page,count,onChange}:{page:number;count:number;onChange:(page:number)=>void}) {
  const pages=Math.max(1,Math.ceil(count/20));
  return <nav aria-label="Pagination" className="flex items-center justify-between rounded-xl border bg-white p-4 text-sm">
    <span>{count} results · Page {page} of {pages}</span>
    <div className="flex gap-2"><button disabled={page<=1} onClick={()=>onChange(page-1)} className="rounded border px-3 py-2 disabled:opacity-40">Previous</button>
      <button disabled={page>=pages} onClick={()=>onChange(page+1)} className="rounded border px-3 py-2 disabled:opacity-40">Next</button></div>
  </nav>;
}
