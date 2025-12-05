/**
 * AI Requirements Quality Evaluator - Frontend Application
 * 
 * This module handles user interactions, API communication,
 * and dynamic rendering of evaluation results.
 */

/**
 * Configuration for the frontend application.
 * 
 * API_ENDPOINT Configuration:
 * - For local development: Use '/api/evaluate' (relative path works with SAM local)
 * - For production: Set window.API_ENDPOINT before loading this script, or
 *   update the default value after deployment with your CloudFront domain:
 *   Example: 'https://d1234abcd.cloudfront.net/api/evaluate'
 * 
 * To set via environment:
 * <script>window.API_ENDPOINT = 'https://your-domain/api/evaluate';</script>
 * <script src="app.js"></script>
 */
const CONFIG = {
    API_ENDPOINT: window.API_ENDPOINT || '/api/evaluate',
    MIN_REQUIREMENT_LENGTH: 10,
    MAX_REQUIREMENT_LENGTH: 2000
};

/**
 * Main function to evaluate a requirement
 * Validates input, sends to API, and displays results
 */
async function evaluateRequirement() {
    const inputElement = document.getElementById('requirement-input');
    const requirement = inputElement.value.trim();

    // Validate input
    const validationError = validateInput(requirement);
    if (validationError) {
        showError(validationError);
        return;
    }

    // Update UI to loading state
    setLoadingState(true);
    hideError();
    hideResults();

    try {
        // Send request to API
        const response = await sendEvaluationRequest(requirement);
        
        // Display results
        displayResults(response);
    } catch (error) {
        console.error('Evaluation failed:', error);
        showError(getErrorMessage(error));
    } finally {
        setLoadingState(false);
    }
}

/**
 * Validates the requirement input
 * @param {string} requirement - The requirement text to validate
 * @returns {string|null} Error message if invalid, null if valid
 */
function validateInput(requirement) {
    if (!requirement) {
        return 'Please enter a requirement to evaluate.';
    }

    if (requirement.length < CONFIG.MIN_REQUIREMENT_LENGTH) {
        return `Requirement must be at least ${CONFIG.MIN_REQUIREMENT_LENGTH} characters long.`;
    }

    if (requirement.length > CONFIG.MAX_REQUIREMENT_LENGTH) {
        return `Requirement must not exceed ${CONFIG.MAX_REQUIREMENT_LENGTH} characters.`;
    }

    return null;
}

/**
 * Sends the evaluation request to the backend API
 * @param {string} requirement - The requirement text to evaluate
 * @returns {Promise<Object>} The evaluation response
 */
async function sendEvaluationRequest(requirement) {
    const response = await fetch(CONFIG.API_ENDPOINT, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({ requirement })
    });

    if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        throw new Error(errorData.message || `HTTP error: ${response.status}`);
    }

    return response.json();
}

/**
 * Displays the evaluation results in the UI
 * @param {Object} results - The evaluation results from the API
 */
function displayResults(results) {
    // Show results section
    const resultsSection = document.getElementById('results-section');
    resultsSection.style.display = 'block';

    // Update overall score
    const overallScore = calculateOverallScore(results);
    document.getElementById('overall-score').textContent = `${overallScore}/10`;

    // Update individual category scores and feedback
    updateCategoryCard('ambiguity', results.ambiguity);
    updateCategoryCard('testability', results.testability);
    updateCategoryCard('completeness', results.completeness);

    // Update suggestions
    updateSuggestions(results.suggestions || []);

    // Scroll to results
    resultsSection.scrollIntoView({ behavior: 'smooth', block: 'start' });
}

/**
 * Calculates the overall score from individual category scores
 * @param {Object} results - The evaluation results
 * @returns {number} The overall score (0-10)
 */
function calculateOverallScore(results) {
    const ambiguityScore = results.ambiguity?.score || 0;
    const testabilityScore = results.testability?.score || 0;
    const completenessScore = results.completeness?.score || 0;

    const average = (ambiguityScore + testabilityScore + completenessScore) / 3;
    return Math.round(average * 10) / 10;
}

/**
 * Updates a category card with score and feedback
 * @param {string} category - The category name (ambiguity, testability, completeness)
 * @param {Object} data - The category data with score and feedback
 */
function updateCategoryCard(category, data) {
    const score = data?.score || 0;
    const feedback = data?.feedback || 'No feedback available.';

    // Update score
    const scoreElement = document.getElementById(`${category}-score`);
    scoreElement.textContent = score;

    // Update feedback
    const feedbackElement = document.getElementById(`${category}-feedback`);
    feedbackElement.textContent = feedback;

    // Update card styling based on score
    const card = document.getElementById(`${category}-card`);
    card.classList.remove('score-high', 'score-medium', 'score-low');
    
    if (score >= 7) {
        card.classList.add('score-high');
    } else if (score >= 4) {
        card.classList.add('score-medium');
    } else {
        card.classList.add('score-low');
    }
}

/**
 * Updates the suggestions list in the UI
 * @param {string[]} suggestions - Array of improvement suggestions
 */
function updateSuggestions(suggestions) {
    const suggestionsList = document.getElementById('suggestions-list');
    suggestionsList.innerHTML = '';

    if (suggestions.length === 0) {
        const li = document.createElement('li');
        li.textContent = 'No specific suggestions - your requirement looks good!';
        suggestionsList.appendChild(li);
        return;
    }

    suggestions.forEach(suggestion => {
        const li = document.createElement('li');
        li.textContent = suggestion;
        suggestionsList.appendChild(li);
    });
}

/**
 * Sets the loading state of the UI
 * @param {boolean} isLoading - Whether the app is in loading state
 */
function setLoadingState(isLoading) {
    const button = document.getElementById('evaluate-btn');
    const buttonText = button.querySelector('.btn-text');
    const buttonLoader = button.querySelector('.btn-loader');

    button.disabled = isLoading;
    buttonText.style.display = isLoading ? 'none' : 'inline';
    buttonLoader.style.display = isLoading ? 'inline' : 'none';
}

/**
 * Shows an error message to the user
 * @param {string} message - The error message to display
 */
function showError(message) {
    const errorSection = document.getElementById('error-section');
    const errorText = document.getElementById('error-text');

    errorText.textContent = message;
    errorSection.style.display = 'block';

    // Scroll to error
    errorSection.scrollIntoView({ behavior: 'smooth', block: 'start' });
}

/**
 * Hides the error section
 */
function hideError() {
    const errorSection = document.getElementById('error-section');
    errorSection.style.display = 'none';
}

/**
 * Hides the results section
 */
function hideResults() {
    const resultsSection = document.getElementById('results-section');
    resultsSection.style.display = 'none';
}

/**
 * Returns a user-friendly error message based on error type
 * @param {Error} error - The error object
 * @returns {string} User-friendly error message
 */
function getErrorMessage(error) {
    if (error.message.includes('429')) {
        return 'Rate limit exceeded. Please wait a moment and try again.';
    }
    if (error.message.includes('NetworkError') || error.message.includes('fetch')) {
        return 'Unable to connect to the server. Please check your connection and try again.';
    }
    return error.message || 'An unexpected error occurred. Please try again.';
}

/**
 * Handles Enter key press in textarea to submit
 */
document.addEventListener('DOMContentLoaded', () => {
    const textarea = document.getElementById('requirement-input');
    
    textarea.addEventListener('keydown', (event) => {
        // Submit on Ctrl+Enter or Cmd+Enter
        if ((event.ctrlKey || event.metaKey) && event.key === 'Enter') {
            event.preventDefault();
            evaluateRequirement();
        }
    });
});
