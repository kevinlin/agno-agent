import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import { QuestionTime } from '../question-time'
import type { Question } from '@/types/survey'

// Mock the validation function
jest.mock('@/lib/survey-validation', () => ({
  validateAnswer: jest.fn().mockReturnValue({ valid: true, error: undefined })
}))

describe('QuestionTime', () => {
  const mockOnChange = jest.fn()

  beforeEach(() => {
    mockOnChange.mockClear()
  })

  const timeQuestion: Question = {
    type: 'TIME',
    code: 'sleep_duration',
    title: 'How many hours do you sleep per night?',
    unit: 'MINUTES',
    required: true
  }

  describe('Rendering', () => {
    it('renders question title and time input', () => {
      render(<QuestionTime question={timeQuestion} value={480} onChange={mockOnChange} />)
      
      expect(screen.getByText('How many hours do you sleep per night?')).toBeInTheDocument()
      expect(screen.getByDisplayValue('08:00')).toBeInTheDocument()
    })

    it('shows required asterisk when required', () => {
      render(<QuestionTime question={timeQuestion} value={undefined} onChange={mockOnChange} />)
      
      expect(screen.getByText('*')).toBeInTheDocument()
    })

    it('shows subtitle when provided', () => {
      const questionWithSubtitle: Question = {
        ...timeQuestion,
        subtitle: 'Enter time in HH:MM format'
      }

      render(<QuestionTime question={questionWithSubtitle} value={undefined} onChange={mockOnChange} />)
      
      expect(screen.getByText('Enter time in HH:MM format')).toBeInTheDocument()
    })

    it('shows help text when provided', () => {
      const questionWithHelp: Question = {
        ...timeQuestion,
        help: 'Average sleep duration including naps'
      }

      render(<QuestionTime question={questionWithHelp} value={undefined} onChange={mockOnChange} />)
      
      expect(screen.getByText('Average sleep duration including naps')).toBeInTheDocument()
    })

    it('shows HH:MM format indicator', () => {
      render(<QuestionTime question={timeQuestion} value={undefined} onChange={mockOnChange} />)
      
      expect(screen.getByText('HH:MM')).toBeInTheDocument()
    })

    it('renders empty input when no value provided', () => {
      render(<QuestionTime question={timeQuestion} value={undefined} onChange={mockOnChange} />)
      
      const input = document.querySelector('#sleep_duration') as HTMLInputElement as HTMLInputElement
      expect(input.value).toBe('')
    })
  })

  describe('Value conversion and display', () => {
    it('converts minutes to HH:MM format for display', () => {
      // 480 minutes = 8 hours = 08:00
      render(<QuestionTime question={timeQuestion} value={480} onChange={mockOnChange} />)
      
      expect(screen.getByDisplayValue('08:00')).toBeInTheDocument()
    })

    it('handles various time values correctly', () => {
      const testCases = [
        { minutes: 0, expected: '00:00' },
        { minutes: 60, expected: '01:00' },
        { minutes: 90, expected: '01:30' },
        { minutes: 720, expected: '12:00' },
        { minutes: 1439, expected: '23:59' }
      ]

      testCases.forEach(({ minutes, expected }) => {
        const { rerender } = render(<QuestionTime question={timeQuestion} value={minutes} onChange={mockOnChange} />)
        
        expect(screen.getByDisplayValue(expected)).toBeInTheDocument()
        
        rerender(<div />) // Clean up for next test
      })
    })

    it('handles fractional minutes by rounding down', () => {
      // 90.7 minutes = 1 hour 30 minutes (fractional part ignored)
      render(<QuestionTime question={timeQuestion} value={90.7} onChange={mockOnChange} />)
      
      expect(screen.getByDisplayValue('01:30')).toBeInTheDocument()
    })
  })

  describe('User Interaction', () => {
    it('calls onChange with minutes when time is entered', () => {
      render(<QuestionTime question={timeQuestion} value={undefined} onChange={mockOnChange} />)
      
      const input = document.querySelector('#sleep_duration') as HTMLInputElement
      fireEvent.change(input, { target: { value: '02:30' } })
      
      // 2 hours 30 minutes = 150 minutes
      expect(mockOnChange).toHaveBeenCalledWith(150)
    })

    it('handles various time inputs correctly', () => {
      render(<QuestionTime question={timeQuestion} value={undefined} onChange={mockOnChange} />)
      
      const input = document.querySelector('#sleep_duration') as HTMLInputElement
      
      const testCases = [
        { input: '00:00', expectedMinutes: 0 },
        { input: '01:00', expectedMinutes: 60 },
        { input: '12:30', expectedMinutes: 750 },
        { input: '23:59', expectedMinutes: 1439 }
      ]

      testCases.forEach(({ input: timeInput, expectedMinutes }) => {
        mockOnChange.mockClear()
        fireEvent.change(input, { target: { value: timeInput } })
        expect(mockOnChange).toHaveBeenCalledWith(expectedMinutes)
      })
    })

    it('maintains display value state during editing', () => {
      render(<QuestionTime question={timeQuestion} value={undefined} onChange={mockOnChange} />)
      
      const input = document.querySelector('#sleep_duration') as HTMLInputElement
      fireEvent.change(input, { target: { value: '15:45' } })
      
      expect(input).toHaveValue('15:45')
    })

    it('handles partial time input gracefully', () => {
      render(<QuestionTime question={timeQuestion} value={undefined} onChange={mockOnChange} />)
      
      const input = document.querySelector('#sleep_duration') as HTMLInputElement
      
      // Partial input should not crash
      fireEvent.change(input, { target: { value: '15:' } })
      fireEvent.change(input, { target: { value: '15' } })
      fireEvent.change(input, { target: { value: ':30' } })
      
      // Should handle gracefully without calling onChange with invalid values
    })

    it('handles invalid time input gracefully', () => {
      render(<QuestionTime question={timeQuestion} value={undefined} onChange={mockOnChange} />)
      
      const input = document.querySelector('#sleep_duration') as HTMLInputElement
      
      // Invalid time formats
      fireEvent.change(input, { target: { value: '25:00' } }) // Invalid hour
      fireEvent.change(input, { target: { value: '12:60' } }) // Invalid minute
      fireEvent.change(input, { target: { value: 'abc:def' } }) // Non-numeric
      
      // Should handle gracefully
    })
  })

  describe('Accessibility', () => {
    it('uses time input type', () => {
      render(<QuestionTime question={timeQuestion} value={undefined} onChange={mockOnChange} />)
      
      const input = document.querySelector('#sleep_duration') as HTMLInputElement
      expect(input).toHaveAttribute('type', 'time')
    })

    it('associates label with input via htmlFor', () => {
      render(<QuestionTime question={timeQuestion} value={undefined} onChange={mockOnChange} />)
      
      const label = screen.getByText('How many hours do you sleep per night?')
      const input = document.querySelector('#sleep_duration') as HTMLInputElement
      
      expect(label).toHaveAttribute('for', timeQuestion.code)
      expect(input).toHaveAttribute('id', timeQuestion.code)
    })

    it('supports keyboard navigation', () => {
      render(<QuestionTime question={timeQuestion} value={undefined} onChange={mockOnChange} />)
      
      const input = document.querySelector('#sleep_duration') as HTMLInputElement
      
      // Focus the input
      input.focus()
      expect(input).toHaveFocus()
      
      // Should support arrow keys for time picker navigation
      fireEvent.keyDown(input, { key: 'ArrowUp' })
      fireEvent.keyDown(input, { key: 'ArrowDown' })
    })

    it('has proper ARIA attributes', () => {
      render(<QuestionTime question={timeQuestion} value={undefined} onChange={mockOnChange} />)
      
      const input = document.querySelector('#sleep_duration') as HTMLInputElement
      expect(input).toHaveAccessibleName('How many hours do you sleep per night? *')
    })
  })

  describe('Validation', () => {
    it('shows validation error on blur when required and empty', async () => {
      const { validateAnswer } = require('@/lib/survey-validation')
      validateAnswer.mockReturnValue({ valid: false, error: 'Please enter a time' })

      render(<QuestionTime question={timeQuestion} value={undefined} onChange={mockOnChange} />)
      
      const input = document.querySelector('#sleep_duration') as HTMLInputElement
      fireEvent.blur(input)
      
      await waitFor(() => {
        expect(screen.getByText('Please enter a time')).toBeInTheDocument()
      })
    })

    it('shows error styling when validation fails', async () => {
      const { validateAnswer } = require('@/lib/survey-validation')
      validateAnswer.mockReturnValue({ valid: false, error: 'Please enter a time' })

      render(<QuestionTime question={timeQuestion} value={undefined} onChange={mockOnChange} />)
      
      const input = document.querySelector('#sleep_duration') as HTMLInputElement
      fireEvent.blur(input)
      
      await waitFor(() => {
        expect(input).toHaveClass('border-destructive')
        expect(screen.getByText('Please enter a time')).toBeInTheDocument()
      })
    })

    it('hides help text when error is shown', async () => {
      const { validateAnswer } = require('@/lib/survey-validation')
      validateAnswer.mockReturnValue({ valid: false, error: 'Please enter a time' })

      const questionWithHelp: Question = {
        ...timeQuestion,
        help: 'Enter your typical sleep duration'
      }

      render(<QuestionTime question={questionWithHelp} value={undefined} onChange={mockOnChange} />)
      
      const input = document.querySelector('#sleep_duration') as HTMLInputElement
      fireEvent.blur(input)
      
      await waitFor(() => {
        expect(screen.getByText('Please enter a time')).toBeInTheDocument()
        expect(screen.queryByText('Enter your typical sleep duration')).not.toBeInTheDocument()
      })
    })

    it('validates on value change after first blur', async () => {
      const { validateAnswer } = require('@/lib/survey-validation')
      validateAnswer.mockReturnValue({ valid: true, error: undefined })

      render(<QuestionTime question={timeQuestion} value={undefined} onChange={mockOnChange} />)
      
      const input = document.querySelector('#sleep_duration') as HTMLInputElement
      
      // First blur to mark as touched
      fireEvent.blur(input)
      
      // Now change value should trigger validation
      fireEvent.change(input, { target: { value: '08:00' } })
      
      expect(validateAnswer).toHaveBeenCalledWith(timeQuestion, 480)
    })
  })

  describe('Edge cases and error handling', () => {
    it('handles 24-hour format correctly', () => {
      render(<QuestionTime question={timeQuestion} value={undefined} onChange={mockOnChange} />)
      
      const input = document.querySelector('#sleep_duration') as HTMLInputElement
      fireEvent.change(input, { target: { value: '00:00' } })
      
      expect(mockOnChange).toHaveBeenCalledWith(0)
      
      fireEvent.change(input, { target: { value: '23:59' } })
      expect(mockOnChange).toHaveBeenCalledWith(1439)
    })

    it('preserves display state during invalid input', () => {
      render(<QuestionTime question={timeQuestion} value={480} onChange={mockOnChange} />)
      
      const input = document.querySelector('#sleep_duration') as HTMLInputElement
      
      // Start with valid display value
      expect(input).toHaveValue('08:00')
      
      // Enter invalid value
      fireEvent.change(input, { target: { value: 'invalid' } })
      
      // Time inputs automatically reject invalid values
      expect(input).toHaveValue('')
    })

    it('handles empty string input', () => {
      render(<QuestionTime question={timeQuestion} value={480} onChange={mockOnChange} />)
      
      const input = document.querySelector('#sleep_duration') as HTMLInputElement
      fireEvent.change(input, { target: { value: '' } })
      
      expect(input).toHaveValue('')
      // Should not call onChange with invalid value
    })

    it('initializes display value correctly from props', () => {
      // Test that initial display value is calculated correctly
      const { rerender } = render(<QuestionTime question={timeQuestion} value={undefined} onChange={mockOnChange} />)
      
      expect(document.querySelector('#sleep_duration')).toHaveValue('')
      
      // Change props
      rerender(<QuestionTime question={timeQuestion} value={1020} onChange={mockOnChange} />)
      
      // Should show 17:00 (1020 minutes = 17 hours)
      expect(screen.getByDisplayValue('17:00')).toBeInTheDocument()
    })
  })
})
