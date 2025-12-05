module.exports = {
    env: {
        node: true,
        es2022: true,
        jest: true
    },
    parserOptions: {
        ecmaVersion: 2022,
        sourceType: 'module'
    },
    extends: ['eslint:recommended'],
    rules: {
        'no-unused-vars': ['error', { 'argsIgnorePattern': '^_' }],
        'no-console': 'off',  // Allow console for Lambda logging
        'semi': ['error', 'always'],
        'quotes': ['error', 'single', { 'avoidEscape': true }],
        'indent': ['error', 4],
        'comma-dangle': ['error', 'never'],
        'eqeqeq': ['error', 'always'],
        'curly': ['error', 'all']
    }
};
