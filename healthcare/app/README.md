# Survey App Frontend

This is a [Next.js](https://nextjs.org) project for the Healthcare Agent Survey App, featuring a modern survey interface with backend integration, auto-save functionality, and comprehensive error handling.

## Features

- **Survey Management**: Dynamic survey rendering with multiple question types
- **Backend Integration**: Seamless API integration with FastAPI backend
- **Auto-save**: Automatic answer persistence with configurable intervals
- **Offline Support**: localStorage fallback when backend is unavailable
- **Progress Tracking**: Real-time progress synchronization
- **Error Recovery**: Comprehensive error handling with retry mechanisms
- **Responsive Design**: Mobile-first responsive interface

## Getting Started

### Prerequisites

- Node.js 18+ and pnpm
- Python 3.12+ with the healthcare backend running
- Backend API server running on `http://localhost:8000` (configurable)

### Development Setup

1. Install dependencies:
```bash
pnpm install
```

1. Run the development server:
```bash
pnpm dev
```

1. Open [http://localhost:3000](http://localhost:3000) with your browser to see the result.

You can start editing the page by modifying `app/page.tsx`. The page auto-updates as you edit the file.

This project uses [`next/font`](https://nextjs.org/docs/app/building-your-application/optimizing/fonts) to automatically optimize and load [Geist](https://vercel.com/font), a new font family for Vercel.

## Testing

The Survey App includes comprehensive testing for both frontend components and backend integration.

### Test Structure

```
healthcare/app/
├── lib/__tests__/           # API client tests
│   └── survey-api.test.ts   # TypeScript API client tests
├── hooks/__tests__/         # React hooks tests
│   └── use-survey.test.ts   # Survey hook tests
└── components/__tests__/    # Component tests (future)
```

### Backend Tests

The backend test suite is located in the Python backend and tests the complete integration:

```bash
# From the project root directory
cd /path/to/agno-agent

# Run all frontend integration tests
uv run pytest tests/healthcare/frontend --tb=short

# Run with verbose output
uv run pytest tests/healthcare/frontend -v

# Run specific test class
uv run pytest tests/healthcare/frontend/test_api_integration.py::TestSurveyApiIntegration -v

# Run with timing information
uv run pytest tests/healthcare/frontend --durations=10
```

### Frontend Unit Tests

The frontend test suite is located in:
- `lib/__tests__/survey-api.test.ts` - API client function tests
- `hooks/__tests__/use-survey.test.ts` - React hooks tests

To set up Jest testing (future enhancement):

```bash
# Run all tests
pnpm run test

# Run all tests with watch
pnpm run test:watch

# Run all tests with coverage
pnpm run test:coverage
```

## API Integration

The frontend integrates with the FastAPI backend through a comprehensive API client:

### Survey API Client (`lib/survey-api.ts`)

```typescript
// Load survey definition
const survey = await getSurveyDefinition('personalization')

// Get existing response
const response = await getSurveyResponse('user123', 'personalization')

// Save individual answer
await saveSurveyAnswer('user123', 'personalization', 'age', 25)

// Complete survey
const result = await completeSurveyResponse('user123', 'personalization')
```

### Survey Hook (`hooks/use-survey.ts`)

```typescript
const surveyHook = useSurvey({
  survey: surveyDefinition,
  userId: "user123",
  enableAutoSave: true,
  autoSaveDelay: 2000, // 2 seconds
})

// Hook provides:
// - currentQuestion, answers, progress
// - updateAnswer(), goToNext(), goToPrevious()
// - isLoading, isSaving, error states
// - Auto-save and backend synchronization
```

### Environment Configuration

Create `.env.local` for custom configuration:

```bash
# Backend API URL (default: http://localhost:8000)
NEXT_PUBLIC_API_URL=http://localhost:8000

# Auto-save settings
NEXT_PUBLIC_AUTO_SAVE_DELAY=2000
NEXT_PUBLIC_REQUEST_TIMEOUT=10000
```

## Learn More

To learn more about Next.js, take a look at the following resources:

- [Next.js Documentation](https://nextjs.org/docs) - learn about Next.js features and API.
- [Learn Next.js](https://nextjs.org/learn) - an interactive Next.js tutorial.

You can check out [the Next.js GitHub repository](https://github.com/vercel/next.js) - your feedback and contributions are welcome!

## Deploy on Vercel

The easiest way to deploy your Next.js app is to use the [Vercel Platform](https://vercel.com/new?utm_medium=default-template&filter=next.js&utm_source=create-next-app&utm_campaign=create-next-app-readme) from the creators of Next.js.

Check out our [Next.js deployment documentation](https://nextjs.org/docs/app/building-your-application/deploying) for more details.
