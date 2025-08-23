import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import { QuestionMultipleSelect } from '../question-multiple-select'
import type { Question } from '@/types/survey'

// Mock the validation function
jest.mock('@/lib/survey-validation', () => ({
  validateAnswer: jest.fn().mockReturnValue({ valid: true, error: undefined })
}))

describe('QuestionMultipleSelect', () => {
  const mockOnChange = jest.fn()

  beforeEach(() => {
    mockOnChange.mockClear()
  })

  const multipleSelectQuestion: Question = {
    type: 'MULTIPLE_SELECT',
    code: 'conditions',
    title: 'I have ...',
    required: true,
    answers: {
      answers: [
        { code: 'diabetes', title: 'Diabetes' },
        { code: 'hypertension', title: 'Hypertension' },
        { code: 'heart_disease', title: 'Heart disease' },
        { code: 'none', title: 'None of the above' }
      ],
      exclusiveOptions: ['none']
    }
  }

  describe('Rendering', () => {
    it('renders question title and all options', () => {
      render(<QuestionMultipleSelect question={multipleSelectQuestion} value={[]} onChange={mockOnChange} />)
      
      expect(screen.getByText('I have ...')).toBeInTheDocument()
      expect(screen.getByText('Diabetes')).toBeInTheDocument()
      expect(screen.getByText('Hypertension')).toBeInTheDocument()
      expect(screen.getByText('Heart disease')).toBeInTheDocument()
      expect(screen.getByText('None of the above')).toBeInTheDocument()
    })

    it('shows required asterisk when required', () => {
      render(<QuestionMultipleSelect question={multipleSelectQuestion} value={[]} onChange={mockOnChange} />)
      
      expect(screen.getByText('*')).toBeInTheDocument()
    })

    it('shows subtitle when provided', () => {
      const questionWithSubtitle: Question = {
        ...multipleSelectQuestion,
        subtitle: 'Select all that apply'
      }

      render(<QuestionMultipleSelect question={questionWithSubtitle} value={[]} onChange={mockOnChange} />)
      
      expect(screen.getByText('Select all that apply')).toBeInTheDocument()
    })

    it('shows help text when provided', () => {
      const questionWithHelp: Question = {
        ...multipleSelectQuestion,
        help: 'Check all conditions you currently have'
      }

      render(<QuestionMultipleSelect question={questionWithHelp} value={[]} onChange={mockOnChange} />)
      
      expect(screen.getByText('Check all conditions you currently have')).toBeInTheDocument()
    })

    it('returns null when no answers are provided', () => {
      const questionNoAnswers: Question = {
        ...multipleSelectQuestion,
        answers: undefined
      }

      const { container } = render(<QuestionMultipleSelect question={questionNoAnswers} value={[]} onChange={mockOnChange} />)
      
      expect(container.firstChild).toBeNull()
    })

    it('styles exclusive options differently', () => {
      render(<QuestionMultipleSelect question={multipleSelectQuestion} value={[]} onChange={mockOnChange} />)
      
      const noneOption = screen.getByText('None of the above')
      expect(noneOption).toHaveClass('font-medium', 'text-muted-foreground')
    })
  })

  describe('User Interaction', () => {
    it('calls onChange when option is selected', () => {
      render(<QuestionMultipleSelect question={multipleSelectQuestion} value={[]} onChange={mockOnChange} />)
      
      const diabetesCheckbox = screen.getByRole('checkbox', { name: /diabetes/i })
      fireEvent.click(diabetesCheckbox)
      
      expect(mockOnChange).toHaveBeenCalledWith(['diabetes'])
    })

    it('shows selected values', () => {
      render(<QuestionMultipleSelect question={multipleSelectQuestion} value={['diabetes', 'hypertension']} onChange={mockOnChange} />)
      
      const diabetesCheckbox = screen.getByRole('checkbox', { name: /diabetes/i })
      const hypertensionCheckbox = screen.getByRole('checkbox', { name: /hypertension/i })
      const heartDiseaseCheckbox = screen.getByRole('checkbox', { name: /heart disease/i })
      
      expect(diabetesCheckbox).toBeChecked()
      expect(hypertensionCheckbox).toBeChecked()
      expect(heartDiseaseCheckbox).not.toBeChecked()
    })

    it('allows selecting multiple non-exclusive options', () => {
      render(<QuestionMultipleSelect question={multipleSelectQuestion} value={['diabetes']} onChange={mockOnChange} />)
      
      const hypertensionCheckbox = screen.getByRole('checkbox', { name: /hypertension/i })
      fireEvent.click(hypertensionCheckbox)
      
      expect(mockOnChange).toHaveBeenCalledWith(['diabetes', 'hypertension'])
    })

    it('allows deselecting options', () => {
      render(<QuestionMultipleSelect question={multipleSelectQuestion} value={['diabetes', 'hypertension']} onChange={mockOnChange} />)
      
      const diabetesCheckbox = screen.getByRole('checkbox', { name: /diabetes/i })
      fireEvent.click(diabetesCheckbox)
      
      expect(mockOnChange).toHaveBeenCalledWith(['hypertension'])
    })
  })

  describe('Exclusive Options', () => {
    it('clears other options when exclusive option is selected', () => {
      render(<QuestionMultipleSelect question={multipleSelectQuestion} value={['diabetes', 'hypertension']} onChange={mockOnChange} />)
      
      const noneCheckbox = screen.getByRole('checkbox', { name: /none of the above/i })
      fireEvent.click(noneCheckbox)
      
      expect(mockOnChange).toHaveBeenCalledWith(['none'])
    })

    it('clears exclusive options when regular option is selected', () => {
      render(<QuestionMultipleSelect question={multipleSelectQuestion} value={['none']} onChange={mockOnChange} />)
      
      const diabetesCheckbox = screen.getByRole('checkbox', { name: /diabetes/i })
      fireEvent.click(diabetesCheckbox)
      
      expect(mockOnChange).toHaveBeenCalledWith(['diabetes'])
    })

    it('handles multiple exclusive options correctly', () => {
      const questionWithMultipleExclusive: Question = {
        ...multipleSelectQuestion,
        answers: {
          answers: [
            { code: 'diabetes', title: 'Diabetes' },
            { code: 'none', title: 'None of the above' },
            { code: 'prefer_not_to_say', title: 'Prefer not to say' }
          ],
          exclusiveOptions: ['none', 'prefer_not_to_say']
        }
      }

      render(<QuestionMultipleSelect question={questionWithMultipleExclusive} value={['none']} onChange={mockOnChange} />)
      
      const preferNotToSayCheckbox = screen.getByRole('checkbox', { name: /prefer not to say/i })
      fireEvent.click(preferNotToSayCheckbox)
      
      expect(mockOnChange).toHaveBeenCalledWith(['prefer_not_to_say'])
    })
  })

  describe('Accessibility', () => {
    it('uses checkboxes for multiple selection', () => {
      render(<QuestionMultipleSelect question={multipleSelectQuestion} value={[]} onChange={mockOnChange} />)
      
      const checkboxes = screen.getAllByRole('checkbox')
      expect(checkboxes).toHaveLength(4)
    })

    it('has proper labels for checkboxes', () => {
      render(<QuestionMultipleSelect question={multipleSelectQuestion} value={[]} onChange={mockOnChange} />)
      
      const diabetesCheckbox = screen.getByRole('checkbox', { name: /diabetes/i })
      const hypertensionCheckbox = screen.getByRole('checkbox', { name: /hypertension/i })
      
      expect(diabetesCheckbox).toBeInTheDocument()
      expect(hypertensionCheckbox).toBeInTheDocument()
    })

    it('associates labels with checkboxes via htmlFor', () => {
      render(<QuestionMultipleSelect question={multipleSelectQuestion} value={[]} onChange={mockOnChange} />)
      
      const diabetesLabel = screen.getByText('Diabetes')
      const diabetesCheckbox = screen.getByRole('checkbox', { name: /diabetes/i })
      
      expect(diabetesLabel).toHaveAttribute('for', `${multipleSelectQuestion.code}-diabetes`)
      expect(diabetesCheckbox).toHaveAttribute('id', `${multipleSelectQuestion.code}-diabetes`)
    })

    it('supports keyboard navigation', () => {
      render(<QuestionMultipleSelect question={multipleSelectQuestion} value={[]} onChange={mockOnChange} />)
      
      const checkboxes = screen.getAllByRole('checkbox')
      
      // Focus first checkbox
      checkboxes[0].focus()
      expect(checkboxes[0]).toHaveFocus()
      
      // Press Tab to move to next checkbox
      fireEvent.keyDown(checkboxes[0], { key: 'Tab' })
    })
  })

  describe('Validation', () => {
    it('shows validation error on blur when required and empty', async () => {
      const { validateAnswer } = require('@/lib/survey-validation')
      validateAnswer.mockReturnValue({ valid: false, error: 'Please select at least one option' })

      render(<QuestionMultipleSelect question={multipleSelectQuestion} value={[]} onChange={mockOnChange} />)
      
      const checkbox = screen.getAllByRole('checkbox')[0]
      fireEvent.blur(checkbox)
      
      await waitFor(() => {
        expect(screen.getByText('Please select at least one option')).toBeInTheDocument()
      })
    })

    it('shows error styling when validation fails', async () => {
      const { validateAnswer } = require('@/lib/survey-validation')
      validateAnswer.mockReturnValue({ valid: false, error: 'Please select at least one option' })

      render(<QuestionMultipleSelect question={multipleSelectQuestion} value={[]} onChange={mockOnChange} />)
      
      const checkbox = screen.getAllByRole('checkbox')[0]
      fireEvent.blur(checkbox)
      
      await waitFor(() => {
        expect(screen.getByText('Please select at least one option')).toBeInTheDocument()
        expect(screen.getByText('Please select at least one option')).toHaveClass('text-destructive')
      })
    })

    it('validates on value change after first blur', async () => {
      const { validateAnswer } = require('@/lib/survey-validation')
      validateAnswer.mockReturnValue({ valid: true, error: undefined })

      render(<QuestionMultipleSelect question={multipleSelectQuestion} value={[]} onChange={mockOnChange} />)
      
      const checkbox = screen.getAllByRole('checkbox')[0]
      
      // First blur to mark as touched
      fireEvent.blur(checkbox)
      
      // Now change value should trigger validation
      fireEvent.click(checkbox)
      
      expect(validateAnswer).toHaveBeenCalledWith(multipleSelectQuestion, ['diabetes'])
    })
  })

  describe('Default values and edge cases', () => {
    it('handles undefined value prop gracefully', () => {
      render(<QuestionMultipleSelect question={multipleSelectQuestion} onChange={mockOnChange} />)
      
      const checkbox = screen.getAllByRole('checkbox')[0]
      fireEvent.click(checkbox)
      
      expect(mockOnChange).toHaveBeenCalledWith(['diabetes'])
    })

    it('handles questions without exclusive options', () => {
      const questionWithoutExclusive: Question = {
        ...multipleSelectQuestion,
        answers: {
          answers: [
            { code: 'diabetes', title: 'Diabetes' },
            { code: 'hypertension', title: 'Hypertension' }
          ]
        }
      }

      const { rerender } = render(<QuestionMultipleSelect question={questionWithoutExclusive} value={[]} onChange={mockOnChange} />)
      
      const diabetesCheckbox = screen.getByRole('checkbox', { name: /diabetes/i })
      fireEvent.click(diabetesCheckbox)
      expect(mockOnChange).toHaveBeenNthCalledWith(1, ['diabetes'])
      
      // Re-render with updated value for the second click
      rerender(<QuestionMultipleSelect question={questionWithoutExclusive} value={['diabetes']} onChange={mockOnChange} />)
      
      const hypertensionCheckbox = screen.getByRole('checkbox', { name: /hypertension/i })
      fireEvent.click(hypertensionCheckbox)
      expect(mockOnChange).toHaveBeenNthCalledWith(2, ['diabetes', 'hypertension'])
    })
  })
})
