"use client"

import { useState } from "react"
import type { Question } from "@/types/survey"
import { validateAnswer } from "@/lib/survey-validation"
import { Label } from "@/components/ui/label"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { cn } from "@/lib/utils"

interface QuestionDropdownProps {
  question: Question
  value?: string
  onChange: (value: string) => void
  className?: string
}

export function QuestionDropdown({ question, value, onChange, className }: QuestionDropdownProps) {
  const [error, setError] = useState<string>()
  const [touched, setTouched] = useState(false)

  const handleChange = (selectedValue: string) => {
    onChange(selectedValue)

    if (touched) {
      const validation = validateAnswer(question, selectedValue)
      setError(validation.error)
    }
  }

  const handleBlur = () => {
    setTouched(true)
    const validation = validateAnswer(question, value)
    setError(validation.error)
  }

  if (!question.answers) return null

  return (
    <div className={cn("space-y-2", className)}>
      <Label htmlFor={question.code} className="text-sm font-medium text-foreground">
        {question.title}
        {question.required && <span className="text-destructive ml-1">*</span>}
      </Label>

      {question.subtitle && <p className="text-sm text-muted-foreground">{question.subtitle}</p>}

      <Select value={value || ""} onValueChange={handleChange}>
        <SelectTrigger
          id={question.code}
          onBlur={handleBlur}
          className={cn(error && "border-destructive focus:ring-destructive")}
        >
          <SelectValue placeholder="Select an option..." />
        </SelectTrigger>
        <SelectContent>
          {question.answers.answers.map((answer) => (
            <SelectItem key={answer.code} value={answer.code}>
              {answer.title}
            </SelectItem>
          ))}
        </SelectContent>
      </Select>

      {error && <p className="text-sm text-destructive">{error}</p>}

      {question.help && !error && <p className="text-sm text-muted-foreground">{question.help}</p>}
    </div>
  )
}
