/**
 * AI Requirements Quality Evaluator - Frontend Application
 * 
 * Handles user interactions, API communication, and result rendering.
 */

// =============================================================================
// Configuration
// =============================================================================

/**
 * API Configuration
 * Replace API_BASE_URL with your actual API Gateway or CloudFront URL after deployment.
 * 
 * For local development with SAM: http://localhost:3000
 * For production: https://your-cloudfront-domain.cloudfront.net
 */
const CONFIG = {
    API_BASE_URL: '', // Set this after deployment (e.g., 'https://d1234abcd.cloudfront.net')
    EVALUATE_ENDPOINT: '/evaluate'
};

// =============================================================================
// DOM Elements
// =============================================================================

const elements = {
    input: document.getElementById('requirement-input'),
    button: document.getElementById('evaluate-btn'),
    buttonText: document.querySelector('.btn-text'),
    buttonLoader: document.querySelector('.btn-loader'),
    resultsSection: document.getElementById('results-section'),
    errorSection: document.getElementById('error-section'),
    errorText: document.getElementById('error-text'),
    // Result elements
    ambiguityIndicator: document.getElementById('ambiguity-indicator'),
    ambiguityDetails: document.getElementById('ambiguity-details'),
    ambiguityCard: document.getElementById('ambiguity-card'),
    testabilityIndicator: document.getElementById('testability-indicator'),
    testabilityDetails: document.getElementById('testability-details'),
    testabilityCard: document.getElementById('testability-card'),
    completenessScore: document.getElementById('completeness-score'),
    completenessDetails: document.getElementById('completeness-details'),
    completenessCard: document.getElementById('completeness-card'),
    issuesList: document.getElementById('issues-list'),
    suggestionsList: document.getElementById('suggestions-list')
};

// =============================================================================
// API Functions
// =============================================================================

/**
 * Get the full API URL for the evaluate endpoint.
 */
function getApiUrl() {
    return CONFIG.API_BASE_URL + CONFIG.EVALUATE_ENDPOINT;
}

/**
 * Send a requirement to the API for evaluation.
 * @param {string} requirementText - The requirement text to evaluate
 * @returns {Promise<Object>} - The evaluation results
 */
async function evaluateRequirement(requirementText) {
    const response = await fetch(getApiUrl(), {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({ requirementText })
    });

    const data = await response.json();

    if (!response.ok) {
        throw new Error(data.error || `HTTP error: ${response.status}`);
    }

    return data;
}

// =============================================================================
// UI Functions
// =============================================================================

/**
 * Set the loading state of the UI.
 */
function setLoading(isLoading) {
    elements.button.disabled = isLoading;
    elements.buttonText.style.display = isLoading ? 'none' : 'inline';
    elements.buttonLoader.style.display = isLoading ? 'inline' : 'none';
}

/**
 * Show an error message.
 */
function showError(message) {
    elements.errorText.textContent = message;
    elements.errorSection.style.display = 'block';
    elements.resultsSection.style.display = 'none';
}

/**
 * Hide error messages.
 */
function hideError() {
    elements.errorSection.style.display = 'none';
}

/**
 * Display the evaluation results.
 */
function displayResults(results) {
    // Ambiguity
    const ambiguityDetected = results.ambiguity_detected;
    elements.ambiguityIndicator.textContent = ambiguityDetected ? 'Detected' : 'Clear';
    elements.ambiguityIndicator.className = 'indicator ' + (ambiguityDetected ? 'status-bad' : 'status-good');
    elements.ambiguityDetails.textContent = results.ambiguity_details || '';

    // Testability
    const isTestable = results.testable;
    elements.testabilityIndicator.textContent = isTestable ? 'Testable' : 'Not Testable';
    elements.testabilityIndicator.className = 'indicator ' + (isTestable ? 'status-good' : 'status-bad');
    elements.testabilityDetails.textContent = results.testability_details || '';

    // Completeness
    const completenessScore = results.completeness_score || 0;
    elements.completenessScore.textContent = `${completenessScore}/10`;
    elements.completenessScore.className = 'score ' + getScoreClass(completenessScore);
    elements.completenessDetails.textContent = results.completeness_details || '';

    // Issues
    elements.issuesList.innerHTML = '';
    const issues = results.issues || [];
    if (issues.length === 0) {
        const li = document.createElement('li');
        li.textContent = 'No issues found';
        elements.issuesList.appendChild(li);
    } else {
        issues.forEach(issue => {
            const li = document.createElement('li');
            li.textContent = issue;
            elements.issuesList.appendChild(li);
        });
    }

    // Suggestions
    elements.suggestionsList.innerHTML = '';
    const suggestions = results.suggestions || [];
    if (suggestions.length === 0) {
        const li = document.createElement('li');
        li.textContent = 'No suggestions';
        elements.suggestionsList.appendChild(li);
    } else {
        suggestions.forEach(suggestion => {
            const li = document.createElement('li');
            li.textContent = suggestion;
            elements.suggestionsList.appendChild(li);
        });
    }

    // Show results
    elements.resultsSection.style.display = 'block';
    elements.resultsSection.scrollIntoView({ behavior: 'smooth', block: 'start' });
}

/**
 * Get CSS class based on completeness score.
 */
function getScoreClass(score) {
    if (score >= 7) return 'score-high';
    if (score >= 4) return 'score-medium';
    return 'score-low';
}

/**
 * Get user-friendly error message.
 */
function getErrorMessage(error) {
    if (error.message.includes('429')) {
        return 'Rate limit exceeded. Please try again later.';
    }
    if (error.message.includes('NetworkError') || error.message.includes('Failed to fetch')) {
        return 'Unable to connect to the server. Please check your connection.';
    }
    return error.message || 'An unexpected error occurred.';
}

// =============================================================================
// Event Handlers
// =============================================================================

/**
 * Handle the evaluate button click.
 */
async function handleEvaluate() {
    const requirementText = elements.input.value.trim();

    // Validate input
    if (!requirementText) {
        showError('Please enter a requirement to evaluate.');
        return;
    }

    if (requirementText.length < 10) {
        showError('Requirement must be at least 10 characters long.');
        return;
    }

    // Start evaluation
    hideError();
    setLoading(true);
    elements.resultsSection.style.display = 'none';

    try {
        const results = await evaluateRequirement(requirementText);
        displayResults(results);
    } catch (error) {
        console.error('Evaluation error:', error);
        showError(getErrorMessage(error));
    } finally {
        setLoading(false);
    }
}

// =============================================================================
// Initialization
// =============================================================================

document.addEventListener('DOMContentLoaded', () => {
    // Button click handler
    elements.button.addEventListener('click', handleEvaluate);

    // Ctrl+Enter to submit
    elements.input.addEventListener('keydown', (event) => {
        if ((event.ctrlKey || event.metaKey) && event.key === 'Enter') {
            event.preventDefault();
            handleEvaluate();
        }
    });
});
