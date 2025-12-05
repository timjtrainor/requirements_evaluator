/**
 * Tests for the Lambda handler
 */

import { jest } from '@jest/globals';

// Mock dependencies before importing the handler
jest.unstable_mockModule('../src/evaluator.js', () => ({
    evaluateRequirement: jest.fn()
}));

jest.unstable_mockModule('../src/rateLimit.js', () => ({
    checkRateLimit: jest.fn(),
    recordRequest: jest.fn()
}));

jest.unstable_mockModule('../src/logger.js', () => ({
    logger: {
        info: jest.fn(),
        debug: jest.fn(),
        warn: jest.fn(),
        error: jest.fn()
    }
}));

// Import after mocking
const { handler } = await import('../src/index.js');
const { evaluateRequirement } = await import('../src/evaluator.js');
const { checkRateLimit, recordRequest } = await import('../src/rateLimit.js');

describe('Lambda Handler', () => {
    beforeEach(() => {
        jest.clearAllMocks();
        checkRateLimit.mockResolvedValue(false);
        recordRequest.mockResolvedValue();
    });

    const createEvent = (body, method = 'POST') => ({
        httpMethod: method,
        body: typeof body === 'string' ? body : JSON.stringify(body),
        path: '/evaluate',
        requestContext: {
            identity: {
                sourceIp: '192.168.1.1'
            }
        },
        headers: {}
    });

    const mockContext = {
        awsRequestId: 'test-request-123'
    };

    test('handles OPTIONS request for CORS', async () => {
        const event = createEvent(null, 'OPTIONS');
        
        const response = await handler(event, mockContext);
        
        expect(response.statusCode).toBe(200);
        expect(response.headers['Access-Control-Allow-Origin']).toBe('*');
    });

    test('returns 400 for missing requirement', async () => {
        const event = createEvent({});
        
        const response = await handler(event, mockContext);
        
        expect(response.statusCode).toBe(400);
        const body = JSON.parse(response.body);
        expect(body.message).toContain('Missing required field');
    });

    test('returns 400 for short requirement', async () => {
        const event = createEvent({ requirement: 'short' });
        
        const response = await handler(event, mockContext);
        
        expect(response.statusCode).toBe(400);
        const body = JSON.parse(response.body);
        expect(body.message).toContain('at least 10 characters');
    });

    test('returns 400 for requirement exceeding max length', async () => {
        const event = createEvent({ requirement: 'a'.repeat(2001) });
        
        const response = await handler(event, mockContext);
        
        expect(response.statusCode).toBe(400);
        const body = JSON.parse(response.body);
        expect(body.message).toContain('2000 characters');
    });

    test('returns 429 when rate limited', async () => {
        checkRateLimit.mockResolvedValue(true);
        const event = createEvent({ requirement: 'This is a valid requirement to test' });
        
        const response = await handler(event, mockContext);
        
        expect(response.statusCode).toBe(429);
        const body = JSON.parse(response.body);
        expect(body.message).toContain('Rate limit');
    });

    test('successfully evaluates valid requirement', async () => {
        const mockEvaluation = {
            ambiguity: { score: 8, feedback: 'Clear requirement' },
            testability: { score: 7, feedback: 'Can be tested' },
            completeness: { score: 9, feedback: 'Complete specification' },
            suggestions: ['Add acceptance criteria']
        };
        evaluateRequirement.mockResolvedValue(mockEvaluation);
        
        const event = createEvent({ requirement: 'The system shall allow users to log in' });
        
        const response = await handler(event, mockContext);
        
        expect(response.statusCode).toBe(200);
        const body = JSON.parse(response.body);
        expect(body.ambiguity.score).toBe(8);
        expect(body.testability.score).toBe(7);
        expect(body.completeness.score).toBe(9);
    });

    test('handles evaluation errors gracefully', async () => {
        evaluateRequirement.mockRejectedValue(new Error('Bedrock error'));
        
        const event = createEvent({ requirement: 'This is a valid requirement to test' });
        
        const response = await handler(event, mockContext);
        
        expect(response.statusCode).toBe(500);
        const body = JSON.parse(response.body);
        expect(body.error).toBe('Internal Server Error');
    });

    test('handles invalid JSON in request body', async () => {
        const event = {
            ...createEvent(null, 'POST'),
            body: 'invalid json {'
        };
        
        const response = await handler(event, mockContext);
        
        expect(response.statusCode).toBe(400);
    });
});
