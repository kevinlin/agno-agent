import { render, screen, fireEvent, waitFor, act } from '@testing-library/react'
import { QuestionInput } from '../question-input'
import type { Question } from '@/types/survey'

// Mock the validation function
jest.mock('@/lib/survey-validation', () => ({
  validateAnswer: jest.fn().mockReturnValue({ valid: true, error: undefined })
}))

describe('QuestionInput', () => {
  const mockOnChange = jest.fn()

  beforeEach(() => {
    mockOnChange.mockClear()
  })

  describe('TEXT unit type', () => {
    const textQuestion: Question = {
      type: 'INPUT',
      code: 'text_field',
      title: 'What do you eat for breakfast?',
      unit: 'TEXT',
      required: true
    }

    it('renders text input for TEXT unit type', () => {
      render(<QuestionInput question={textQuestion} value="" onChange={mockOnChange} />)
      
      const input = screen.getByRole('textbox')
      expect(input).toBeInTheDocument()
      expect(input).toHaveAttribute('type', 'text')
    })

    it('handles text input changes correctly', () => {
      render(<QuestionInput question={textQuestion} value="" onChange={mockOnChange} />)
      
      const input = screen.getByRole('textbox')
      fireEvent.change(input, { target: { value: 'Oatmeal and fruit' } })
      
      expect(mockOnChange).toHaveBeenCalledWith('Oatmeal and fruit')
    })

    it('displays current text value', () => {
      render(<QuestionInput question={textQuestion} value="Cereal and milk" onChange={mockOnChange} />)
      
      const input = screen.getByRole('textbox') as HTMLInputElement
      expect(input.value).toBe('Cereal and milk')
    })

    it('shows placeholder with unit_text for TEXT fields', () => {
      const questionWithUnitText: Question = {
        ...textQuestion,
        unit_text: 'free text'
      }

      render(<QuestionInput question={questionWithUnitText} value="" onChange={mockOnChange} />)
      
      const input = screen.getByRole('textbox')
      expect(input).toHaveAttribute('placeholder', 'Enter value in free text')
    })
  })

  describe('INTEGER_NUMBER unit type', () => {
    const integerQuestion: Question = {
      type: 'INPUT',
      code: 'height',
      title: 'What is your height?',
      unit: 'INTEGER_NUMBER',
      unit_text: 'cm',
      constraints: { min: 100, max: 250 },
      required: true
    }

    it('renders number input for INTEGER_NUMBER unit type', () => {
      render(<QuestionInput question={integerQuestion} value="" onChange={mockOnChange} />)
      
      const input = screen.getByRole('spinbutton')
      expect(input).toBeInTheDocument()
      expect(input).toHaveAttribute('type', 'number')
      expect(input).toHaveAttribute('step', '1')
      expect(input).toHaveAttribute('min', '100')
      expect(input).toHaveAttribute('max', '250')
    })

    it('converts input to integer', () => {
      render(<QuestionInput question={integerQuestion} value="" onChange={mockOnChange} />)
      
      const input = screen.getByRole('spinbutton')
      fireEvent.change(input, { target: { value: '175' } })
      
      expect(mockOnChange).toHaveBeenCalledWith(175)
    })

    it('displays unit text for number inputs', () => {
      render(<QuestionInput question={integerQuestion} value="" onChange={mockOnChange} />)
      
      expect(screen.getByText('cm')).toBeInTheDocument()
    })
  })

  describe('DECIMAL_NUMBER unit type', () => {
    const decimalQuestion: Question = {
      type: 'INPUT',
      code: 'weight',
      title: 'What is your weight?',
      unit: 'DECIMAL_NUMBER',
      unit_text: 'kg',
      constraints: { min: 30, max: 200 },
      required: true
    }

    it('renders number input for DECIMAL_NUMBER unit type', () => {
      render(<QuestionInput question={decimalQuestion} value="" onChange={mockOnChange} />)
      
      const input = screen.getByRole('spinbutton')
      expect(input).toHaveAttribute('type', 'number')
      expect(input).toHaveAttribute('step', '0.1')
    })

    it('converts input to float', () => {
      render(<QuestionInput question={decimalQuestion} value="" onChange={mockOnChange} />)
      
      const input = screen.getByRole('spinbutton')
      fireEvent.change(input, { target: { value: '70.5' } })
      
      expect(mockOnChange).toHaveBeenCalledWith(70.5)
    })
  })

  describe('Required field validation', () => {
    const requiredQuestion: Question = {
      type: 'INPUT',
      code: 'required_field',
      title: 'Required Field',
      unit: 'TEXT',
      required: true
    }

    it('shows required asterisk', () => {
      render(<QuestionInput question={requiredQuestion} value="" onChange={mockOnChange} />)
      
      expect(screen.getByText('*')).toBeInTheDocument()
    })

    it('shows validation error on blur when empty and required', async () => {
      const { validateAnswer } = require('@/lib/survey-validation')
      validateAnswer.mockReturnValue({ valid: false, error: 'This field is required' })

      render(<QuestionInput question={requiredQuestion} value="" onChange={mockOnChange} />)
      
      const input = screen.getByRole('textbox')
      fireEvent.blur(input)
      
      await waitFor(() => {
        expect(screen.getByText('This field is required')).toBeInTheDocument()
      })
    })
  })

  describe('Accessibility', () => {
    const question: Question = {
      type: 'INPUT',
      code: 'accessible_field',
      title: 'Accessible Field',
      subtitle: 'This is a subtitle',
      help: 'This is help text',
      unit: 'TEXT'
    }

    it('has proper labels and descriptions', () => {
      render(<QuestionInput question={question} value="" onChange={mockOnChange} />)
      
      const input = screen.getByRole('textbox')
      expect(input).toHaveAccessibleName('Accessible Field')
      expect(screen.getByText('This is a subtitle')).toBeInTheDocument()
      expect(screen.getByText('This is help text')).toBeInTheDocument()
    })

    it('associates label with input via htmlFor', () => {
      render(<QuestionInput question={question} value="" onChange={mockOnChange} />)
      
      const label = screen.getByText('Accessible Field')
      const input = screen.getByRole('textbox')
      
      expect(label).toHaveAttribute('for', question.code)
      expect(input).toHaveAttribute('id', question.code)
    })
  })

  describe('Error states', () => {
    const question: Question = {
      type: 'INPUT',
      code: 'error_field',
      title: 'Error Field',
      unit: 'TEXT'
    }

    it('shows error styling when validation fails', async () => {
      const { validateAnswer } = require('@/lib/survey-validation')
      validateAnswer.mockReturnValue({ valid: false, error: 'Invalid input' })

      render(<QuestionInput question={question} value="" onChange={mockOnChange} />)
      
      const input = screen.getByRole('textbox')
      fireEvent.blur(input)
      
      await waitFor(() => {
        expect(input).toHaveClass('border-destructive')
        expect(screen.getByText('Invalid input')).toBeInTheDocument()
      })
    })

    it('hides help text when error is shown', async () => {
      const { validateAnswer } = require('@/lib/survey-validation')
      validateAnswer.mockReturnValue({ valid: false, error: 'Invalid input' })

      const questionWithHelp: Question = {
        ...question,
        help: 'This is help text'
      }

      render(<QuestionInput question={questionWithHelp} value="" onChange={mockOnChange} />)
      
      const input = screen.getByRole('textbox')
      fireEvent.blur(input)
      
      await waitFor(() => {
        expect(screen.getByText('Invalid input')).toBeInTheDocument()
        expect(screen.queryByText('This is help text')).not.toBeInTheDocument()
      })
    })
  })
})
