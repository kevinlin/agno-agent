"use client"

import { useState } from "react"
import type { Question } from "@/types/survey"
import { validateAnswer } from "@/lib/survey-validation"
import { Label } from "@/components/ui/label"
import { Checkbox } from "@/components/ui/checkbox"
import { cn } from "@/lib/utils"

interface QuestionMultipleSelectProps {
  question: Question
  value?: string[]
  onChange: (value: string[]) => void
  className?: string
}

export function QuestionMultipleSelect({ question, value = [], onChange, className }: QuestionMultipleSelectProps) {
  const [error, setError] = useState<string>()
  const [touched, setTouched] = useState(false)

  const handleChange = (optionCode: string, checked: boolean) => {
    let newValue: string[]

    if (checked) {
      // Check if this is an exclusive option
      const exclusiveOptions = question.answers?.exclusiveOptions || []
      if (exclusiveOptions.includes(optionCode)) {
        // If selecting an exclusive option, clear all others
        newValue = [optionCode]
      } else {
        // If selecting a regular option, remove any exclusive options first
        const filteredValue = value.filter((v) => !exclusiveOptions.includes(v))
        newValue = [...filteredValue, optionCode]
      }
    } else {
      newValue = value.filter((v) => v !== optionCode)
    }

    onChange(newValue)

    if (touched) {
      const validation = validateAnswer(question, newValue)
      setError(validation.error)
    }
  }

  const handleBlur = () => {
    setTouched(true)
    const validation = validateAnswer(question, value)
    setError(validation.error)
  }

  if (!question.answers) return null

  const exclusiveOptions = question.answers.exclusiveOptions || []

  return (
    <div className={cn("space-y-4", className)}>
      <div>
        <Label className="text-sm font-medium text-foreground">
          {question.title}
          {question.required && <span className="text-destructive ml-1">*</span>}
        </Label>

        {question.subtitle && <p className="text-sm text-muted-foreground mt-1">{question.subtitle}</p>}
      </div>

      <div className="space-y-3">
        {question.answers.answers.map((answer) => {
          const isChecked = value.includes(answer.code)
          const isExclusive = exclusiveOptions.includes(answer.code)

          return (
            <div key={answer.code} className="flex items-center space-x-3">
              <Checkbox
                id={`${question.code}-${answer.code}`}
                checked={isChecked}
                onCheckedChange={(checked) => handleChange(answer.code, checked as boolean)}
                onBlur={handleBlur}
                className="border-2 border-border data-[state=checked]:border-primary data-[state=checked]:bg-primary"
              />
              <Label
                htmlFor={`${question.code}-${answer.code}`}
                className={cn(
                  "text-sm font-normal cursor-pointer flex-1 leading-relaxed",
                  isExclusive && "font-medium text-muted-foreground",
                )}
              >
                {answer.title}
              </Label>
            </div>
          )
        })}
      </div>

      {error && <p className="text-sm text-destructive">{error}</p>}

      {question.help && !error && <p className="text-sm text-muted-foreground">{question.help}</p>}
    </div>
  )
}
