"use client"

import { useState } from "react"
import type { Question } from "@/types/survey"
import { validateAnswer } from "@/lib/survey-validation"
import { Label } from "@/components/ui/label"
import { RadioGroup, RadioGroupItem } from "@/components/ui/radio-group"
import { cn } from "@/lib/utils"

interface QuestionSingleSelectProps {
  question: Question
  value?: string
  onChange: (value: string) => void
  className?: string
}

export function QuestionSingleSelect({ question, value, onChange, className }: QuestionSingleSelectProps) {
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
    <div className={cn("space-y-4", className)}>
      <div>
        <Label className="text-sm font-medium text-foreground">
          {question.title}
          {question.required && <span className="text-destructive ml-1">*</span>}
        </Label>

        {question.subtitle && <p className="text-sm text-muted-foreground mt-1">{question.subtitle}</p>}
      </div>

      <RadioGroup value={value || ""} onValueChange={handleChange} className="space-y-3">
        {question.answers.answers.map((answer) => (
          <div key={answer.code} className="flex items-center space-x-3">
            <RadioGroupItem
              value={answer.code}
              id={`${question.code}-${answer.code}`}
              onBlur={handleBlur}
              className="border-2 border-border data-[state=checked]:border-primary data-[state=checked]:bg-primary"
            />
            <Label
              htmlFor={`${question.code}-${answer.code}`}
              className="text-sm font-normal cursor-pointer flex-1 leading-relaxed"
            >
              {answer.title}
            </Label>
          </div>
        ))}
      </RadioGroup>

      {error && <p className="text-sm text-destructive">{error}</p>}

      {question.help && !error && <p className="text-sm text-muted-foreground">{question.help}</p>}
    </div>
  )
}
