import {
  evaluateCondition,
  evaluateBranchingRule,
  getApplicableBranchingRules,
  getVisibleQuestions,
  getVoidedAnswers,
  calculateProgress,
  updateSurveyState,
} from '../branching'
import type { 
  Condition, 
  BranchingRule, 
  Survey, 
  Question 
} from '@/types/survey'

describe('Branching Logic', () => {
  // Sample survey data for testing
  const mockQuestions: Question[] = [
    {
      type: 'SINGLE_SELECT',
      code: 'q1',
      title: 'Are you a smoker?',
      required: true,
      answers: {
        answers: [
          { code: 'yes', title: 'Yes' },
          { code: 'no', title: 'No' },
        ],
      },
    },
    {
      type: 'INPUT',
      code: 'q2',
      title: 'How many cigarettes per day?',
      required: true,
      unit: 'INTEGER_NUMBER',
      visible_if: {
        operator: 'equals',
        question_code: 'q1',
        value: 'yes',
      },
    },
    {
      type: 'SINGLE_SELECT',
      code: 'q3',
      title: 'Your age range?',
      required: true,
      answers: {
        answers: [
          { code: 'young', title: 'Under 30' },
          { code: 'middle', title: '30-50' },
          { code: 'older', title: 'Over 50' },
        ],
      },
    },
    {
      type: 'INPUT',
      code: 'q4',
      title: 'Your BMI?',
      required: false,
      unit: 'DECIMAL_NUMBER',
    },
  ]

  const mockSurvey: Survey = {
    code: 'test',
    type: 'TEST',
    version: '1.0.0',
    title: 'Test Survey',
    questions: mockQuestions,
    branching_rules: [
      {
        id: 'rule1',
        condition: {
          operator: 'equals',
          question_code: 'q3',
          value: 'young',
        },
        action: {
          type: 'skip_questions',
          target: ['q4'],
        },
        priority: 1,
      },
      {
        id: 'rule2',
        condition: {
          operator: 'gt',
          question_code: 'q2',
          value: 20,
        },
        action: {
          type: 'require_questions',
          target: ['q4'],
        },
        priority: 2,
      },
    ],
  }

  describe('evaluateCondition', () => {
    it('should evaluate equals condition correctly', () => {
      const condition: Condition = {
        operator: 'equals',
        question_code: 'q1',
        value: 'yes',
      }
      const answers = { q1: 'yes' }
      expect(evaluateCondition(condition, answers)).toBe(true)
      
      const answersNo = { q1: 'no' }
      expect(evaluateCondition(condition, answersNo)).toBe(false)
    })

    it('should evaluate one_of condition correctly', () => {
      const condition: Condition = {
        operator: 'one_of',
        question_code: 'q3',
        value: ['young', 'middle'],
      }
      expect(evaluateCondition(condition, { q3: 'young' })).toBe(true)
      expect(evaluateCondition(condition, { q3: 'middle' })).toBe(true)
      expect(evaluateCondition(condition, { q3: 'older' })).toBe(false)
    })

    it('should evaluate includes condition correctly', () => {
      const condition: Condition = {
        operator: 'includes',
        question_code: 'q1',
        value: 'option1',
      }
      const answers = { q1: ['option1', 'option2'] }
      expect(evaluateCondition(condition, answers)).toBe(true)
      
      const answersNo = { q1: ['option2', 'option3'] }
      expect(evaluateCondition(condition, answersNo)).toBe(false)
    })

    it('should evaluate numeric comparison conditions correctly', () => {
      const answers = { q2: '25' }
      
      expect(evaluateCondition({
        operator: 'gt',
        question_code: 'q2',
        value: 20,
      }, answers)).toBe(true)

      expect(evaluateCondition({
        operator: 'gte',
        question_code: 'q2',
        value: 25,
      }, answers)).toBe(true)

      expect(evaluateCondition({
        operator: 'lt',
        question_code: 'q2',
        value: 30,
      }, answers)).toBe(true)

      expect(evaluateCondition({
        operator: 'lte',
        question_code: 'q2',
        value: 25,
      }, answers)).toBe(true)
    })

    it('should evaluate compound and condition correctly', () => {
      const condition: Condition = {
        operator: 'and',
        conditions: [
          {
            operator: 'equals',
            question_code: 'q1',
            value: 'yes',
          },
          {
            operator: 'gt',
            question_code: 'q2',
            value: 10,
          },
        ],
      }
      
      expect(evaluateCondition(condition, { q1: 'yes', q2: '15' })).toBe(true)
      expect(evaluateCondition(condition, { q1: 'no', q2: '15' })).toBe(false)
      expect(evaluateCondition(condition, { q1: 'yes', q2: '5' })).toBe(false)
    })

    it('should evaluate compound or condition correctly', () => {
      const condition: Condition = {
        operator: 'or',
        conditions: [
          {
            operator: 'equals',
            question_code: 'q1',
            value: 'yes',
          },
          {
            operator: 'equals',
            question_code: 'q3',
            value: 'young',
          },
        ],
      }
      
      expect(evaluateCondition(condition, { q1: 'yes', q3: 'older' })).toBe(true)
      expect(evaluateCondition(condition, { q1: 'no', q3: 'young' })).toBe(true)
      expect(evaluateCondition(condition, { q1: 'no', q3: 'older' })).toBe(false)
    })

    it('should evaluate not condition correctly', () => {
      const condition: Condition = {
        operator: 'not',
        conditions: [
          {
            operator: 'equals',
            question_code: 'q1',
            value: 'yes',
          },
        ],
      }
      
      expect(evaluateCondition(condition, { q1: 'no' })).toBe(true)
      expect(evaluateCondition(condition, { q1: 'yes' })).toBe(false)
    })

    it('should return false for missing answers', () => {
      const condition: Condition = {
        operator: 'equals',
        question_code: 'q1',
        value: 'yes',
      }
      expect(evaluateCondition(condition, {})).toBe(false)
      expect(evaluateCondition(condition, { q1: null })).toBe(false)
      expect(evaluateCondition(condition, { q1: undefined })).toBe(false)
    })
  })

  describe('evaluateBranchingRule', () => {
    it('should evaluate branching rule correctly', () => {
      const rule: BranchingRule = {
        id: 'test-rule',
        condition: {
          operator: 'equals',
          question_code: 'q1',
          value: 'yes',
        },
        action: {
          type: 'skip_questions',
          target: ['q2'],
        },
      }
      
      expect(evaluateBranchingRule(rule, { q1: 'yes' })).toBe(true)
      expect(evaluateBranchingRule(rule, { q1: 'no' })).toBe(false)
    })
  })

  describe('getApplicableBranchingRules', () => {
    it('should return applicable rules sorted by priority', () => {
      const rules: BranchingRule[] = [
        {
          id: 'rule1',
          condition: { operator: 'equals', question_code: 'q1', value: 'yes' },
          action: { type: 'skip_questions', target: ['q2'] },
          priority: 2,
        },
        {
          id: 'rule2',
          condition: { operator: 'equals', question_code: 'q3', value: 'young' },
          action: { type: 'skip_questions', target: ['q4'] },
          priority: 1,
        },
      ]
      
      const answers = { q1: 'yes', q3: 'young' }
      const applicable = getApplicableBranchingRules(rules, answers)
      
      expect(applicable).toHaveLength(2)
      expect(applicable[0].id).toBe('rule2') // Lower priority number = higher priority
      expect(applicable[1].id).toBe('rule1')
    })

    it('should filter out non-applicable rules', () => {
      const rules: BranchingRule[] = [
        {
          id: 'rule1',
          condition: { operator: 'equals', question_code: 'q1', value: 'yes' },
          action: { type: 'skip_questions', target: ['q2'] },
        },
        {
          id: 'rule2',
          condition: { operator: 'equals', question_code: 'q1', value: 'no' },
          action: { type: 'skip_questions', target: ['q3'] },
        },
      ]
      
      const answers = { q1: 'yes' }
      const applicable = getApplicableBranchingRules(rules, answers)
      
      expect(applicable).toHaveLength(1)
      expect(applicable[0].id).toBe('rule1')
    })
  })

  describe('getVisibleQuestions', () => {
    it('should return all questions when no conditions are met', () => {
      const survey = { ...mockSurvey, branching_rules: [] }
      const visible = getVisibleQuestions(survey, {})
      // q2 has visible_if condition requiring q1='yes', so it should be hidden when no answers
      expect(visible).toHaveLength(3)
      expect(visible.find(q => q.code === 'q2')).toBeUndefined()
    })

    it('should hide questions based on visible_if conditions', () => {
      const answers = { q1: 'no' }
      const visible = getVisibleQuestions(mockSurvey, answers)
      
      // q2 should be hidden because q1 is not 'yes'
      expect(visible).toHaveLength(3)
      expect(visible.find(q => q.code === 'q2')).toBeUndefined()
    })

    it('should show questions based on visible_if conditions', () => {
      const answers = { q1: 'yes' }
      const visible = getVisibleQuestions(mockSurvey, answers)
      
      // All questions should be visible
      expect(visible).toHaveLength(4)
      expect(visible.find(q => q.code === 'q2')).toBeDefined()
    })

    it('should apply skip_questions action', () => {
      const answers = { q3: 'young' }
      const visible = getVisibleQuestions(mockSurvey, answers)
      
      // q4 should be skipped due to branching rule
      expect(visible.find(q => q.code === 'q4')).toBeUndefined()
    })

    it('should apply require_questions action', () => {
      const answers = { q1: 'yes', q2: '25', q3: 'middle' }
      const visible = getVisibleQuestions(mockSurvey, answers)
      
      // q4 should be required due to q2 > 20
      expect(visible.find(q => q.code === 'q4')).toBeDefined()
    })
  })

  describe('getVoidedAnswers', () => {
    it('should identify questions that became hidden', () => {
      const previousQuestions = mockQuestions
      const currentQuestions = mockQuestions.filter(q => q.code !== 'q2')
      const answers = { q1: 'yes', q2: '10', q3: 'middle' }
      
      const voided = getVoidedAnswers(previousQuestions, currentQuestions, answers)
      expect(voided).toContain('q2')
      expect(voided).not.toContain('q1')
      expect(voided).not.toContain('q3')
    })

    it('should only return codes that have answers', () => {
      const previousQuestions = mockQuestions
      const currentQuestions = mockQuestions.filter(q => q.code !== 'q2')
      const answers = { q1: 'yes', q3: 'middle' } // q2 has no answer
      
      const voided = getVoidedAnswers(previousQuestions, currentQuestions, answers)
      expect(voided).not.toContain('q2')
    })
  })

  describe('calculateProgress', () => {
    it('should calculate progress based on answered questions', () => {
      const visibleQuestions = mockQuestions.slice(0, 3) // 3 questions
      const answers = { q1: 'yes', q2: '10' } // 2 answered
      
      const progress = calculateProgress(answers, visibleQuestions)
      expect(progress).toBe(67) // 2/3 * 100 rounded
    })

    it('should return 0 for no questions', () => {
      const progress = calculateProgress({}, [])
      expect(progress).toBe(0)
    })

    it('should ignore empty string answers', () => {
      const visibleQuestions = mockQuestions.slice(0, 2)
      const answers = { q1: 'yes', q2: '' } // Empty string should not count
      
      const progress = calculateProgress(answers, visibleQuestions)
      expect(progress).toBe(50) // Only q1 counts as answered
    })
  })

  describe('updateSurveyState', () => {
    it('should return complete state update', () => {
      const currentAnswers = { q1: 'yes', q2: '10' }
      const previouslyVisible = mockQuestions.slice(0, 2)
      
      const update = updateSurveyState(mockSurvey, currentAnswers, previouslyVisible)
      
      expect(update.visibleQuestions).toBeDefined()
      expect(update.voidedAnswerCodes).toBeDefined()
      expect(update.updatedAnswers).toBeDefined()
      expect(update.progressPercentage).toBeDefined()
      expect(typeof update.progressPercentage).toBe('number')
    })

    it('should void answers for hidden questions', () => {
      // Start with q1='yes' which makes q2 visible
      const currentAnswers = { q1: 'no', q2: '10' } // Change q1 to 'no'
      const previouslyVisible = mockQuestions // All questions were visible
      
      const update = updateSurveyState(mockSurvey, currentAnswers, previouslyVisible)
      
      // q2 should be voided because q1 is now 'no'
      expect(update.voidedAnswerCodes).toContain('q2')
      expect(update.updatedAnswers.q2).toBeUndefined()
      expect(update.updatedAnswers.q1).toBe('no')
    })

    it('should recalculate progress correctly', () => {
      const currentAnswers = { q1: 'yes', q2: '10', q3: 'young' }
      const previouslyVisible = mockQuestions
      
      const update = updateSurveyState(mockSurvey, currentAnswers, previouslyVisible)
      
      expect(update.progressPercentage).toBeGreaterThan(0)
      expect(update.progressPercentage).toBeLessThanOrEqual(100)
    })
  })
})
