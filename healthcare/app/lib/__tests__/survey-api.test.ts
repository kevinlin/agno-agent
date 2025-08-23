/**
 * Tests for Survey API Client Functions
 */

import {
  getSurveyDefinition,
  getSurveyResponse,
  saveSurveyResponse,
  completeSurveyResponse,
  generateSurveyLink,
  getSurveyCatalog,
  SurveyApiError,
  isNetworkError,
  isClientError,
  formatErrorMessage,
  API_CONFIG,
} from '../survey-api';

// Mock fetch for testing
const mockFetch = jest.fn() as jest.MockedFunction<typeof fetch>;

// Mock implementation setup
beforeEach(() => {
  global.fetch = mockFetch;
  mockFetch.mockClear();
});

describe('Survey API Client', () => {
  describe('getSurveyDefinition', () => {
    test('should fetch survey definition successfully', async () => {
      const mockSurvey = {
        code: 'test-survey',
        title: 'Test Survey',
        questions: [
          {
            type: 'INPUT',
            code: 'age',
            title: 'What is your age?',
            required: true,
          }
        ]
      }

      mockFetch.mockResolvedValueOnce({
        ok: true,
        headers: { get: () => 'application/json' },
        json: async () => mockSurvey,
      } as Response);

      const result = await getSurveyDefinition('test-survey');
      expect(result).toEqual(mockSurvey);
      expect(mockFetch).toHaveBeenCalledWith(
        'http://localhost:8000/api/survey/test-survey',
        expect.objectContaining({
          headers: expect.objectContaining({
            'Content-Type': 'application/json',
          }),
        })
      );
    })

    test('should handle 404 error for non-existent survey', async () => {
      const mockError = {
        ok: false,
        error: {
          code: 'survey_not_found',
          message: 'Survey not found',
          details: 'The requested survey does not exist'
        }
      }

      mockFetch.mockResolvedValueOnce({
        ok: false,
        status: 404,
        headers: { get: () => 'application/json' },
        json: async () => mockError,
      } as Response);

      await expect(getSurveyDefinition('non-existent')).rejects.toThrow(SurveyApiError);
    })

    test('should handle network timeout', async () => {
      const abortError = new Error('The operation was aborted');
      abortError.name = 'AbortError';
      
      mockFetch.mockRejectedValueOnce(abortError);

      await expect(getSurveyDefinition('test-survey')).rejects.toThrow();
    })

    test('should retry on server errors', async () => {
      // First call fails with 500
      mockFetch
        .mockResolvedValueOnce({
          ok: false,
          status: 500,
          headers: { get: () => 'application/json' },
          json: async () => ({ 
            ok: false,
            error: { 
              code: 'server_error',
              message: 'Internal server error' 
            }
          }),
        } as Response)
        // Second call succeeds
        .mockResolvedValueOnce({
          ok: true,
          headers: { get: () => 'application/json' },
          json: async () => ({ code: 'test-survey' }),
        } as Response);

      const result = await getSurveyDefinition('test-survey');
      expect(result.code).toBe('test-survey');
      expect(mockFetch).toHaveBeenCalledTimes(2);
    })
  })

  describe('getSurveyResponse', () => {
    test('should fetch existing survey response', async () => {
      const mockResponse = {
        ok: true,
        status: 'in_progress',
        progress_pct: 50,
        user_response: {
          age: 25
        }
      }

      mockFetch.mockResolvedValueOnce({
        ok: true,
        headers: { get: () => 'application/json' },
        json: async () => mockResponse,
      } as Response);

      const result = await getSurveyResponse('user123', 'test-survey');
      expect(result).toEqual(mockResponse);
      expect(mockFetch).toHaveBeenCalledWith(
        'http://localhost:8000/api/survey-response?user_id=user123&survey_code=test-survey',
        expect.any(Object)
      );
    })

    test('should handle new user with no existing response', async () => {
      const mockResponse = {
        ok: true,
        status: 'in_progress',
        progress_pct: 0,
        user_response: {}
      }

      mockFetch.mockResolvedValueOnce({
        ok: true,
        headers: { get: () => 'application/json' },
        json: async () => mockResponse,
      } as Response);

      const result = await getSurveyResponse('new_user', 'test-survey');
      expect(result.progress_pct).toBe(0);
      expect(result.user_response).toEqual({});
    })
  })

  describe('saveSurveyResponse', () => {
    test('should save survey response successfully', async () => {
      const mockResponse = {
        ok: true,
        progress_pct: 33,
        status: 'in_progress'
      }

      mockFetch.mockResolvedValueOnce({
        ok: true,
        headers: { get: () => 'application/json' },
        json: async () => mockResponse,
      } as Response);

      const result = await saveSurveyResponse('user123', 'test-survey', { age: 25 }, 'in_progress');
      expect(result).toEqual(mockResponse);
      expect(mockFetch).toHaveBeenCalledWith(
        'http://localhost:8000/api/survey-response?user_id=user123&survey_code=test-survey',
        expect.objectContaining({
          method: 'POST',
          body: JSON.stringify({
            user_response: { age: 25 },
            status: 'in_progress'
          }),
        })
      );
    })

    test('should handle validation errors', async () => {
      const mockError = {
        ok: false,
        error: {
          code: 'validation_error',
          message: 'Invalid response data',
          details: 'User response cannot be empty'
        }
      }

      mockFetch.mockResolvedValueOnce({
        ok: false,
        status: 400,
        headers: { get: () => 'application/json' },
        json: async () => mockError,
      } as Response);

      await expect(saveSurveyResponse('user123', 'test-survey', {}, 'in_progress'))
        .rejects.toThrow(SurveyApiError);
    })
  })

  describe('completeSurveyResponse', () => {
    test('should complete survey successfully', async () => {
      const mockResponse = {
        ok: true,
        status: 'completed',
        progress_pct: 100
      }

      mockFetch.mockResolvedValueOnce({
        ok: true,
        headers: { get: () => 'application/json' },
        json: async () => mockResponse,
      } as Response);

      const userResponse = { height: 170, weight: 65, age: 25 };
      const result = await completeSurveyResponse('user123', 'test-survey', userResponse);
      expect(result.status).toBe('completed');
      expect(result.progress_pct).toBe(100);
    })

    test('should handle incomplete survey error', async () => {
      const mockError = {
        ok: false,
        error: {
          code: 'survey_incomplete',
          message: 'Survey cannot be completed',
          details: 'Required questions not answered'
        }
      }

      mockFetch.mockResolvedValueOnce({
        ok: false,
        status: 400,
        headers: { get: () => 'application/json' },
        json: async () => mockError,
      } as Response);

      await expect(completeSurveyResponse('user123', 'test-survey'))
        .rejects.toThrow(SurveyApiError);
    })
  })

  describe('Error handling utilities', () => {
    test('isNetworkError should identify network errors correctly', () => {
      const networkError = new SurveyApiError('timeout', 'Request timed out');
      const serverError = new SurveyApiError('server_error', 'Server error', '', 500);
      const clientError = new SurveyApiError('validation_error', 'Validation error', '', 400);

      expect(isNetworkError(networkError)).toBe(true);
      expect(isNetworkError(serverError)).toBe(true);
      expect(isNetworkError(clientError)).toBe(false);
    })

    test('isClientError should identify client errors correctly', () => {
      const clientError = new SurveyApiError('validation_error', 'Validation error', '', 400);
      const serverError = new SurveyApiError('server_error', 'Server error', '', 500);

      expect(isClientError(clientError)).toBe(true);
      expect(isClientError(serverError)).toBe(false);
    })

    test('formatErrorMessage should format errors for user display', () => {
      const timeoutError = new SurveyApiError('timeout', 'Request timed out');
      const surveyNotFoundError = new SurveyApiError('survey_not_found', 'Survey not found');
      const genericError = new Error('Generic error');

      expect(formatErrorMessage(timeoutError)).toBe('Request timed out. Please check your connection and try again.');
      expect(formatErrorMessage(surveyNotFoundError)).toBe('Survey not found. Please check the survey code.');
      expect(formatErrorMessage(genericError)).toBe('An unexpected error occurred. Please try again.');
    })
  })

  describe('Retry logic', () => {
    test('should retry failed requests with exponential backoff', async () => {
      // For this test, we'll just verify that retries happen
      // The actual retry logic with delays is complex to test with timers
      mockFetch
        .mockRejectedValueOnce(new Error('Network error'))
        .mockRejectedValueOnce(new Error('Network error'))
        .mockResolvedValueOnce({
          ok: true,
          headers: { get: () => 'application/json' },
          json: async () => ({ code: 'test-survey' }),
        } as Response);

      const result = await getSurveyDefinition('test-survey');
      expect(result.code).toBe('test-survey');
      expect(mockFetch).toHaveBeenCalledTimes(3);
    })

    test('should not retry client errors', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: false,
        status: 400,
        headers: { get: () => 'application/json' },
        json: async () => ({
          ok: false,
          error: { code: 'validation_error', message: 'Bad request' }
        }),
      } as Response);

      await expect(getSurveyDefinition('test-survey')).rejects.toThrow(SurveyApiError);
      expect(mockFetch).toHaveBeenCalledTimes(1); // Should not retry
    })
  })
})

describe('API Configuration', () => {
  test('should use correct base URL from environment', () => {
    // Test that API_CONFIG uses the correct base URL
    expect(API_CONFIG.baseUrl).toBe(process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000');
  })

  test('should have appropriate timeout settings', () => {
    expect(API_CONFIG.timeout).toBe(10000);
    expect(API_CONFIG.retryAttempts).toBe(3);
    expect(API_CONFIG.retryDelay).toBe(1000);
  })
})

// Export for potential use in other test files
export { mockFetch }
