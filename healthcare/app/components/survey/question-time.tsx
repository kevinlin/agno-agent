"use client"

import { useState } from "react"
import type { Question } from "@/types/survey"
import { validateAnswer } from "@/lib/survey-validation"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { cn } from "@/lib/utils"

interface QuestionTimeProps {
  question: Question
  value?: number
  onChange: (value: number) => void
  className?: string
}

export function QuestionTime({ question, value, onChange, className }: QuestionTimeProps) {
  const [error, setError] = useState<string>()
  const [touched, setTouched] = useState(false)
  const [displayValue, setDisplayValue] = useState(() => {
    if (value) {
      const hours = Math.floor(value / 60)
      const minutes = value % 60
      return `${hours.toString().padStart(2, "0")}:${minutes.toString().padStart(2, "0")}`
    }
    return ""
  })

  const handleChange = (timeString: string) => {
    setDisplayValue(timeString)

    // Parse HH:MM format to minutes
    const [hours, minutes] = timeString.split(":").map(Number)
    if (!isNaN(hours) && !isNaN(minutes)) {
      const totalMinutes = hours * 60 + minutes
      onChange(totalMinutes)

      if (touched) {
        const validation = validateAnswer(question, totalMinutes)
        setError(validation.error)
      }
    }
  }

  const handleBlur = () => {
    setTouched(true)
    const validation = validateAnswer(question, value)
    setError(validation.error)
  }

  return (
    <div className={cn("space-y-2", className)}>
      <Label htmlFor={question.code} className="text-sm font-medium text-foreground">
        {question.title}
        {question.required && <span className="text-destructive ml-1">*</span>}
      </Label>

      {question.subtitle && <p className="text-sm text-muted-foreground">{question.subtitle}</p>}

      <div className="relative">
        <Input
          id={question.code}
          type="time"
          value={displayValue}
          onChange={(e) => handleChange(e.target.value)}
          onBlur={handleBlur}
          className={cn("pr-16", error && "border-destructive focus-visible:ring-destructive")}
        />

        <div className="absolute right-3 top-1/2 -translate-y-1/2 text-sm text-muted-foreground">HH:MM</div>
      </div>

      {error && <p className="text-sm text-destructive">{error}</p>}

      {question.help && !error && <p className="text-sm text-muted-foreground">{question.help}</p>}
    </div>
  )
}
