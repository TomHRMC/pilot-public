/**
 * WipSkeleton — Loading skeleton for the WIP report
 *
 * Location: apps/web/src/features/wip/components/WipSkeleton.tsx
 *
 * 4 skeleton metric cards + 8 skeleton table rows.
 * animate-pulse respects prefers-reduced-motion via motion-reduce:animate-none.
 *
 * Per batch-up-1-ui-design-spec.md §5.1 + §9.8.
 */

const skeletonBar =
  "bg-neutral-200 animate-pulse rounded motion-reduce:animate-none";
const cardBase = "rounded-lg border border-neutral-200 bg-white p-4";

export function WipSkeleton() {
  return (
    <div className="space-y-6">
      {/* 4 skeleton metric cards */}
      <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
        {Array.from({ length: 4 }).map((_, i) => (
          <div key={i} className={cardBase}>
            <div className={`h-4 w-24 ${skeletonBar}`} />
            <div className={`h-8 w-16 ${skeletonBar} mt-2`} />
          </div>
        ))}
      </div>

      {/* Skeleton table — header + 8 rows */}
      <div className="overflow-x-auto rounded-lg border border-neutral-200 bg-white">
        <table
          className="w-full table-fixed"
          aria-label="Loading work-in-progress report"
        >
          <thead className="bg-neutral-50 border-b border-neutral-200">
            <tr>
              {Array.from({ length: 9 }).map((_, i) => (
                <th
                  key={i}
                  className="px-4 py-3 text-left text-xs font-semibold text-neutral-500 uppercase tracking-wide"
                >
                  <div className={`h-4 w-20 ${skeletonBar}`} />
                </th>
              ))}
            </tr>
          </thead>
          <tbody className="divide-y divide-neutral-100">
            {Array.from({ length: 8 }).map((_, rowIdx) => (
              <tr key={rowIdx} className="h-12">
                {Array.from({ length: 9 }).map((_, cellIdx) => (
                  <td key={cellIdx} className="px-4 py-3">
                    <div
                      className={`h-4 ${skeletonBar}`}
                      style={{ width: `${30 + ((cellIdx * 7) % 50)}%` }}
                    />
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
