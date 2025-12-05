export default {
    testEnvironment: 'node',
    transform: {},
    moduleNameMapper: {},
    testMatch: ['**/tests/**/*.test.js'],
    collectCoverage: true,
    coverageDirectory: 'coverage',
    coverageReporters: ['text', 'lcov'],
    verbose: true
};
