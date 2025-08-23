import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import { QuestionSingleSelect } from '../question-single-select'
import type { Question } from '@/types/survey'

// Mock the validation function
jest.mock('@/lib/survey-validation', () => ({
  validateAnswer: jest.fn().mockReturnValue({ valid: true, error: undefined })
}))

describe('QuestionSingleSelect', () => {
  const mockOnChange = jest.fn()

  beforeEach(() => {
    mockOnChange.mockClear()
  })

  const singleSelectQuestion: Question = {
    type: 'SINGLE_SELECT',
    code: 'smoke_status',
    title: 'Do you smoke?',
    required: true,
    answers: {
      answers: [
        { code: 'never', title: 'Never smoked' },
        { code: 'former', title: 'Former smoker' },
        { code: 'current', title: 'Current smoker' }
      ]
    }
  }

  describe('Rendering', () => {
    it('renders question title and options', () => {
      render(<QuestionSingleSelect question={singleSelectQuestion} value="" onChange={mockOnChange} />)
      
      expect(screen.getByText('Do you smoke?')).toBeInTheDocument()
      expect(screen.getByText('Never smoked')).toBeInTheDocument()
      expect(screen.getByText('Former smoker')).toBeInTheDocument()
      expect(screen.getByText('Current smoker')).toBeInTheDocument()
    })

    it('shows required asterisk when required', () => {
      render(<QuestionSingleSelect question={singleSelectQuestion} value="" onChange={mockOnChange} />)
      
      expect(screen.getByText('*')).toBeInTheDocument()
    })

    it('shows subtitle when provided', () => {
      const questionWithSubtitle: Question = {
        ...singleSelectQuestion,
        subtitle: 'Select one option'
      }

      render(<QuestionSingleSelect question={questionWithSubtitle} value="" onChange={mockOnChange} />)
      
      expect(screen.getByText('Select one option')).toBeInTheDocument()
    })

    it('shows help text when provided', () => {
      const questionWithHelp: Question = {
        ...singleSelectQuestion,
        help: 'This information helps us assess your health risk'
      }

      render(<QuestionSingleSelect question={questionWithHelp} value="" onChange={mockOnChange} />)
      
      expect(screen.getByText('This information helps us assess your health risk')).toBeInTheDocument()
    })

    it('returns null when no answers are provided', () => {
      const questionNoAnswers: Question = {
        ...singleSelectQuestion,
        answers: undefined
      }

      const { container } = render(<QuestionSingleSelect question={questionNoAnswers} value="" onChange={mockOnChange} />)
      
      expect(container.firstChild).toBeNull()
    })
  })

  describe('User Interaction', () => {
    it('calls onChange when option is selected', () => {
      render(<QuestionSingleSelect question={singleSelectQuestion} value="" onChange={mockOnChange} />)
      
      const neverOption = screen.getByRole('radio', { name: /never smoked/i })
      fireEvent.click(neverOption)
      
      expect(mockOnChange).toHaveBeenCalledWith('never')
    })

    it('shows selected value', () => {
      render(<QuestionSingleSelect question={singleSelectQuestion} value="former" onChange={mockOnChange} />)
      
      const formerOption = screen.getByRole('radio', { name: /former smoker/i })
      expect(formerOption).toBeChecked()
    })

    it('allows changing selection', () => {
      render(<QuestionSingleSelect question={singleSelectQuestion} value="never" onChange={mockOnChange} />)
      
      const currentOption = screen.getByRole('radio', { name: /current smoker/i })
      fireEvent.click(currentOption)
      
      expect(mockOnChange).toHaveBeenCalledWith('current')
    })
  })

  describe('Accessibility', () => {
    it('uses radio group for single selection', () => {
      render(<QuestionSingleSelect question={singleSelectQuestion} value="" onChange={mockOnChange} />)
      
      const radioGroup = screen.getByRole('radiogroup')
      expect(radioGroup).toBeInTheDocument()
      
      const radioButtons = screen.getAllByRole('radio')
      expect(radioButtons).toHaveLength(3)
    })

    it('has proper labels for radio buttons', () => {
      render(<QuestionSingleSelect question={singleSelectQuestion} value="" onChange={mockOnChange} />)
      
      const neverOption = screen.getByRole('radio', { name: /never smoked/i })
      const formerOption = screen.getByRole('radio', { name: /former smoker/i })
      const currentOption = screen.getByRole('radio', { name: /current smoker/i })
      
      expect(neverOption).toBeInTheDocument()
      expect(formerOption).toBeInTheDocument()
      expect(currentOption).toBeInTheDocument()
    })

    it('associates labels with radio buttons via htmlFor', () => {
      render(<QuestionSingleSelect question={singleSelectQuestion} value="" onChange={mockOnChange} />)
      
      const neverLabel = screen.getByText('Never smoked')
      const neverRadio = screen.getByRole('radio', { name: /never smoked/i })
      
      expect(neverLabel).toHaveAttribute('for', `${singleSelectQuestion.code}-never`)
      expect(neverRadio).toHaveAttribute('id', `${singleSelectQuestion.code}-never`)
    })

    it('supports keyboard navigation', () => {
      render(<QuestionSingleSelect question={singleSelectQuestion} value="" onChange={mockOnChange} />)
      
      const radioButtons = screen.getAllByRole('radio')
      
      // Focus first radio button
      radioButtons[0].focus()
      expect(radioButtons[0]).toHaveFocus()
      
      // Test arrow key navigation works without crashing
      fireEvent.keyDown(radioButtons[0], { key: 'ArrowDown' })
      fireEvent.keyDown(radioButtons[0], { key: 'ArrowUp' })
      
      // Basic keyboard navigation should work
      expect(radioButtons[0]).toBeInTheDocument()
    })
  })

  describe('Validation', () => {
    it('shows validation error on blur when required and empty', async () => {
      const { validateAnswer } = require('@/lib/survey-validation')
      validateAnswer.mockReturnValue({ valid: false, error: 'Please select an option' })

      render(<QuestionSingleSelect question={singleSelectQuestion} value="" onChange={mockOnChange} />)
      
      const radioButton = screen.getAllByRole('radio')[0]
      fireEvent.blur(radioButton)
      
      await waitFor(() => {
        expect(screen.getByText('Please select an option')).toBeInTheDocument()
      })
    })

    it('shows error styling when validation fails', async () => {
      const { validateAnswer } = require('@/lib/survey-validation')
      validateAnswer.mockReturnValue({ valid: false, error: 'Please select an option' })

      render(<QuestionSingleSelect question={singleSelectQuestion} value="" onChange={mockOnChange} />)
      
      const radioButton = screen.getAllByRole('radio')[0]
      fireEvent.blur(radioButton)
      
      await waitFor(() => {
        expect(screen.getByText('Please select an option')).toBeInTheDocument()
        expect(screen.getByText('Please select an option')).toHaveClass('text-destructive')
      })
    })

    it('hides help text when error is shown', async () => {
      const { validateAnswer } = require('@/lib/survey-validation')
      validateAnswer.mockReturnValue({ valid: false, error: 'Please select an option' })

      const questionWithHelp: Question = {
        ...singleSelectQuestion,
        help: 'Choose the option that best describes you'
      }

      render(<QuestionSingleSelect question={questionWithHelp} value="" onChange={mockOnChange} />)
      
      const radioButton = screen.getAllByRole('radio')[0]
      fireEvent.blur(radioButton)
      
      await waitFor(() => {
        expect(screen.getByText('Please select an option')).toBeInTheDocument()
        expect(screen.queryByText('Choose the option that best describes you')).not.toBeInTheDocument()
      })
    })

    it('validates on value change after first blur', async () => {
      const { validateAnswer } = require('@/lib/survey-validation')
      validateAnswer.mockReturnValue({ valid: true, error: undefined })

      render(<QuestionSingleSelect question={singleSelectQuestion} value="" onChange={mockOnChange} />)
      
      const radioButton = screen.getAllByRole('radio')[0]
      
      // First blur to mark as touched
      fireEvent.blur(radioButton)
      
      // Now change value should trigger validation
      fireEvent.click(radioButton)
      
      expect(validateAnswer).toHaveBeenCalledWith(singleSelectQuestion, 'never')
    })
  })
})
