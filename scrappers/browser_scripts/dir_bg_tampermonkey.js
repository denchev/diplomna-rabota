// ==UserScript==
// @name         dir.bg Comments Scraper
// @namespace    marush_denchev_comments_scraper
// @version      1.0
// @description  Polls a local Flask server for scraping tasks and executes
//               them on dir.bg category and comments pages. Sends results back
//               to Flask which writes them to CSV.
// @author       marush_denchev_comments_scraper
// @match        *://*.dir.bg/*
// @grant        GM_setValue
// @grant        GM_getValue
// @grant        GM_xmlhttpRequest
// @connect      127.0.0.1
// @run-at       document-idle
// ==/UserScript==

(function () {
    "use strict";

    // -----------------------------------------------------------------------
    // Configuration
    // -----------------------------------------------------------------------

    const FLASK_BASE_URL = "http://127.0.0.1:5000";
    const TASK_ENDPOINT = FLASK_BASE_URL + "/api/task";
    const COMPLETE_ENDPOINT = FLASK_BASE_URL + "/api/task/complete";

    // Time to wait (ms) before polling again when the server returns noop.
    const NOOP_POLL_INTERVAL_MS = 3000;

    // Time to wait (ms) after page load before starting to scrape, to allow
    // dynamic content to settle.
    const POST_LOAD_SETTLE_MS = 2500;

    // GM storage keys
    const KEY_PENDING_TASK = "dir_bg_pending_task";

    // -----------------------------------------------------------------------
    // Logging
    // -----------------------------------------------------------------------

    /**
     * Log a message to the browser console with a script prefix.
     *
     * @param {string} level - Log level label (INFO, DEBUG, ERROR, etc.).
     * @param {string} message - Message text.
     */
    function log(level, message) {
        console.log("[dir.bg-scraper][" + level + "] " + message);
    }

    // -----------------------------------------------------------------------
    // HTTP helpers (via GM_xmlhttpRequest to bypass CORS on localhost)
    // -----------------------------------------------------------------------

    /**
     * Perform a GET request via GM_xmlhttpRequest.
     *
     * @param {string} url - Target URL.
     * @returns {Promise<object>} Parsed JSON response body.
     */
    function gmGet(url) {
        return new Promise(function (resolve, reject) {
            GM_xmlhttpRequest({
                method: "GET",
                url: url,
                onload: function (response) {
                    try {
                        resolve(JSON.parse(response.responseText));
                    } catch (err) {
                        reject(new Error("JSON parse error on GET " + url + ": " + err));
                    }
                },
                onerror: function (err) {
                    reject(new Error("Network error on GET " + url));
                },
            });
        });
    }

    /**
     * Perform a POST request with a JSON body via GM_xmlhttpRequest.
     *
     * @param {string} url - Target URL.
     * @param {object} payload - Object to serialise as request body.
     * @returns {Promise<object>} Parsed JSON response body.
     */
    function gmPost(url, payload) {
        return new Promise(function (resolve, reject) {
            GM_xmlhttpRequest({
                method: "POST",
                url: url,
                headers: { "Content-Type": "application/json" },
                data: JSON.stringify(payload),
                onload: function (response) {
                    try {
                        resolve(JSON.parse(response.responseText));
                    } catch (err) {
                        reject(new Error("JSON parse error on POST " + url + ": " + err));
                    }
                },
                onerror: function (err) {
                    reject(new Error("Network error on POST " + url));
                },
            });
        });
    }

    // -----------------------------------------------------------------------
    // Utility helpers
    // -----------------------------------------------------------------------

    /**
     * Return trimmed text content of an element, or a fallback value.
     *
     * @param {Element|null} element - DOM element (may be null).
     * @param {string} fallback - Value to return when element is absent.
     * @returns {string} Cleaned text content or fallback.
     */
    function safeText(element, fallback) {
        if (!element) {
            return fallback || "";
        }
        return (element.innerText || element.textContent || "").trim();
    }

    /**
     * Derive the comments page URL from an article URL.
     *
     * Pattern:
     *   https://{subdomain}.dir.bg/{category}/{slug}
     *   → https://{subdomain}.dir.bg/comments/{slug}
     *
     * @param {string} articleUrl - Full article URL.
     * @returns {string} Derived comments page URL.
     */
    function deriveCommentsUrl(articleUrl) {
        try {
            const parsed = new URL(articleUrl);
            const parts = parsed.pathname.split("/").filter(Boolean);
            // Replace the category segment (index 0) with "comments".
            parts[0] = "comments";
            parsed.pathname = "/" + parts.join("/");
            return parsed.toString();
        } catch (_err) {
            return "";
        }
    }

    /**
     * Clean a raw username string extracted from the DOM.
     *
     * Strips the trailing " (нерегистриран)" suffix and normalises whitespace.
     *
     * @param {string} rawUsername - Raw text from h3.username.
     * @returns {string} Cleaned username.
     */
    function cleanUsername(rawUsername) {
        return rawUsername
            .replace(/\s*\(нерегистриран\)\s*/g, "")
            .trim();
    }

    /**
     * Parse a vote count string to an integer string.
     *
     * @param {string} raw - Raw vote text (may include leading +/-).
     * @returns {string} Non-negative integer string.
     */
    function parseVote(raw) {
        const match = (raw || "").match(/\d+/);
        return match ? match[0] : "0";
    }

    // -----------------------------------------------------------------------
    // Category page scraping
    // -----------------------------------------------------------------------

    /**
     * Extract all articles from the current category / topic page.
     *
     * Selects only the desktop list-article blocks to avoid duplicates from
     * the mobile rendering that coexists in the same DOM.
     *
     * @returns {Array<object>} Array of article metadata objects.
     */
    function scrapeCurrentCategoryPage() {
        const articles = [];

        // Target only the desktop section to avoid mobile duplicate blocks.
        const container = document.querySelector(
            ".section.topic-theme-main-section .display-desktop, " +
            ".main-section .display-desktop"
        );

        const blocks = (container || document).querySelectorAll(
            "div.text-news.list-article"
        );

        blocks.forEach(function (block) {
            const linkEl = block.querySelector("a.img-wrapper");
            const titleEl = block.querySelector(
                "div.text-wrapper h3.title a, div.text-wrapper h2.title a"
            );
            const dateEl = block.querySelector(
                "div.additional-info span.timestamp"
            );
            const viewsEl = block.querySelector(
                "div.additional-info span.views span"
            );

            const articleUrl = (linkEl && linkEl.href) ? linkEl.href.trim() : "";
            const articleTitle = safeText(titleEl);
            const articleDate = safeText(dateEl);
            const articleViews = safeText(viewsEl);

            if (!articleUrl) {
                return;
            }

            const commentsUrl = deriveCommentsUrl(articleUrl);

            if (!commentsUrl) {
                return;
            }

            articles.push({
                article_url: articleUrl,
                article_title: articleTitle,
                article_date: articleDate,
                article_views: articleViews,
                comments_url: commentsUrl,
            });
        });

        return articles;
    }

    /**
     * Extract the next-page URL from the current category page pagination.
     *
     * @returns {string|null} Next-page URL or null if this is the last page.
     */
    function getNextCategoryPageUrl() {
        // Desktop pagination — prefer the desktop block.
        const nextEl = document.querySelector(
            ".display-desktop ul.pagination li.next-page a, " +
            "ul.pagination li.next-page a"
        );
        return (nextEl && nextEl.href) ? nextEl.href.trim() : null;
    }

    // -----------------------------------------------------------------------
    // Comments page scraping
    // -----------------------------------------------------------------------

    /**
     * Recursively extract all comments from a root DOM element as a flat list.
     *
     * Handles arbitrarily deep reply trees by processing direct child
     * div.comment-block elements at each level.
     *
     * @param {Element} rootElement - DOM element to search within.
     * @returns {Array<object>} Flat array of parsed comment objects.
     */
    function extractCommentsFlat(rootElement) {
        const results = [];

        // Select only direct children to avoid double-counting nested replies.
        const directBlocks = Array.from(
            rootElement.querySelectorAll(":scope > div.comment-block")
        );

        directBlocks.forEach(function (block) {
            // Comment ID from span.comment-id[id].
            const idSpan = block.querySelector(
                ":scope > span.comment-id"
            );
            const commentId = idSpan ? idSpan.id.trim() : "";

            // Timestamp from user-info.
            const timestampEl = block.querySelector(
                ".user-info .timestamp"
            );
            const timestamp = safeText(timestampEl);

            // Username — may be plain text or wrapped in <a> for registered users.
            const usernameEl = block.querySelector("h3.username");
            const rawUsername = safeText(usernameEl);
            const username = cleanUsername(rawUsername);
            const isRegistered = !!(usernameEl && usernameEl.querySelector("a"));

            // Vote counts from the heading actions of THIS block only.
            const voteUpEl = block.querySelector(
                ":scope > div.comment-heading .vote_up"
            );
            const voteDownEl = block.querySelector(
                ":scope > div.comment-heading .vote_down"
            );
            const voteUp = parseVote(safeText(voteUpEl));
            const voteDown = parseVote(safeText(voteDownEl));

            // Comment text — innerText strips HTML tags including <i> censors.
            const textEl = block.querySelector(":scope > div.comment p");
            const commentText = safeText(textEl);

            // Only record comments that have both an ID and text.
            if (commentId && commentText) {
                results.push({
                    comment_id: commentId,
                    timestamp: timestamp,
                    username: username,
                    is_registered: isRegistered,
                    vote_up: voteUp,
                    vote_down: voteDown,
                    comment_text: commentText,
                });
            }

            // Recurse into this block to pick up nested replies.
            const nested = extractCommentsFlat(block);
            nested.forEach(function (c) {
                results.push(c);
            });
        });

        return results;
    }

    /**
     * Scrape all comments from the current comments page.
     *
     * @returns {object} Object with `comments` array and `nextPageUrl`.
     */
    function scrapeCurrentCommentsPage() {
        // The comments page has two div.comments-wrapper elements:
        // the first holds only the "Коментирай" button, the second holds
        // the actual comment blocks. Find the one with direct comment children.
        let wrapper = null;

        const allWrappers = document.querySelectorAll("div.comments-wrapper");

        allWrappers.forEach(function (w) {
            if (!wrapper && w.querySelector(":scope > div.comment-block")) {
                wrapper = w;
            }
        });

        // Fallback to the main section or body if no wrapper matched.
        if (!wrapper) {
            wrapper = (
                document.querySelector(".main-comments-section .main-section") ||
                document.body
            );
        }

        const comments = extractCommentsFlat(wrapper);

        // Pagination — next page link.
        const nextEl = document.querySelector(
            "ul.pagination li.next-page a"
        );
        const nextPageUrl = (nextEl && nextEl.href) ? nextEl.href.trim() : null;

        return {
            comments: comments,
            next_page_url: nextPageUrl || null,
        };
    }

    // -----------------------------------------------------------------------
    // Task execution
    // -----------------------------------------------------------------------

    /**
     * Execute a scrape_category task on the current page.
     *
     * Extracts articles and pagination, then POSTs results to Flask.
     *
     * @param {object} task - Task object received from Flask.
     * @returns {Promise<void>}
     */
    async function executeCategoryTask(task) {
        log("INFO", "Executing scrape_category | url=" + task.url);

        const articles = scrapeCurrentCategoryPage();
        const nextPageUrl = getNextCategoryPageUrl();

        log(
            "INFO",
            "Category scraped | articles=" + articles.length +
            " | next_page=" + (nextPageUrl || "none")
        );

        try {
            await gmPost(COMPLETE_ENDPOINT, {
                task: "scrape_category",
                source_url: window.location.href,
                next_page_url: nextPageUrl || null,
                articles: articles,
            });
            log("INFO", "Category result posted successfully");
        } catch (err) {
            log("ERROR", "Failed to post category result: " + err.message);
        }
    }

    /**
     * Execute a scrape_comments task on the current page.
     *
     * Extracts all flat comments and pagination, then POSTs results to Flask.
     *
     * @param {object} task - Task object received from Flask.
     * @returns {Promise<void>}
     */
    async function executeCommentsTask(task) {
        log("INFO", "Executing scrape_comments | url=" + task.comments_url);

        const result = scrapeCurrentCommentsPage();

        log(
            "INFO",
            "Comments scraped | count=" + result.comments.length +
            " | next_page=" + (result.next_page_url || "none")
        );

        try {
            await gmPost(COMPLETE_ENDPOINT, {
                task: "scrape_comments",
                source_url: window.location.href,
                article_url: task.article_url || "",
                article_title: task.article_title || "",
                article_date: task.article_date || "",
                article_views: task.article_views || "",
                category_url: task.category_url || "",
                next_page_url: result.next_page_url,
                comments: result.comments,
            });
            log("INFO", "Comments result posted successfully");
        } catch (err) {
            log("ERROR", "Failed to post comments result: " + err.message);
        }
    }

    // -----------------------------------------------------------------------
    // Navigation
    // -----------------------------------------------------------------------

    /**
     * Navigate the current tab to a given URL if not already there.
     *
     * @param {string} targetUrl - URL to navigate to.
     */
    function navigateTo(targetUrl) {
        // Normalise only trailing slashes — preserve query params for pagination.
        const current = window.location.href.replace(/\/$/, "");
        const target  = targetUrl.replace(/\/$/, "");

        if (current === target) {
            log("DEBUG", "Already on target URL — no navigation needed");
            return;
        }

        log("INFO", "Navigating to | url=" + targetUrl);
        window.location.href = targetUrl;
    }

    /**
     * Determine whether the browser is currently on the expected task URL.
     *
     * @param {object} task - Pending task object.
     * @returns {boolean} True if the current page matches the task URL.
     */
    function isOnTaskUrl(task) {
        // Compare full URLs including query params — required for pagination.
        const current = window.location.href.replace(/\/$/, "");

        let taskUrl = "";

        if (task.task === "scrape_category") {
            taskUrl = (task.url || "").replace(/\/$/, "");
        } else if (task.task === "scrape_comments") {
            taskUrl = (task.comments_url || "").replace(/\/$/, "");
        }

        return current === taskUrl;
    }

    // -----------------------------------------------------------------------
    // Main loop
    // -----------------------------------------------------------------------

    /**
     * Main entry point — runs once after page load with a settle delay.
     *
     * Checks whether there is a stored pending task that matches the current
     * page. If so, executes it. Otherwise polls Flask for the next task.
     *
     * @returns {Promise<void>}
     */
    async function main() {
        log("INFO", "Script started | url=" + window.location.href);

        // Retrieve any task that was stored before the last page navigation.
        let pendingTaskJson = GM_getValue(KEY_PENDING_TASK, null);
        let pendingTask = null;

        if (pendingTaskJson) {
            try {
                pendingTask = JSON.parse(pendingTaskJson);
            } catch (_err) {
                log("ERROR", "Failed to parse stored pending task — clearing");
                GM_setValue(KEY_PENDING_TASK, null);
                pendingTask = null;
            }
        }

        // If we have a pending task and we are on its URL, execute it.
        if (pendingTask && isOnTaskUrl(pendingTask)) {
            log(
                "INFO",
                "Resuming pending task | type=" + pendingTask.task
            );
            GM_setValue(KEY_PENDING_TASK, null);

            if (pendingTask.task === "scrape_category") {
                await executeCategoryTask(pendingTask);
            } else if (pendingTask.task === "scrape_comments") {
                await executeCommentsTask(pendingTask);
            }

            // After executing, immediately poll for the next task.
            await pollAndDispatch();
            return;
        }

        // If we have a pending task but are NOT on its URL the target page
        // likely redirected (e.g. a /comments/{slug} URL that redirects to the
        // article when there are no comments). Attempting to navigate again
        // would create an infinite redirect loop. Instead: skip the task, report
        // 0 results to Flask so it moves on, then poll for the next task.
        if (pendingTask) {
            const expectedUrl = (pendingTask.task === "scrape_category")
                ? pendingTask.url
                : pendingTask.comments_url;

            log(
                "WARN",
                "Pending task target not reached — likely redirected. " +
                "Skipping | expected=" + expectedUrl +
                " | actual=" + window.location.href
            );

            GM_setValue(KEY_PENDING_TASK, null);

            try {
                if (pendingTask.task === "scrape_comments") {
                    await gmPost(COMPLETE_ENDPOINT, {
                        task: "scrape_comments",
                        source_url: expectedUrl,
                        article_url: pendingTask.article_url || "",
                        article_title: pendingTask.article_title || "",
                        article_date: pendingTask.article_date || "",
                        article_views: pendingTask.article_views || "",
                        category_url: pendingTask.category_url || "",
                        next_page_url: null,
                        comments: [],
                    });
                } else if (pendingTask.task === "scrape_category") {
                    await gmPost(COMPLETE_ENDPOINT, {
                        task: "scrape_category",
                        source_url: expectedUrl,
                        next_page_url: null,
                        articles: [],
                    });
                }
                log("INFO", "Skipped task reported to Flask");
            } catch (err) {
                log("ERROR", "Failed to report skipped task: " + err.message);
            }

            await pollAndDispatch();
            return;
        }

        // No stored task — poll Flask for the next one.
        await pollAndDispatch();
    }

    /**
     * Poll Flask for the next task and dispatch it (navigate or execute).
     *
     * Retries with a delay on noop responses.
     *
     * @returns {Promise<void>}
     */
    async function pollAndDispatch() {
        let task = null;

        try {
            task = await gmGet(TASK_ENDPOINT);
        } catch (err) {
            log("ERROR", "Failed to poll for task: " + err.message);
            return;
        }

        log("DEBUG", "Received task | type=" + task.task);

        if (task.task === "noop") {
            log(
                "INFO",
                "No tasks pending — retrying in " +
                (NOOP_POLL_INTERVAL_MS / 1000) + "s"
            );
            setTimeout(pollAndDispatch, NOOP_POLL_INTERVAL_MS);
            return;
        }

        if (task.task !== "scrape_category" && task.task !== "scrape_comments") {
            log("ERROR", "Unknown task type received: " + task.task);
            return;
        }

        const targetUrl = (task.task === "scrape_category")
            ? task.url
            : task.comments_url;

        // Compare full URLs including query params — required for pagination.
        const current = window.location.href.replace(/\/$/, "");
        const target  = (targetUrl || "").replace(/\/$/, "");

        if (current === target) {
            // Already on target — execute immediately without navigating.
            GM_setValue(KEY_PENDING_TASK, null);

            if (task.task === "scrape_category") {
                await executeCategoryTask(task);
            } else {
                await executeCommentsTask(task);
            }

            await pollAndDispatch();

        } else {
            // Store the task and navigate. Script will resume on next load.
            GM_setValue(KEY_PENDING_TASK, JSON.stringify(task));
            navigateTo(targetUrl);
        }
    }

    // -----------------------------------------------------------------------
    // Bootstrap
    // -----------------------------------------------------------------------

    // Wait for the page content to settle before starting.
    setTimeout(main, POST_LOAD_SETTLE_MS);

})();
