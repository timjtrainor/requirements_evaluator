/**
 * AI Requirements Quality Evaluator - Lambda Handler
 * 
 * Main entry point for the AWS Lambda function.
 * Handles API Gateway requests and orchestrates the evaluation process.
 */

import { evaluateRequirement } from './evaluator.js';
import { checkRateLimit, recordRequest } from './rateLimit.js';
import { logger } from './logger.js';

// CORS headers for API Gateway responses
const CORS_HEADERS = {
    'Access-Control-Allow-Origin': '*',
    'Access-Control-Allow-Headers': 'Content-Type,Authorization',
    'Access-Control-Allow-Methods': 'POST,OPTIONS',
    'Content-Type': 'application/json'
};

/**
 * Lambda handler function
 * @param {Object} event - API Gateway event
 * @param {Object} context - Lambda context
 * @returns {Object} API Gateway response
 */
export async function handler(event, context) {
    const requestId = context.awsRequestId || 'local-request';
    
    logger.info('Received request', { 
        requestId, 
        path: event.path,
        method: event.httpMethod 
    });

    // Handle CORS preflight
    if (event.httpMethod === 'OPTIONS') {
        return createResponse(200, { message: 'OK' });
    }

    try {
        // Parse and validate request body
        const body = parseRequestBody(event.body);
        
        if (!body.requirement) {
            return createResponse(400, { 
                error: 'Bad Request',
                message: 'Missing required field: requirement' 
            });
        }

        // Validate requirement length
        const requirement = body.requirement.trim();
        if (requirement.length < 10) {
            return createResponse(400, {
                error: 'Bad Request',
                message: 'Requirement must be at least 10 characters long'
            });
        }

        if (requirement.length > 2000) {
            return createResponse(400, {
                error: 'Bad Request',
                message: 'Requirement must not exceed 2000 characters'
            });
        }

        // Check rate limit using client IP
        const clientIp = getClientIp(event);
        const isRateLimited = await checkRateLimit(clientIp);
        
        if (isRateLimited) {
            logger.warn('Rate limit exceeded', { clientIp, requestId });
            return createResponse(429, {
                error: 'Too Many Requests',
                message: 'Rate limit exceeded. Please try again later.'
            });
        }

        // Record this request for rate limiting
        await recordRequest(clientIp);

        // Evaluate the requirement using Bedrock
        logger.info('Evaluating requirement', { 
            requestId, 
            requirementLength: requirement.length 
        });
        
        const evaluation = await evaluateRequirement(requirement);

        logger.info('Evaluation completed', { requestId });

        return createResponse(200, evaluation);

    } catch (error) {
        logger.error('Error processing request', { 
            requestId, 
            error: error.message,
            stack: error.stack 
        });

        // Return appropriate error response
        if (error.name === 'ValidationError') {
            return createResponse(400, {
                error: 'Bad Request',
                message: error.message
            });
        }

        return createResponse(500, {
            error: 'Internal Server Error',
            message: 'An error occurred while processing your request'
        });
    }
}

/**
 * Creates a properly formatted API Gateway response
 * @param {number} statusCode - HTTP status code
 * @param {Object} body - Response body
 * @returns {Object} API Gateway response object
 */
function createResponse(statusCode, body) {
    return {
        statusCode,
        headers: CORS_HEADERS,
        body: JSON.stringify(body)
    };
}

/**
 * Parses the request body from JSON string
 * @param {string} body - Request body string
 * @returns {Object} Parsed body object
 */
function parseRequestBody(body) {
    if (!body) {
        return {};
    }

    try {
        return JSON.parse(body);
    } catch {
        throw new ValidationError('Invalid JSON in request body');
    }
}

/**
 * Extracts client IP from API Gateway event
 * @param {Object} event - API Gateway event
 * @returns {string} Client IP address
 */
function getClientIp(event) {
    // Try to get IP from various possible locations
    if (event.requestContext?.identity?.sourceIp) {
        return event.requestContext.identity.sourceIp;
    }
    
    // Check X-Forwarded-For header (set by CloudFront/ALB)
    const forwardedFor = event.headers?.['X-Forwarded-For'] 
        || event.headers?.['x-forwarded-for'];
    
    if (forwardedFor) {
        // Take the first IP in the chain (original client)
        return forwardedFor.split(',')[0].trim();
    }

    return 'unknown';
}

/**
 * Custom validation error class
 */
class ValidationError extends Error {
    constructor(message) {
        super(message);
        this.name = 'ValidationError';
    }
}
