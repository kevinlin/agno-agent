import { 
  BranchingRule, 
  Condition, 
  BranchingAction, 
  Question, 
  Survey,
  ConditionOperator 
} from '../types/survey'

/**
 * Evaluates a single condition against the current answers
 */
export function evaluateCondition(
  condition: Condition, 
  answers: Record<string, any>
): boolean {
  const { operator, question_code, value, conditions } = condition

  // Handle compound conditions (and/or/not)
  if (operator === 'and') {
    return conditions?.every(c => evaluateCondition(c, answers)) ?? false
  }
  
  if (operator === 'or') {
    return conditions?.some(c => evaluateCondition(c, answers)) ?? false
  }
  
  if (operator === 'not') {
    return conditions?.length === 1 ? !evaluateCondition(conditions[0], answers) : false
  }

  // For non-compound conditions, question_code is required
  if (!question_code) {
    return false
  }

  const answerValue = answers[question_code]

  // Handle cases where answer doesn't exist
  if (answerValue === undefined || answerValue === null) {
    return false
  }

  // Evaluate simple conditions
  switch (operator) {
    case 'equals':
      return answerValue === value

    case 'one_of':
      return Array.isArray(value) && value.includes(answerValue)

    case 'includes':
      return Array.isArray(answerValue) && answerValue.includes(value)

    case 'gt':
      return Number(answerValue) > Number(value)

    case 'gte':
      return Number(answerValue) >= Number(value)

    case 'lt':
      return Number(answerValue) < Number(value)

    case 'lte':
      return Number(answerValue) <= Number(value)

    default:
      console.warn(`Unknown condition operator: ${operator}`)
      return false
  }
}

/**
 * Evaluates a branching rule against current answers
 */
export function evaluateBranchingRule(
  rule: BranchingRule, 
  answers: Record<string, any>
): boolean {
  return evaluateCondition(rule.condition, answers)
}

/**
 * Gets all applicable branching rules for the current state
 */
export function getApplicableBranchingRules(
  rules: BranchingRule[], 
  answers: Record<string, any>
): BranchingRule[] {
  return rules
    .filter(rule => evaluateBranchingRule(rule, answers))
    .sort((a, b) => (a.priority ?? 0) - (b.priority ?? 0))
}

/**
 * Calculates which questions should be visible based on:
 * 1. Question-level visible_if conditions
 * 2. Survey-level branching rules
 */
export function getVisibleQuestions(
  survey: Survey, 
  answers: Record<string, any>
): Question[] {
  const { questions, branching_rules = [] } = survey
  
  // Start with all questions
  let visibleQuestions = [...questions]

  // Step 1: Apply question-level visibility conditions
  visibleQuestions = visibleQuestions.filter(question => {
    if (!question.visible_if) {
      return true
    }
    return evaluateCondition(question.visible_if, answers)
  })

  // Step 2: Apply survey-level branching rules
  const applicableRules = getApplicableBranchingRules(branching_rules, answers)
  
  for (const rule of applicableRules) {
    visibleQuestions = applyBranchingAction(visibleQuestions, rule.action, questions)
  }

  return visibleQuestions
}

/**
 * Applies a branching action to modify the visible questions list
 */
function applyBranchingAction(
  currentVisible: Question[],
  action: BranchingAction,
  allQuestions: Question[]
): Question[] {
  const { type, target } = action

  switch (type) {
    case 'skip_questions': {
      const targetCodes = Array.isArray(target) ? target : [target]
      return currentVisible.filter(q => !targetCodes.includes(q.code))
    }

    case 'goto_question': {
      const targetCode = Array.isArray(target) ? target[0] : target
      const targetIndex = allQuestions.findIndex(q => q.code === targetCode)
      if (targetIndex === -1) return currentVisible
      
      // Show all questions up to and including the target
      const questionCodesToShow = allQuestions
        .slice(0, targetIndex + 1)
        .map(q => q.code)
      
      return currentVisible.filter(q => questionCodesToShow.includes(q.code))
    }

    case 'require_questions': {
      const targetCodes = Array.isArray(target) ? target : [target]
      const questionsToAdd = allQuestions.filter(q => 
        targetCodes.includes(q.code) && 
        !currentVisible.some(vq => vq.code === q.code)
      )
      return [...currentVisible, ...questionsToAdd]
    }

    case 'insert_questions_after': {
      // This would need additional data to specify where to insert
      // For now, just add the questions to the end
      const targetCodes = Array.isArray(target) ? target : [target]
      const questionsToAdd = allQuestions.filter(q => 
        targetCodes.includes(q.code) && 
        !currentVisible.some(vq => vq.code === q.code)
      )
      return [...currentVisible, ...questionsToAdd]
    }

    default:
      console.warn(`Unknown branching action type: ${type}`)
      return currentVisible
  }
}

/**
 * Determines which answers should be voided when questions become hidden
 */
export function getVoidedAnswers(
  previouslyVisible: Question[],
  currentlyVisible: Question[],
  answers: Record<string, any>
): string[] {
  const previousCodes = new Set(previouslyVisible.map(q => q.code))
  const currentCodes = new Set(currentlyVisible.map(q => q.code))
  
  const hiddenQuestionCodes: string[] = []
  
  for (const code of previousCodes) {
    if (!currentCodes.has(code)) {
      hiddenQuestionCodes.push(code)
    }
  }
  
  // Return only the codes that actually have answers to void
  return hiddenQuestionCodes.filter(code => answers[code] !== undefined)
}

/**
 * Calculates the next question index after applying branching logic
 */
export function getNextQuestionIndex(
  currentIndex: number,
  visibleQuestions: Question[],
  allQuestions: Question[]
): number {
  // Simple next question logic - just go to the next visible question
  if (currentIndex + 1 < visibleQuestions.length) {
    return currentIndex + 1
  }
  
  // If we're at the end, return the current index
  return currentIndex
}

/**
 * Calculates progress percentage based on visible questions
 */
export function calculateProgress(
  answers: Record<string, any>,
  visibleQuestions: Question[]
): number {
  if (visibleQuestions.length === 0) return 0
  
  const answeredCount = visibleQuestions.filter(q => 
    answers[q.code] !== undefined && 
    answers[q.code] !== null && 
    answers[q.code] !== ''
  ).length
  
  return Math.round((answeredCount / visibleQuestions.length) * 100)
}

/**
 * Comprehensive state update that handles visibility changes and answer voiding
 */
export interface BranchingStateUpdate {
  visibleQuestions: Question[]
  voidedAnswerCodes: string[]
  updatedAnswers: Record<string, any>
  progressPercentage: number
}

export function updateSurveyState(
  survey: Survey,
  currentAnswers: Record<string, any>,
  previouslyVisibleQuestions: Question[]
): BranchingStateUpdate {
  // Calculate new visible questions
  const visibleQuestions = getVisibleQuestions(survey, currentAnswers)
  
  // Determine which answers need to be voided
  const voidedAnswerCodes = getVoidedAnswers(
    previouslyVisibleQuestions, 
    visibleQuestions, 
    currentAnswers
  )
  
  // Create updated answers with voided answers removed
  const updatedAnswers = { ...currentAnswers }
  for (const code of voidedAnswerCodes) {
    delete updatedAnswers[code]
  }
  
  // Calculate progress based on new state
  const progressPercentage = calculateProgress(updatedAnswers, visibleQuestions)
  
  return {
    visibleQuestions,
    voidedAnswerCodes,
    updatedAnswers,
    progressPercentage
  }
}
