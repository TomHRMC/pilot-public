/**
 * MonthDeferredState — Placeholder for the deferred Month view
 *
 * Location: apps/web/src/features/dispatch-board/components/MonthDeferredState.tsx
 *
 * Month view is deferred to post-beta per batch-beta-v1-fixes-b5-design.md §G.
 * Renders a friendly "coming soon" message instead of a blank or broken grid.
 */

export function MonthDeferredState() {
  return (
    <div className="flex flex-col items-center justify-center h-64 text-center">
      <div className="text-4xl mb-4" aria-hidden="true">
        📅
      </div>
      <h3 className="text-lg font-medium text-neutral-700 mb-2">
        Month view coming soon
      </h3>
      <p className="text-sm text-neutral-500 max-w-xs">
        Switch to Day, 4-Day, or Week view to manage your schedule.
      </p>
    </div>
  );
}
