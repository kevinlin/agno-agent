/**
 * Tests for Survey Navigation and Progress Tracking
 */

import { renderHook, act, waitFor } from '@testing-library/react';
import { useSurvey } from '../use-survey';
import * as surveyApi from '../../lib/survey-api';

// Mock the survey API
jest.mock('../../lib/survey-api');
const mockSurveyApi = surveyApi as jest.Mocked<typeof surveyApi>;

describe('Survey Navigation and Progress Tracking', () => {
  const mockSurvey = {
    code: 'test-survey',
    type: 'PERSONALIZATION' as const,
    version: '1.0.0',
    title: 'Test Survey',
    questions: [
      {
        type: 'INPUT' as const,
        code: 'q1',
        title: 'Question 1',
        required: true,
        unit: 'TEXT' as const,
      },
      {
        type: 'SINGLE_SELECT' as const,
        code: 'q2',
        title: 'Question 2',
        required: true,
        answers: {
          answers: [
            { code: 'yes', title: 'Yes' },
            { code: 'no', title: 'No' },
          ]
        }
      },
      {
        type: 'INPUT' as const,
        code: 'q3',
        title: 'Question 3',
        required: false,
        unit: 'INTEGER_NUMBER' as const,
      },
    ],
    branching_rules: []
  };

  beforeEach(() => {
    jest.clearAllMocks();
    mockSurveyApi.getSurveyResponse.mockResolvedValue({
      ok: true,
      status: 'in_progress',
      progress_pct: 0,
      user_response: {}
    });
    mockSurveyApi.saveSurveyResponse.mockResolvedValue({
      ok: true,
      progress_pct: 33,
      status: 'in_progress'
    });
  });

  describe('Progress Calculation', () => {
    test('should calculate progress based on answered questions', async () => {
      const { result } = renderHook(() => useSurvey({
        survey: mockSurvey,
        userId: 'test-user',
        enableAutoSave: false
      }));

      await waitFor(() => {
        expect(result.current.progressPercentage).toBe(0);
      });

      // Answer first question
      act(() => {
        result.current.updateAnswer('q1', 'Answer 1');
      });

      await waitFor(() => {
        expect(result.current.progressPercentage).toBe(33); // 1/3 questions answered
      });

      // Answer second question
      act(() => {
        result.current.updateAnswer('q2', 'yes');
      });

      await waitFor(() => {
        expect(result.current.progressPercentage).toBe(67); // 2/3 questions answered
      });

      // Answer third question
      act(() => {
        result.current.updateAnswer('q3', '25');
      });

      await waitFor(() => {
        expect(result.current.progressPercentage).toBe(100); // 3/3 questions answered
      });
    });

    test('should not count empty answers in progress', async () => {
      const { result } = renderHook(() => useSurvey({
        survey: mockSurvey,
        userId: 'test-user',
        enableAutoSave: false
      }));

      // Set empty/null values
      act(() => {
        result.current.updateAnswer('q1', '');
        result.current.updateAnswer('q2', null);
        result.current.updateAnswer('q3', undefined);
      });

      await waitFor(() => {
        expect(result.current.progressPercentage).toBe(0);
      });
    });
  });

  describe('Single-Question Navigation', () => {
    test('should navigate between questions correctly', async () => {
      const { result } = renderHook(() => useSurvey({
        survey: mockSurvey,
        userId: 'test-user',
        enableAutoSave: false
      }));

      await waitFor(() => {
        expect(result.current.currentQuestionIndex).toBe(0);
        expect(result.current.currentQuestion?.code).toBe('q1');
        expect(result.current.isFirstQuestion).toBe(true);
        expect(result.current.isLastQuestion).toBe(false);
      });

      // Navigate to next question
      act(() => {
        result.current.updateAnswer('q1', 'Answer 1');
      });

      act(() => {
        result.current.goToNext();
      });

      await waitFor(() => {
        expect(result.current.currentQuestionIndex).toBe(1);
        expect(result.current.currentQuestion?.code).toBe('q2');
        expect(result.current.isFirstQuestion).toBe(false);
        expect(result.current.isLastQuestion).toBe(false);
      });

      // Navigate to last question
      act(() => {
        result.current.updateAnswer('q2', 'yes');
      });

      act(() => {
        result.current.goToNext();
      });

      await waitFor(() => {
        expect(result.current.currentQuestionIndex).toBe(2);
        expect(result.current.currentQuestion?.code).toBe('q3');
        expect(result.current.isFirstQuestion).toBe(false);
        expect(result.current.isLastQuestion).toBe(true);
      });

      // Navigate back
      act(() => {
        result.current.goToPrevious();
      });

      await waitFor(() => {
        expect(result.current.currentQuestionIndex).toBe(1);
        expect(result.current.currentQuestion?.code).toBe('q2');
      });
    });

    test('should not navigate if current question is invalid and required', async () => {
      const { result } = renderHook(() => useSurvey({
        survey: mockSurvey,
        userId: 'test-user',
        enableAutoSave: false
      }));

      await waitFor(() => {
        expect(result.current.currentQuestionIndex).toBe(0);
        expect(result.current.isCurrentQuestionValid).toBe(false);
      });

      // Try to navigate without answering required question
      const initialIndex = result.current.currentQuestionIndex;
      
      act(() => {
        result.current.goToNext();
      });

      await waitFor(() => {
        expect(result.current.currentQuestionIndex).toBe(initialIndex); // Should not move
      });
    });

    test('should handle direct navigation to specific questions', async () => {
      const { result } = renderHook(() => useSurvey({
        survey: mockSurvey,
        userId: 'test-user',
        enableAutoSave: false
      }));

      await waitFor(() => {
        expect(result.current.currentQuestionIndex).toBe(0);
      });

      // Jump directly to question 2
      act(() => {
        result.current.goToQuestion(2);
      });

      await waitFor(() => {
        expect(result.current.currentQuestionIndex).toBe(2);
        expect(result.current.currentQuestion?.code).toBe('q3');
      });

      // Jump to question 0
      act(() => {
        result.current.goToQuestion(0);
      });

      await waitFor(() => {
        expect(result.current.currentQuestionIndex).toBe(0);
        expect(result.current.currentQuestion?.code).toBe('q1');
      });
    });

    test('should ignore invalid direct navigation attempts', async () => {
      const { result } = renderHook(() => useSurvey({
        survey: mockSurvey,
        userId: 'test-user',
        enableAutoSave: false
      }));

      await waitFor(() => {
        expect(result.current.currentQuestionIndex).toBe(0);
      });

      const initialIndex = result.current.currentQuestionIndex;

      // Try to navigate to invalid indices
      act(() => {
        result.current.goToQuestion(-1);
      });

      expect(result.current.currentQuestionIndex).toBe(initialIndex);

      act(() => {
        result.current.goToQuestion(999);
      });

      expect(result.current.currentQuestionIndex).toBe(initialIndex);
    });
  });

  describe('Survey Mode Navigation', () => {
    test('should transition to review mode from last question', async () => {
      const { result } = renderHook(() => useSurvey({
        survey: mockSurvey,
        userId: 'test-user',
        enableAutoSave: false
      }));

      // Answer all questions and navigate to the end
      act(() => {
        result.current.updateAnswer('q1', 'Answer 1');
      });

      act(() => {
        result.current.goToNext();
      });

      act(() => {
        result.current.updateAnswer('q2', 'yes');
      });

      act(() => {
        result.current.goToNext();
      });

      act(() => {
        result.current.updateAnswer('q3', '25');
      });

      await waitFor(() => {
        expect(result.current.currentQuestionIndex).toBe(2);
        expect(result.current.isLastQuestion).toBe(true);
        expect(result.current.isCurrentQuestionValid).toBe(true);
      });

      // Navigate from last question should go to review
      act(() => {
        result.current.goToNext();
      });

      await waitFor(() => {
        expect(result.current.surveyMode).toBe('review');
      });
    });

    test('should manually navigate to review mode', async () => {
      const { result } = renderHook(() => useSurvey({
        survey: mockSurvey,
        userId: 'test-user',
        enableAutoSave: false
      }));

      await waitFor(() => {
        expect(result.current.surveyMode).toBe('questions');
      });

      act(() => {
        result.current.goToReview();
      });

      await waitFor(() => {
        expect(result.current.surveyMode).toBe('review');
      });
    });

    test('should navigate back to questions from review mode', async () => {
      const { result } = renderHook(() => useSurvey({
        survey: mockSurvey,
        userId: 'test-user',
        enableAutoSave: false
      }));

      // Go to review mode
      act(() => {
        result.current.goToReview();
      });

      await waitFor(() => {
        expect(result.current.surveyMode).toBe('review');
      });

      // Navigate back to specific question
      act(() => {
        result.current.goToQuestion(1);
      });

      await waitFor(() => {
        expect(result.current.surveyMode).toBe('questions');
        expect(result.current.currentQuestionIndex).toBe(1);
      });
    });
  });

  describe('Auto-Save During Navigation', () => {
    test('should trigger save when navigating with unsaved changes', async () => {
      const { result } = renderHook(() => useSurvey({
        survey: mockSurvey,
        userId: 'test-user',
        enableAutoSave: true,
        autoSaveDelay: 100
      }));

      // Answer a question
      act(() => {
        result.current.updateAnswer('q1', 'Answer 1');
      });

      // Navigate to next question
      act(() => {
        result.current.goToNext();
      });

      // Should have called save API
      await waitFor(() => {
        expect(mockSurveyApi.saveSurveyResponse).toHaveBeenCalled();
      });
    });

    test('should save when using direct navigation', async () => {
      const { result } = renderHook(() => useSurvey({
        survey: mockSurvey,
        userId: 'test-user',
        enableAutoSave: true
      }));

      // Answer a question
      act(() => {
        result.current.updateAnswer('q1', 'Answer 1');
      });

      // Use direct navigation
      act(() => {
        result.current.goToQuestion(2);
      });

      // Should have called save API
      await waitFor(() => {
        expect(mockSurveyApi.saveSurveyResponse).toHaveBeenCalled();
      });
    });
  });

  describe('Survey Completion Logic', () => {
    test('should detect when survey is complete', async () => {
      const { result } = renderHook(() => useSurvey({
        survey: mockSurvey,
        userId: 'test-user',
        enableAutoSave: false
      }));

      await waitFor(() => {
        expect(result.current.isComplete).toBe(false);
      });

      // Answer required questions only (q1 and q2 are required, q3 is not)
      act(() => {
        result.current.updateAnswer('q1', 'Answer 1');
      });

      await waitFor(() => {
        expect(result.current.isComplete).toBe(false); // Still missing q2
      });

      act(() => {
        result.current.updateAnswer('q2', 'yes');
      });

      await waitFor(() => {
        expect(result.current.isComplete).toBe(true); // Now complete
      });
    });

    test('should handle completion flow correctly', async () => {
      mockSurveyApi.completeSurveyResponse.mockResolvedValue({
        ok: true,
        status: 'completed',
        progress_pct: 100
      });

      const { result } = renderHook(() => useSurvey({
        survey: mockSurvey,
        userId: 'test-user',
        enableAutoSave: false
      }));

      // Complete the survey
      await act(async () => {
        await result.current.goToComplete();
      });

      await waitFor(() => {
        expect(result.current.surveyMode).toBe('complete');
        expect(mockSurveyApi.completeSurveyResponse).toHaveBeenCalledWith('test-user', 'test-survey', {});
      });
    });
  });

  describe('Question Validation with Navigation', () => {
    test('should validate required questions before navigation', async () => {
      const { result } = renderHook(() => useSurvey({
        survey: mockSurvey,
        userId: 'test-user',
        enableAutoSave: false
      }));

      await waitFor(() => {
        expect(result.current.isCurrentQuestionValid).toBe(false);
      });

      // Try to navigate without valid answer
      const initialIndex = result.current.currentQuestionIndex;
      
      act(() => {
        result.current.goToNext();
      });

      expect(result.current.currentQuestionIndex).toBe(initialIndex);

      // Provide valid answer
      act(() => {
        result.current.updateAnswer('q1', 'Valid answer');
      });

      await waitFor(() => {
        expect(result.current.isCurrentQuestionValid).toBe(true);
      });

      // Now navigation should work
      act(() => {
        result.current.goToNext();
      });

      await waitFor(() => {
        expect(result.current.currentQuestionIndex).toBe(1);
      });
    });

    test('should allow navigation to previous questions regardless of validation', async () => {
      const { result } = renderHook(() => useSurvey({
        survey: mockSurvey,
        userId: 'test-user',
        enableAutoSave: false
      }));

      // Navigate to question 1 first
      act(() => {
        result.current.updateAnswer('q1', 'Answer 1');
      });

      act(() => {
        result.current.goToNext();
      });

      await waitFor(() => {
        expect(result.current.currentQuestionIndex).toBe(1);
      });

      // Should be able to go back even without answering current question
      act(() => {
        result.current.goToPrevious();
      });

      await waitFor(() => {
        expect(result.current.currentQuestionIndex).toBe(0);
      });
    });
  });

  describe('Edge Cases', () => {
    test('should handle empty survey gracefully', async () => {
      const emptySurvey = {
        ...mockSurvey,
        questions: []
      };

      const { result } = renderHook(() => useSurvey({
        survey: emptySurvey,
        userId: 'test-user',
        enableAutoSave: false
      }));

      await waitFor(() => {
        expect(result.current.totalQuestions).toBe(0);
        expect(result.current.progressPercentage).toBe(0);
        expect(result.current.currentQuestion).toBeUndefined();
      });
    });

    test('should handle single question survey', async () => {
      const singleQuestionSurvey = {
        ...mockSurvey,
        questions: [mockSurvey.questions[0]]
      };

      const { result } = renderHook(() => useSurvey({
        survey: singleQuestionSurvey,
        userId: 'test-user',
        enableAutoSave: false
      }));

      await waitFor(() => {
        expect(result.current.totalQuestions).toBe(1);
        expect(result.current.isFirstQuestion).toBe(true);
        expect(result.current.isLastQuestion).toBe(true);
      });

      // Answer the question
      act(() => {
        result.current.updateAnswer('q1', 'Answer');
      });

      await waitFor(() => {
        expect(result.current.progressPercentage).toBe(100);
        expect(result.current.isComplete).toBe(true);
      });
    });
  });
});
