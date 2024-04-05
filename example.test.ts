import { chromium, Browser, BrowserContext, Page, test } from 'playwright/test';

let browser: Browser;
let context: BrowserContext;
let page: Page;

test.beforeAll(async () => {
    browser = await chromium.launch();
    context = await browser.newContext();

    // Create a new page in the context
    page = await context.newPage();

    // Perform login once
    await page.goto('https://www.demoblaze.com/');
    await page.locator("id=login2").click();
    await page.locator("id=loginusername").fill("username");
    await page.locator("id=loginpassword").fill("password");
    await page.locator("//*[@class='btn btn-primary' and text()='Log in']").click();
    await page.locator("id=nameofuser").waitFor();
});

test.afterAll(async () => {
    await browser.close();
});
test('Test Case 1', async () => {
  // Use the same context and page for Test Case 2
  //await page.goto('https://example.com/testcase2');
  await page.locator("//*[text()='Cart']").click();
  await page.waitForTimeout(10000);
  // Perform actions specific to Test Case 2
});

test('Test Case 2', async () => {
    // Use the same context and page for Test Case 1
    //await page.goto('https://example.com/testcase1');
    // Perform actions specific to Test Case 1

    await page.locator("//*[text()='Contact']").click();
    await page.locator("id=recipient-email").fill("test@fisglobal.com");
    await page.locator("id=recipient-name").fill("it is me");
    await page.locator("id=message-text").fill("enquiry");
    await page.locator("//*[text()='Send message']").click();
    await page.waitForTimeout(10000);

});

test('Test Case 3', async () => {
  // Use the same context and page for Test Case 1
  //await page.goto('https://example.com/testcase1');
  // Perform actions specific to Test Case 1

  await page.locator("//*[text()='Home ']").click();
  await page.waitForTimeout(2000);
  await page.getByRole('link', { name: 'Samsung galaxy s6' }).waitFor();
  await page.getByRole('link', { name: 'Samsung galaxy s6' }).click();
  await page.getByRole('link', { name: 'Add to cart' }).click();
  page.once('dialog', dialog => {
    console.log(`Dialog message: ${dialog.message()}`);
    dialog.dismiss().catch(() => {});
  });
  await page.getByRole('link', { name: 'Cart', exact: true }).click();
  await page.waitForTimeout(10000);
});

test('Test Case 4', async () => {
  // Use the same context and page for Test Case 1
  //await page.goto('https://example.com/testcase1');
  // Perform actions specific to Test Case 1
  await page.locator("//*[text()='Cart']").click();
  await page.getByRole('link', { name: 'Delete' }).first().click();
  await page.waitForTimeout(10000);
});


// Repeat for other test cases...
