import { defineConfig } from '@playwright/test';

export default defineConfig({
  testDir: './orchestration/tests/e2e',
  timeout: 30000,
  retries: 0,
  use: {
    baseURL: 'http://localhost:3939',
    // Block mermaid CDN to avoid flaky network dependencies
    // The page handles mermaid being undefined gracefully
  },
  webServer: {
    command: 'npx serve -l 3939 --no-clipboard',
    port: 3939,
    reuseExistingServer: true,
  },
  projects: [
    { name: 'chromium', use: { browserName: 'chromium' } },
  ],
});
