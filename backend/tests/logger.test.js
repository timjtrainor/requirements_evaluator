/**
 * Tests for the logger utility
 */

import { jest } from '@jest/globals';

// Store original console methods
const originalConsole = {
    log: console.log,
    warn: console.warn,
    error: console.error
};

describe('Logger', () => {
    let logger;

    beforeAll(async () => {
        // Reset module cache and import fresh
        jest.resetModules();
        const loggerModule = await import('../src/logger.js');
        logger = loggerModule.logger;
    });

    beforeEach(() => {
        // Mock console methods
        console.log = jest.fn();
        console.warn = jest.fn();
        console.error = jest.fn();
    });

    afterEach(() => {
        // Restore console methods
        console.log = originalConsole.log;
        console.warn = originalConsole.warn;
        console.error = originalConsole.error;
    });

    test('logs info messages with JSON format', () => {
        logger.info('Test message', { key: 'value' });
        
        expect(console.log).toHaveBeenCalled();
        const logOutput = console.log.mock.calls[0][0];
        const parsed = JSON.parse(logOutput);
        
        expect(parsed.level).toBe('INFO');
        expect(parsed.message).toBe('Test message');
        expect(parsed.key).toBe('value');
        expect(parsed.timestamp).toBeDefined();
    });

    test('logs warn messages using console.warn', () => {
        logger.warn('Warning message');
        
        expect(console.warn).toHaveBeenCalled();
        const logOutput = console.warn.mock.calls[0][0];
        const parsed = JSON.parse(logOutput);
        
        expect(parsed.level).toBe('WARN');
        expect(parsed.message).toBe('Warning message');
    });

    test('logs error messages using console.error', () => {
        logger.error('Error message', { error: 'test error' });
        
        expect(console.error).toHaveBeenCalled();
        const logOutput = console.error.mock.calls[0][0];
        const parsed = JSON.parse(logOutput);
        
        expect(parsed.level).toBe('ERROR');
        expect(parsed.message).toBe('Error message');
        expect(parsed.error).toBe('test error');
    });

    test('includes timestamp in all log messages', () => {
        logger.info('Timestamp test');
        
        const logOutput = console.log.mock.calls[0][0];
        const parsed = JSON.parse(logOutput);
        
        expect(parsed.timestamp).toMatch(/^\d{4}-\d{2}-\d{2}T/);
    });
});
