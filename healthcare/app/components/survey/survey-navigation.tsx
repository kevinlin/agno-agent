"use client"

import { Button } from "@/components/ui/button"
import { ChevronLeft, ChevronRight } from "lucide-react"
import { cn } from "@/lib/utils"

interface SurveyNavigationProps {
  onPrevious: () => void
  onNext: () => void
  canGoBack: boolean
  canGoForward: boolean
  isLastQuestion: boolean
  className?: string
}

export function SurveyNavigation({
  onPrevious,
  onNext,
  canGoBack,
  canGoForward,
  isLastQuestion,
  className,
}: SurveyNavigationProps) {
  return (
    <div className={cn("flex items-center justify-between gap-4", className)}>
      <Button
        variant="outline"
        onClick={onPrevious}
        disabled={!canGoBack}
        className="flex items-center gap-2 bg-transparent"
      >
        <ChevronLeft className="h-4 w-4" />
        Back
      </Button>

      <Button onClick={onNext} disabled={!canGoForward} className="flex items-center gap-2 min-w-[100px]">
        {isLastQuestion ? "Review" : "Next"}
        {!isLastQuestion && <ChevronRight className="h-4 w-4" />}
      </Button>
    </div>
  )
}
