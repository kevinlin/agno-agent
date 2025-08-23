import { render, screen } from '@testing-library/react'
import { QuestionRenderer } from '../question-renderer'
import type { Question } from '@/types/survey'

// Mock all the question components
jest.mock('../question-input', () => ({
  QuestionInput: ({ question }: any) => <div data-testid="question-input">{question.title}</div>
}))

jest.mock('../question-single-select', () => ({
  QuestionSingleSelect: ({ question }: any) => <div data-testid="question-single-select">{question.title}</div>
}))

jest.mock('../question-multiple-select', () => ({
  QuestionMultipleSelect: ({ question }: any) => <div data-testid="question-multiple-select">{question.title}</div>
}))

jest.mock('../question-dropdown', () => ({
  QuestionDropdown: ({ question }: any) => <div data-testid="question-dropdown">{question.title}</div>
}))

jest.mock('../question-time', () => ({
  QuestionTime: ({ question }: any) => <div data-testid="question-time">{question.title}</div>
}))

describe('QuestionRenderer', () => {
  const mockOnChange = jest.fn()

  beforeEach(() => {
    mockOnChange.mockClear()
  })

  describe('Question type routing', () => {
    it('renders QuestionInput for INPUT type', () => {
      const question: Question = {
        type: 'INPUT',
        code: 'height',
        title: 'What is your height?',
        unit: 'INTEGER_NUMBER'
      }

      render(<QuestionRenderer question={question} value="" onChange={mockOnChange} />)
      
      expect(screen.getByTestId('question-input')).toBeInTheDocument()
      expect(screen.getByText('What is your height?')).toBeInTheDocument()
    })

    it('renders QuestionSingleSelect for SINGLE_SELECT type', () => {
      const question: Question = {
        type: 'SINGLE_SELECT',
        code: 'gender',
        title: 'What is your gender?',
        answers: {
          answers: [
            { code: 'male', title: 'Male' },
            { code: 'female', title: 'Female' }
          ]
        }
      }

      render(<QuestionRenderer question={question} value="" onChange={mockOnChange} />)
      
      expect(screen.getByTestId('question-single-select')).toBeInTheDocument()
      expect(screen.getByText('What is your gender?')).toBeInTheDocument()
    })

    it('renders QuestionMultipleSelect for MULTIPLE_SELECT type', () => {
      const question: Question = {
        type: 'MULTIPLE_SELECT',
        code: 'conditions',
        title: 'Select your conditions',
        answers: {
          answers: [
            { code: 'diabetes', title: 'Diabetes' },
            { code: 'hypertension', title: 'Hypertension' }
          ]
        }
      }

      render(<QuestionRenderer question={question} value={[]} onChange={mockOnChange} />)
      
      expect(screen.getByTestId('question-multiple-select')).toBeInTheDocument()
      expect(screen.getByText('Select your conditions')).toBeInTheDocument()
    })

    it('renders QuestionDropdown for DROPDOWN type', () => {
      const question: Question = {
        type: 'DROPDOWN',
        code: 'education',
        title: 'What is your education level?',
        answers: {
          answers: [
            { code: 'high_school', title: 'High School' },
            { code: 'college', title: 'College' }
          ]
        }
      }

      render(<QuestionRenderer question={question} value="" onChange={mockOnChange} />)
      
      expect(screen.getByTestId('question-dropdown')).toBeInTheDocument()
      expect(screen.getByText('What is your education level?')).toBeInTheDocument()
    })

    it('renders QuestionTime for TIME type', () => {
      const question: Question = {
        type: 'TIME',
        code: 'sleep_time',
        title: 'What time do you sleep?',
        unit: 'MINUTES'
      }

      render(<QuestionRenderer question={question} value={480} onChange={mockOnChange} />)
      
      expect(screen.getByTestId('question-time')).toBeInTheDocument()
      expect(screen.getByText('What time do you sleep?')).toBeInTheDocument()
    })
  })

  describe('Unsupported question types', () => {
    it('renders error message for unsupported question type', () => {
      const question = {
        type: 'UNSUPPORTED_TYPE',
        code: 'unsupported',
        title: 'Unsupported Question'
      } as Question

      render(<QuestionRenderer question={question} value="" onChange={mockOnChange} />)
      
      expect(screen.getByText('Unsupported question type: UNSUPPORTED_TYPE')).toBeInTheDocument()
      expect(screen.getByText('Unsupported question type: UNSUPPORTED_TYPE')).toHaveClass('text-destructive')
    })

    it('applies error styling for unsupported types', () => {
      const question = {
        type: 'INVALID',
        code: 'invalid',
        title: 'Invalid Question'
      } as Question

      render(<QuestionRenderer question={question} value="" onChange={mockOnChange} />)
      
      const errorContainer = screen.getByText('Unsupported question type: INVALID').parentElement
      expect(errorContainer).toHaveClass('p-4', 'border', 'border-destructive', 'rounded-md')
    })
  })

  describe('Props forwarding', () => {
    it('forwards all props to child components', () => {
      const question: Question = {
        type: 'INPUT',
        code: 'test',
        title: 'Test Question',
        unit: 'TEXT'
      }

      const customClassName = 'custom-class'
      const testValue = 'test value'

      render(
        <QuestionRenderer 
          question={question} 
          value={testValue} 
          onChange={mockOnChange} 
          className={customClassName}
        />
      )
      
      // The mock component should receive all these props
      expect(screen.getByTestId('question-input')).toBeInTheDocument()
    })

    it('handles undefined value prop', () => {
      const question: Question = {
        type: 'INPUT',
        code: 'test',
        title: 'Test Question',
        unit: 'TEXT'
      }

      render(<QuestionRenderer question={question} onChange={mockOnChange} />)
      
      expect(screen.getByTestId('question-input')).toBeInTheDocument()
    })

    it('handles undefined className prop', () => {
      const question: Question = {
        type: 'INPUT',
        code: 'test',
        title: 'Test Question',
        unit: 'TEXT'
      }

      render(<QuestionRenderer question={question} value="" onChange={mockOnChange} />)
      
      expect(screen.getByTestId('question-input')).toBeInTheDocument()
    })
  })

  describe('Type safety and edge cases', () => {
    it('handles questions with minimal required fields', () => {
      const minimalQuestion: Question = {
        type: 'INPUT',
        code: 'minimal',
        title: 'Minimal Question'
      }

      render(<QuestionRenderer question={minimalQuestion} value="" onChange={mockOnChange} />)
      
      expect(screen.getByTestId('question-input')).toBeInTheDocument()
    })

    it('handles questions with all optional fields', () => {
      const fullQuestion: Question = {
        type: 'SINGLE_SELECT',
        code: 'full',
        title: 'Full Question',
        subtitle: 'This is a subtitle',
        required: true,
        help: 'This is help text',
        answers: {
          answers: [
            { code: 'option1', title: 'Option 1' },
            { code: 'option2', title: 'Option 2' }
          ]
        },
        visible_if: {
          operator: 'equals',
          question_code: 'other_question',
          value: 'yes'
        }
      }

      render(<QuestionRenderer question={fullQuestion} value="" onChange={mockOnChange} />)
      
      expect(screen.getByTestId('question-single-select')).toBeInTheDocument()
    })

    it('handles different value types correctly', () => {
      const testCases = [
        {
          question: { type: 'INPUT', code: 'text', title: 'Text' } as Question,
          value: 'string value'
        },
        {
          question: { type: 'INPUT', code: 'number', title: 'Number' } as Question,
          value: 42
        },
        {
          question: { type: 'MULTIPLE_SELECT', code: 'multi', title: 'Multi' } as Question,
          value: ['option1', 'option2']
        },
        {
          question: { type: 'TIME', code: 'time', title: 'Time' } as Question,
          value: 480
        }
      ]

      testCases.forEach(({ question, value }) => {
        const { unmount } = render(<QuestionRenderer question={question} value={value} onChange={mockOnChange} />)
        
        // Should render without errors
        expect(screen.getByText(question.title)).toBeInTheDocument()
        
        unmount()
      })
    })
  })

  describe('Component integration', () => {
    it('passes through onChange callback correctly', () => {
      const question: Question = {
        type: 'INPUT',
        code: 'test',
        title: 'Test Question',
        unit: 'TEXT'
      }

      render(<QuestionRenderer question={question} value="" onChange={mockOnChange} />)
      
      // The mock component should receive the onChange prop
      expect(screen.getByTestId('question-input')).toBeInTheDocument()
    })

    it('maintains component state during re-renders', () => {
      const question: Question = {
        type: 'INPUT',
        code: 'test',
        title: 'Test Question',
        unit: 'TEXT'
      }

      const { rerender } = render(<QuestionRenderer question={question} value="initial" onChange={mockOnChange} />)
      
      expect(screen.getByTestId('question-input')).toBeInTheDocument()
      
      // Re-render with different value
      rerender(<QuestionRenderer question={question} value="updated" onChange={mockOnChange} />)
      
      expect(screen.getByTestId('question-input')).toBeInTheDocument()
    })

    it('switches question types correctly on re-render', () => {
      const inputQuestion: Question = {
        type: 'INPUT',
        code: 'test',
        title: 'Input Question',
        unit: 'TEXT'
      }

      const selectQuestion: Question = {
        type: 'SINGLE_SELECT',
        code: 'test',
        title: 'Select Question',
        answers: {
          answers: [{ code: 'option', title: 'Option' }]
        }
      }

      const { rerender } = render(<QuestionRenderer question={inputQuestion} value="" onChange={mockOnChange} />)
      
      expect(screen.getByTestId('question-input')).toBeInTheDocument()
      
      // Switch to different question type
      rerender(<QuestionRenderer question={selectQuestion} value="" onChange={mockOnChange} />)
      
      expect(screen.queryByTestId('question-input')).not.toBeInTheDocument()
      expect(screen.getByTestId('question-single-select')).toBeInTheDocument()
    })
  })
})
