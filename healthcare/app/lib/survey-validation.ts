import type { Question } from "@/types/survey"

export interface ValidationResult {
  isValid: boolean
  error?: string
}

export function validateAnswer(question: Question, value: any): ValidationResult {
  // Check if required field is empty
  if (question.required && (value === undefined || value === null || value === "")) {
    return {
      isValid: false,
      error: "This field is required",
    }
  }

  // If not required and empty, it's valid
  if (!question.required && (value === undefined || value === null || value === "")) {
    return { isValid: true }
  }

  // Validate based on question type
  switch (question.type) {
    case "INPUT":
      return validateInputAnswer(question, value)
    case "SINGLE_SELECT":
      return validateSingleSelectAnswer(question, value)
    case "MULTIPLE_SELECT":
      return validateMultipleSelectAnswer(question, value)
    case "DROPDOWN":
      return validateDropdownAnswer(question, value)
    case "TIME":
      return validateTimeAnswer(question, value)
    default:
      return { isValid: true }
  }
}

function validateInputAnswer(question: Question, value: any): ValidationResult {
  if (question.unit === "INTEGER_NUMBER" || question.unit === "DECIMAL_NUMBER") {
    const numValue = Number(value)

    if (isNaN(numValue)) {
      return {
        isValid: false,
        error: "Please enter a valid number",
      }
    }

    if (question.constraints) {
      if (question.constraints.min !== undefined && numValue < question.constraints.min) {
        return {
          isValid: false,
          error: `Value must be at least ${question.constraints.min}`,
        }
      }

      if (question.constraints.max !== undefined && numValue > question.constraints.max) {
        return {
          isValid: false,
          error: `Value must be at most ${question.constraints.max}`,
        }
      }
    }
  }

  if (question.unit === "TEXT") {
    const strValue = String(value)

    if (question.constraints) {
      if (question.constraints.minLength !== undefined && strValue.length < question.constraints.minLength) {
        return {
          isValid: false,
          error: `Must be at least ${question.constraints.minLength} characters`,
        }
      }

      if (question.constraints.maxLength !== undefined && strValue.length > question.constraints.maxLength) {
        return {
          isValid: false,
          error: `Must be at most ${question.constraints.maxLength} characters`,
        }
      }
    }
  }

  return { isValid: true }
}

function validateSingleSelectAnswer(question: Question, value: any): ValidationResult {
  if (!question.answers) {
    return { isValid: true }
  }

  const validOptions = question.answers.answers.map((answer) => answer.code)

  if (!validOptions.includes(value)) {
    return {
      isValid: false,
      error: "Please select a valid option",
    }
  }

  return { isValid: true }
}

function validateMultipleSelectAnswer(question: Question, value: any): ValidationResult {
  if (!Array.isArray(value)) {
    return {
      isValid: false,
      error: "Please select at least one option",
    }
  }

  if (!question.answers) {
    return { isValid: true }
  }

  const validOptions = question.answers.answers.map((answer) => answer.code)
  const exclusiveOptions = question.answers.exclusiveOptions || []

  // Check if all selected values are valid options
  for (const selectedValue of value) {
    if (!validOptions.includes(selectedValue)) {
      return {
        isValid: false,
        error: "Invalid option selected",
      }
    }
  }

  // Check exclusive options logic
  const hasExclusiveOption = value.some((v) => exclusiveOptions.includes(v))
  const hasNonExclusiveOption = value.some((v) => !exclusiveOptions.includes(v))

  if (hasExclusiveOption && hasNonExclusiveOption) {
    return {
      isValid: false,
      error: "Cannot select exclusive option with other options",
    }
  }

  return { isValid: true }
}

function validateDropdownAnswer(question: Question, value: any): ValidationResult {
  return validateSingleSelectAnswer(question, value)
}

function validateTimeAnswer(question: Question, value: any): ValidationResult {
  const numValue = Number(value)

  if (isNaN(numValue) || numValue < 0) {
    return {
      isValid: false,
      error: "Please enter a valid time in minutes",
    }
  }

  if (question.constraints) {
    if (question.constraints.min !== undefined && numValue < question.constraints.min) {
      return {
        isValid: false,
        error: `Time must be at least ${question.constraints.min} minutes`,
      }
    }

    if (question.constraints.max !== undefined && numValue > question.constraints.max) {
      return {
        isValid: false,
        error: `Time must be at most ${question.constraints.max} minutes`,
      }
    }
  }

  return { isValid: true }
}
