/**
 * AI Requirements Quality Evaluator - Bedrock Integration
 * 
 * Handles communication with Amazon Bedrock to evaluate
 * software requirements for ambiguity, testability, and completeness.
 */

import { BedrockRuntimeClient, InvokeModelCommand } from '@aws-sdk/client-bedrock-runtime';
import { logger } from './logger.js';

// Initialize Bedrock client
const bedrockClient = new BedrockRuntimeClient({
    region: process.env.AWS_REGION || 'us-east-1'
});

// Model configuration - using Claude 3 Sonnet for quality responses
const MODEL_ID = process.env.BEDROCK_MODEL_ID || 'anthropic.claude-3-sonnet-20240229-v1:0';

// Maximum number of suggestions to return in the evaluation response
const MAX_SUGGESTIONS = 5;

/**
 * Evaluation prompt template for the AI model
 * This prompt guides the model to provide structured evaluation
 */
const EVALUATION_PROMPT = `You are an expert software requirements analyst. Analyze the following software requirement and evaluate it on three dimensions: Ambiguity, Testability, and Completeness.

For each dimension, provide:
1. A score from 1-10 (where 10 is best)
2. A brief explanation of the score

Additionally, provide specific suggestions for improvement.

Requirement to evaluate:
"{requirement}"

Respond in the following JSON format only (no additional text):
{
    "ambiguity": {
        "score": <number 1-10>,
        "feedback": "<explanation of ambiguity score>"
    },
    "testability": {
        "score": <number 1-10>,
        "feedback": "<explanation of testability score>"
    },
    "completeness": {
        "score": <number 1-10>,
        "feedback": "<explanation of completeness score>"
    },
    "suggestions": [
        "<suggestion 1>",
        "<suggestion 2>",
        "<suggestion 3>"
    ]
}

Scoring Guidelines:
- Ambiguity (10 = completely clear, 1 = very ambiguous): Consider vague terms, unclear references, subjective language
- Testability (10 = easily testable, 1 = cannot be tested): Consider measurable criteria, acceptance conditions, quantifiable outcomes
- Completeness (10 = fully complete, 1 = severely lacking): Consider actors, actions, conditions, constraints, success criteria`;

/**
 * Evaluates a software requirement using Amazon Bedrock
 * @param {string} requirement - The requirement text to evaluate
 * @returns {Promise<Object>} Structured evaluation results
 */
export async function evaluateRequirement(requirement) {
    logger.info('Starting Bedrock evaluation', { 
        modelId: MODEL_ID,
        requirementLength: requirement.length 
    });

    // Prepare the prompt with the requirement
    const prompt = EVALUATION_PROMPT.replace('{requirement}', requirement);

    // Prepare the request body for Claude model
    const requestBody = {
        anthropic_version: 'bedrock-2023-05-31',
        max_tokens: 1024,
        messages: [
            {
                role: 'user',
                content: prompt
            }
        ],
        // Temperature 0.3: Lower value for more deterministic, consistent evaluations.
        // Higher values (0.7-1.0) increase creativity but reduce reproducibility.
        // For quality assessments, consistency is preferred over variety.
        temperature: 0.3
    };

    try {
        const command = new InvokeModelCommand({
            modelId: MODEL_ID,
            contentType: 'application/json',
            accept: 'application/json',
            body: JSON.stringify(requestBody)
        });

        const response = await bedrockClient.send(command);
        
        // Parse the response
        const responseBody = JSON.parse(new TextDecoder().decode(response.body));
        
        logger.debug('Bedrock response received', { 
            stopReason: responseBody.stop_reason 
        });

        // Extract the content from Claude's response
        const content = responseBody.content?.[0]?.text;
        
        if (!content) {
            throw new Error('Empty response from Bedrock');
        }

        // Parse the JSON evaluation from the response
        const evaluation = parseEvaluationResponse(content);
        
        return evaluation;

    } catch (error) {
        logger.error('Bedrock evaluation failed', { 
            error: error.message,
            modelId: MODEL_ID 
        });
        
        // Re-throw with more context
        throw new Error(`Bedrock evaluation failed: ${error.message}`);
    }
}

/**
 * Parses the AI response and extracts structured evaluation
 * @param {string} content - Raw response content from the model
 * @returns {Object} Parsed evaluation object
 */
function parseEvaluationResponse(content) {
    try {
        // Try to find JSON in the response (in case there's extra text)
        const jsonMatch = content.match(/\{[\s\S]*\}/);
        
        if (!jsonMatch) {
            throw new Error('No JSON found in response');
        }

        const evaluation = JSON.parse(jsonMatch[0]);

        // Validate and sanitize the response structure
        return {
            ambiguity: validateCategory(evaluation.ambiguity, 'ambiguity'),
            testability: validateCategory(evaluation.testability, 'testability'),
            completeness: validateCategory(evaluation.completeness, 'completeness'),
            suggestions: validateSuggestions(evaluation.suggestions)
        };

    } catch (error) {
        logger.error('Failed to parse evaluation response', { 
            error: error.message,
            content: content.substring(0, 200) 
        });
        
        // Return a default response if parsing fails
        return getDefaultEvaluation();
    }
}

/**
 * Validates and normalizes a category evaluation
 * @param {Object} category - Category evaluation object
 * @param {string} name - Category name for error messages
 * @returns {Object} Validated category object
 */
function validateCategory(category, name) {
    const score = typeof category?.score === 'number' 
        ? Math.max(1, Math.min(10, Math.round(category.score)))
        : 5;

    const feedback = typeof category?.feedback === 'string'
        ? category.feedback.trim()
        : `Unable to evaluate ${name}.`;

    return { score, feedback };
}

/**
 * Validates and normalizes suggestions array
 * @param {Array} suggestions - Array of suggestion strings
 * @returns {Array} Validated suggestions array
 */
function validateSuggestions(suggestions) {
    if (!Array.isArray(suggestions)) {
        return [];
    }

    return suggestions
        .filter(s => typeof s === 'string' && s.trim().length > 0)
        .map(s => s.trim())
        .slice(0, MAX_SUGGESTIONS);
}

/**
 * Returns a default evaluation when parsing fails
 * @returns {Object} Default evaluation object
 */
function getDefaultEvaluation() {
    return {
        ambiguity: {
            score: 5,
            feedback: 'Unable to fully evaluate ambiguity. Please try again.'
        },
        testability: {
            score: 5,
            feedback: 'Unable to fully evaluate testability. Please try again.'
        },
        completeness: {
            score: 5,
            feedback: 'Unable to fully evaluate completeness. Please try again.'
        },
        suggestions: ['Please try submitting your requirement again.']
    };
}
