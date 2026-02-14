interface LoadingStateProps {
  titleWidth?: string
  cardCount?: number
  listCount?: number
  variant?: 'cards' | 'list' | 'panel'
}

export function LoadingState({
  titleWidth = 'w-48',
  cardCount = 4,
  listCount = 3,
  variant = 'cards',
}: LoadingStateProps) {
  return (
    <div className="p-8">
      <div className="animate-pulse space-y-6">
        <div className={`h-8 bg-surface1 rounded ${titleWidth}`} />
        {variant === 'cards' && (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
            {Array.from({ length: cardCount }).map((_, i) => (
              <div key={i} className="h-40 bg-surface1 rounded-lg" />
            ))}
          </div>
        )}
        {variant === 'list' && (
          <div className="space-y-4">
            {Array.from({ length: listCount }).map((_, i) => (
              <div key={i} className="h-40 bg-surface1 rounded-lg" />
            ))}
          </div>
        )}
        {variant === 'panel' && (
          <div className="h-96 bg-surface1 rounded-lg" />
        )}
      </div>
    </div>
  )
}
