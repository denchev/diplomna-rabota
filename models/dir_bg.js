import { chromium } from 'playwright';

async function getArticlesFromMultiplePages() {
  const browser = await chromium.launch({ headless: true });
  const context = await browser.newContext({
    userAgent: 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
  });
  const page = await context.newPage();

  const allUrls = new Set();
  const maxPages = 5;

  try {
    const baseUrl = 'https://dir.bg/topic/predsrochni-izbori-2026';
    console.log(`Navigating to initial page: ${baseUrl}`);
    await page.goto(baseUrl, { waitUntil: 'networkidle' });

    for (let currentPage = 1; currentPage <= maxPages; currentPage++) {
      console.log(`\n[Page ${currentPage}] Scraping articles...`);

      // 1. Extract the article URLs
      const urls = await page.$$eval('.topic-theme-main-section .list-article > a', anchors => {
        return anchors
          .map(a => a.getAttribute('href'))
          .filter(href => href !== null);
      });

      // 2. Clean and save the URLs
      urls.forEach(link => {
        const absoluteUrl = link.startsWith('http') ? link : `https://dir.bg${link}`;
        allUrls.add(absoluteUrl);
      });
      console.log(`[Page ${currentPage}] Found ${urls.length} articles.`);

      // 3. Navigate to next page safely
      if (currentPage < maxPages) {
        console.log(`[Page ${currentPage}] Navigating to next page...`);

        // We set up the listener BEFORE clicking to capture the navigation event safely
        const navigationPromise = page.waitForNavigation({ waitUntil: 'load' });

        const clickSuccessful = await page.evaluate(() => {
          const paginationLinks = Array.from(document.querySelectorAll('.display-desktop .pagination a'));
          const activeIndex = paginationLinks.findIndex(el => el.classList.contains('active'));
          const nextPageElement = paginationLinks[activeIndex + 1];

          if (nextPageElement && !nextPageElement.classList.contains('disabled')) {
            nextPageElement.click();
            return true;
          }
          return false;
        });

        if (clickSuccessful) {
          // Wait for the URL change and document destruction/creation cycle to fully finish
          await navigationPromise;
          // Small extra safety buffer for JS rendering
          await page.waitForTimeout(1000); 
        } else {
          console.log('No more pages available or next button not found. Stopping.');
          break;
        }
      }
    }

    // Output all gathered results
    console.log('\n===================================');
    console.log(`Extraction Complete! Total Unique Articles Found: ${allUrls.size}`);
    console.log('===================================');
    Array.from(allUrls).forEach((url, index) => {
      console.log(`${index + 1}. ${url}`);
    });

  } catch (error) {
    console.error('An error occurred during execution:', error);
  } finally {
    await browser.close();
  }
}

getArticlesFromMultiplePages();