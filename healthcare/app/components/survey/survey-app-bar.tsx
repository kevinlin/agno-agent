"use client"

import { Progress } from "@/components/ui/progress"
import { Button } from "@/components/ui/button"
import { Menu, X, Save } from "lucide-react"
import type { Survey } from "@/types/survey"

interface SurveyAppBarProps {
  survey: Survey
  currentQuestion: number
  totalQuestions: number
  progressPercentage: number
  showSidebar: boolean
  onToggleSidebar: () => void
  onSave?: () => void
  isSaving?: boolean
  lastSaved?: Date | null
  surveyMode?: "question" | "review" | "complete"
}

export function SurveyAppBar({
  survey,
  currentQuestion,
  totalQuestions,
  progressPercentage,
  showSidebar,
  onToggleSidebar,
  onSave,
  isSaving,
  lastSaved,
  surveyMode = "question",
}: SurveyAppBarProps) {
  const getTitle = () => {
    switch (surveyMode) {
      case "review":
        return "Review Your Answers"
      case "complete":
        return "Survey Complete"
      default:
        return survey.title
    }
  }

  const getSubtitle = () => {
    switch (surveyMode) {
      case "review":
        return "Please review your responses before submitting"
      case "complete":
        return "Thank you for completing the survey"
      default:
        return `Question ${currentQuestion} of ${totalQuestions}`
    }
  }

  return (
    <div className="app-bar-gradient text-white shadow-lg sticky top-0 z-50">
      <div className="container mx-auto px-4 py-4">
        <div className="flex items-center justify-between">
          {/* Left section - Menu and Title */}
          <div className="flex items-center space-x-4 flex-1">
            <Button
              variant="ghost"
              size="icon"
              onClick={onToggleSidebar}
              className="lg:hidden text-white hover:bg-white/20"
            >
              {showSidebar ? <X className="h-5 w-5" /> : <Menu className="h-5 w-5" />}
            </Button>

            <div className="flex-1 min-w-0">
              <h1 className="text-xl font-bold text-white truncate">{getTitle()}</h1>
              <p className="text-white/80 text-sm">{getSubtitle()}</p>
            </div>
          </div>

          {/* Right section - Progress and Save */}
          <div className="flex items-center space-x-4">
            {surveyMode === "question" && (
              <>
                {/* Progress bar for larger screens */}
                <div className="hidden md:flex items-center space-x-3 min-w-0">
                  <div className="w-32 lg:w-48">
                    <Progress value={progressPercentage} className="h-2 bg-white/20" />
                  </div>
                  <span className="text-white/90 text-sm font-medium whitespace-nowrap">
                    {Math.round(progressPercentage)}%
                  </span>
                </div>

                {/* Save button */}
                {onSave && (
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={onSave}
                    disabled={isSaving}
                    className="text-white hover:bg-white/20 hidden lg:flex"
                  >
                    <Save className="h-4 w-4 mr-2" />
                    {isSaving ? "Saving..." : "Save"}
                  </Button>
                )}
              </>
            )}
          </div>
        </div>

        {/* Mobile progress bar */}
        {surveyMode === "question" && (
          <div className="md:hidden mt-3 flex items-center space-x-3">
            <Progress value={progressPercentage} className="flex-1 h-2 bg-white/20" />
            <span className="text-white/90 text-sm font-medium">{Math.round(progressPercentage)}%</span>
          </div>
        )}

        {/* Last saved indicator */}
        {lastSaved && surveyMode === "question" && (
          <div className="mt-2 text-white/70 text-xs">Last saved: {lastSaved.toLocaleTimeString()}</div>
        )}
      </div>
    </div>
  )
}
