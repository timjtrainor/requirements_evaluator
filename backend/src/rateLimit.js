/**
 * AI Requirements Quality Evaluator - Rate Limiting
 * 
 * Implements rate limiting using DynamoDB to prevent abuse
 * and ensure fair usage of the API.
 */

import { DynamoDBClient, GetItemCommand, UpdateItemCommand } from '@aws-sdk/client-dynamodb';
import { logger } from './logger.js';

// Initialize DynamoDB client
const dynamoClient = new DynamoDBClient({
    region: process.env.AWS_REGION || 'us-east-1'
});

// Configuration
const TABLE_NAME = process.env.RATE_LIMIT_TABLE || 'requirements-evaluator-rate-limit';
const MAX_REQUESTS_PER_WINDOW = parseInt(process.env.RATE_LIMIT_MAX || '10', 10);
const WINDOW_SIZE_SECONDS = parseInt(process.env.RATE_LIMIT_WINDOW || '60', 10);

/**
 * Checks if the client has exceeded the rate limit
 * @param {string} clientIp - Client IP address
 * @returns {Promise<boolean>} True if rate limited, false otherwise
 */
export async function checkRateLimit(clientIp) {
    // Skip rate limiting for unknown clients or in test mode
    if (clientIp === 'unknown' || process.env.SKIP_RATE_LIMIT === 'true') {
        return false;
    }

    try {
        const now = Math.floor(Date.now() / 1000);
        const windowStart = now - WINDOW_SIZE_SECONDS;

        // Get current rate limit record
        const command = new GetItemCommand({
            TableName: TABLE_NAME,
            Key: {
                pk: { S: `IP#${clientIp}` }
            }
        });

        const response = await dynamoClient.send(command);
        
        if (!response.Item) {
            // No record exists, not rate limited
            return false;
        }

        const lastReset = parseInt(response.Item.lastReset?.N || '0', 10);
        const requestCount = parseInt(response.Item.requestCount?.N || '0', 10);

        // Check if we're in a new window
        if (lastReset < windowStart) {
            // Window has expired, reset count
            return false;
        }

        // Check if limit exceeded
        if (requestCount >= MAX_REQUESTS_PER_WINDOW) {
            logger.warn('Rate limit check: exceeded', { 
                clientIp, 
                requestCount, 
                limit: MAX_REQUESTS_PER_WINDOW 
            });
            return true;
        }

        return false;

    } catch (error) {
        // Log error but don't block request if rate limiting fails
        logger.error('Rate limit check failed', { 
            error: error.message,
            clientIp 
        });
        return false;
    }
}

/**
 * Records a request for rate limiting tracking
 * @param {string} clientIp - Client IP address
 * @returns {Promise<void>}
 */
export async function recordRequest(clientIp) {
    // Skip recording for unknown clients or in test mode
    if (clientIp === 'unknown' || process.env.SKIP_RATE_LIMIT === 'true') {
        return;
    }

    try {
        const now = Math.floor(Date.now() / 1000);
        const windowStart = now - WINDOW_SIZE_SECONDS;
        const ttl = now + WINDOW_SIZE_SECONDS * 2;  // TTL for DynamoDB auto-cleanup

        // Use conditional update to atomically increment counter
        const command = new UpdateItemCommand({
            TableName: TABLE_NAME,
            Key: {
                pk: { S: `IP#${clientIp}` }
            },
            UpdateExpression: `
                SET requestCount = if_not_exists(requestCount, :zero) + :one,
                    lastReset = if_not_exists(lastReset, :now),
                    #ttl = :ttl
            `,
            ConditionExpression: 'attribute_not_exists(lastReset) OR lastReset >= :windowStart',
            ExpressionAttributeNames: {
                '#ttl': 'ttl'
            },
            ExpressionAttributeValues: {
                ':zero': { N: '0' },
                ':one': { N: '1' },
                ':now': { N: now.toString() },
                ':ttl': { N: ttl.toString() },
                ':windowStart': { N: windowStart.toString() }
            }
        });

        await dynamoClient.send(command);
        
        logger.debug('Request recorded for rate limiting', { clientIp });

    } catch (error) {
        // If condition failed, window has expired - reset the counter
        if (error.name === 'ConditionalCheckFailedException') {
            await resetRateLimitCounter(clientIp);
            return;
        }

        // Log error but don't fail the request
        logger.error('Failed to record request for rate limiting', { 
            error: error.message,
            clientIp 
        });
    }
}

/**
 * Resets the rate limit counter for a client
 * @param {string} clientIp - Client IP address
 * @returns {Promise<void>}
 */
async function resetRateLimitCounter(clientIp) {
    try {
        const now = Math.floor(Date.now() / 1000);
        const ttl = now + WINDOW_SIZE_SECONDS * 2;

        const command = new UpdateItemCommand({
            TableName: TABLE_NAME,
            Key: {
                pk: { S: `IP#${clientIp}` }
            },
            UpdateExpression: 'SET requestCount = :one, lastReset = :now, #ttl = :ttl',
            ExpressionAttributeNames: {
                '#ttl': 'ttl'
            },
            ExpressionAttributeValues: {
                ':one': { N: '1' },
                ':now': { N: now.toString() },
                ':ttl': { N: ttl.toString() }
            }
        });

        await dynamoClient.send(command);
        
        logger.debug('Rate limit counter reset', { clientIp });

    } catch (error) {
        logger.error('Failed to reset rate limit counter', { 
            error: error.message,
            clientIp 
        });
    }
}
