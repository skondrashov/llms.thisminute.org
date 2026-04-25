export default [
  {
    files: ["orchestration/app.js"],
    languageOptions: {
      ecmaVersion: 2020,
      sourceType: "script",
      globals: {
        // Browser globals
        window: "readonly",
        document: "readonly",
        localStorage: "readonly",
        location: "readonly",
        history: "readonly",
        navigator: "readonly",
        fetch: "readonly",
        setTimeout: "readonly",
        clearTimeout: "readonly",
        requestAnimationFrame: "readonly",
        console: "readonly",
        URL: "readonly",
        Blob: "readonly",
        Set: "readonly",
        Map: "readonly",
        JSON: "readonly",
        Object: "readonly",
        Array: "readonly",
        Math: "readonly",
        RegExp: "readonly",
        parseInt: "readonly",
        IntersectionObserver: "readonly",
        MutationObserver: "readonly",
        // External libs loaded before app.js
        mermaid: "readonly",
      }
    },
    rules: {
      "no-undef": "error",
      "no-unused-vars": ["warn", { "args": "none" }]
    }
  }
];
