/**
 * AI Requirements Quality Evaluator - Logging Utility
 * 
 * Provides structured logging for CloudWatch integration.
 * Uses JSON format for easy parsing and querying in CloudWatch Logs Insights.
 */

// Log levels with numeric values for filtering
const LOG_LEVELS = {
    DEBUG: 10,
    INFO: 20,
    WARN: 30,
    ERROR: 40
};

// Current log level from environment (defaults to INFO)
const CURRENT_LOG_LEVEL = LOG_LEVELS[process.env.LOG_LEVEL?.toUpperCase()] || LOG_LEVELS.INFO;

/**
 * Logger class for structured logging
 * Outputs JSON-formatted logs for CloudWatch
 */
class Logger {
    /**
     * Logs a message at DEBUG level
     * @param {string} message - Log message
     * @param {Object} data - Additional data to include
     */
    debug(message, data = {}) {
        this.log('DEBUG', message, data);
    }

    /**
     * Logs a message at INFO level
     * @param {string} message - Log message
     * @param {Object} data - Additional data to include
     */
    info(message, data = {}) {
        this.log('INFO', message, data);
    }

    /**
     * Logs a message at WARN level
     * @param {string} message - Log message
     * @param {Object} data - Additional data to include
     */
    warn(message, data = {}) {
        this.log('WARN', message, data);
    }

    /**
     * Logs a message at ERROR level
     * @param {string} message - Log message
     * @param {Object} data - Additional data to include
     */
    error(message, data = {}) {
        this.log('ERROR', message, data);
    }

    /**
     * Internal logging method
     * @param {string} level - Log level
     * @param {string} message - Log message
     * @param {Object} data - Additional data to include
     */
    log(level, message, data) {
        // Skip if below current log level
        if (LOG_LEVELS[level] < CURRENT_LOG_LEVEL) {
            return;
        }

        const logEntry = {
            timestamp: new Date().toISOString(),
            level,
            message,
            ...data
        };

        // Output as JSON for CloudWatch parsing
        const output = JSON.stringify(logEntry);

        // Use appropriate console method based on level
        if (level === 'ERROR') {
            console.error(output);
        } else if (level === 'WARN') {
            console.warn(output);
        } else {
            console.log(output);
        }
    }
}

// Export singleton logger instance
export const logger = new Logger();
