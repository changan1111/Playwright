import fs from 'fs';
import path from 'path';

export default async () => {
  // Load test configuration
  const configPath = path.resolve(__dirname, 'testConfig.json');
  const testConfig = JSON.parse(fs.readFileSync(configPath, 'utf-8'));

  // Get the current client from environment variables
  const currentClient = process.env.CLIENT_NAME;
  const testsToRun = testConfig[currentClient] || [];

  // Write the tests to run into a temporary file
  const tempFilePath = path.resolve(__dirname, 'testsToRun.json');
  fs.writeFileSync(tempFilePath, JSON.stringify(testsToRun));
};
