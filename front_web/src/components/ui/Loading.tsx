export function Loading({ className = 'py-12' }: { className?: string }) {
  return (
    <div className={`${className} flex items-center justify-center gap-2 text-sm text-gray-400`}>
      <div className="spinner" />
      로딩 중...
    </div>
  )
}

export function EmptyState({ message = '데이터가 없습니다', sub }: { message?: string; sub?: string }) {
  return (
    <div className="py-16 flex flex-col items-center justify-center text-center">
      <div className="mb-3 h-10 w-10 rounded-full bg-gray-100 flex items-center justify-center text-gray-300 text-xl font-light">
        —
      </div>
      <p className="text-sm font-medium text-gray-400">{message}</p>
      {sub && <p className="mt-1 text-xs text-gray-300">{sub}</p>}
    </div>
  )
}
