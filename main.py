from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
try:
    from bs4 import BeautifulSoup
except ImportError:
    print("Error: Missing required package 'beautifulsoup4'")
    print("Install it with: pip install beautifulsoup4")
    exit(1)
import time
from datetime import datetime
import random
import re
import hashlib
import signal
import sys
import os
import json
from urllib.parse import urlparse
import pickle
from pathlib import Path


def validate_url(url):
    """Validate if a string is a proper URL."""
    try:
        result = urlparse(url)
        return all([result.scheme, result.netloc])
    except:
        return False


class TwitterScraper:
    """Enhanced Twitter scraper with undetected-chromedriver and cookie-based login."""

    def __init__(self):
        self.driver = None
        self.wait = None
        self.cookies_file = "twitter_cookies.pkl"

    def setup_driver(self):
        """Configure Chrome WebDriver with anti-detection measures."""
        options = webdriver.ChromeOptions()

        # Anti-detection options
        options.add_argument("--no-first-run")
        options.add_argument("--no-service-autorun")
        options.add_argument("--password-store=basic")
        options.add_argument("--disable-blink-features=AutomationControlled")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--disable-extensions")
        options.add_argument("--disable-gpu")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-web-security")
        options.add_argument("--disable-features=VizDisplayCompositor")

        # User agent - use current Chrome version
        options.add_argument(
            'user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
            'AppleWebKit/537.36 (KHTML, like Gecko) Chrome/138.0.7204.157 Safari/537.36'
        )

        # Create driver with automatic version handling via webdriver-manager
        try:
            service = Service(ChromeDriverManager().install())
            self.driver = webdriver.Chrome(service=service, options=options)
            print("✓ ChromeDriver automatically matched to browser version")
        except Exception as e:
            print(f"ChromeDriver setup error: {e}")
            print("Attempting fallback...")
            # Fallback to basic setup
            service = Service()
            self.driver = webdriver.Chrome(service=service, options=options)

        self.wait = WebDriverWait(self.driver, 20)

    def save_cookies(self):
        """Save cookies and session data for persistent login."""
        try:
            cookies = self.driver.get_cookies()
            with open(self.cookies_file, 'wb') as f:
                pickle.dump(cookies, f)
            print("✓ Cookies saved successfully")
        except Exception as e:
            print(f"⚠ Error saving cookies: {e}")

    def load_cookies(self):
        """Load saved cookies for automatic login."""
        try:
            if os.path.exists(self.cookies_file):
                with open(self.cookies_file, 'rb') as f:
                    cookies = pickle.load(f)

                self.driver.get("https://x.com")
                time.sleep(2)

                for cookie in cookies:
                    try:
                        self.driver.add_cookie(cookie)
                    except Exception as e:
                        continue

                self.driver.refresh()
                time.sleep(3)

                # Check if logged in
                try:
                    self.wait.until(EC.presence_of_element_located(
                        (By.CSS_SELECTOR, '[data-testid="AppTabBar_Home_Link"]')
                    ))
                    print("✓ Automatically logged in using saved cookies")
                    return True
                except:
                    print("⚠ Saved cookies expired, manual login required")
                    return False
            return False
        except Exception as e:
            print(f"⚠ Error loading cookies: {e}")
            return False

    def wait_for_manual_login(self):
        """Wait for user to manually log in with enhanced error handling."""
        print("\n" + "=" * 60)
        print("LOGIN OPTIONS")
        print("1. Automatic login (if cookies saved)")
        print("2. Manual login")
        print("=" * 60 + "\n")

        # Try automatic login first
        if self.load_cookies():
            return

        # Manual login
        print("Manual login required - browser will open X.com login page")

        max_attempts = 5000
        for attempt in range(max_attempts):
            try:
                self.driver.get("https://x.com/i/flow/login")
                input("Press Enter AFTER you've successfully logged in...")

                # Verify login
                try:
                    self.wait.until(EC.presence_of_element_located(
                        (By.CSS_SELECTOR, '[data-testid="AppTabBar_Home_Link"]')
                    ))
                    print("✓ Login verified successfully")
                    self.save_cookies()
                    return
                except TimeoutException:
                    if attempt < max_attempts - 1:
                        print(f"⚠ Login verification failed, retrying... ({attempt + 1}/{max_attempts})")
                    else:
                        print("⚠ Could not verify login - continuing anyway")

            except Exception as e:
                print(f"⚠ Login error: {e}")
                if attempt < max_attempts - 1:
                    time.sleep(5)

    def handle_errors(self):
        """Handle common Twitter errors with recovery mechanisms."""
        try:
            # Check for "Something went wrong"
            error_elements = self.driver.find_elements(By.XPATH,
                "//span[contains(., 'Something went wrong') or contains(., 'Try again')]")

            if error_elements:
                print("⚠ Detected error message - attempting recovery...")

                # Try refresh
                self.driver.refresh()
                time.sleep(random.uniform(5, 8))

                # Check if error persists
                error_elements = self.driver.find_elements(By.XPATH,
                    "//span[contains(., 'Something went wrong')]")

                if error_elements:
                    # Try navigating back to home
                    self.driver.get("https://x.com/home")
                    time.sleep(random.uniform(3, 5))
                    return False

                return True

            # Check for rate limiting
            rate_limit = self.driver.find_elements(By.XPATH,
                "//span[contains(., 'Rate limit') or contains(., 'Too many requests')]")

            if rate_limit:
                print("⚠ Rate limit detected - waiting...")
                time.sleep(random.uniform(30, 60))
                return False

            return True

        except Exception as e:
            print(f"⚠ Error handling failed: {e}")
            return False

    def collect_loaded_tweets(self, seen_keys, start_date, username, end_date):
        """Collect tweets currently loaded on page with enhanced error handling."""
        collected = []
        try:
            tweet_elements = self.driver.find_elements(By.XPATH, "//article")
            print(f"Found {len(tweet_elements)} tweet elements on page")

            for el in tweet_elements:
                try:
                    html = el.get_attribute('outerHTML')
                    tweet = self.extract_tweet_data(html)
                    if not tweet:
                        continue

                    # Validation and deduplication
                    content_hash = hashlib.sha256(tweet['text'].strip().encode()).hexdigest()
                    timestamp_key = tweet['timestamp'][:10] if tweet['timestamp'] else 'unknown'
                    key = f"{timestamp_key}_{content_hash}"

                    if key not in seen_keys:
                        try:
                            if tweet['timestamp']:
                                tweet_date = datetime.strptime(tweet['timestamp'][:10], "%Y-%m-%d")
                                if tweet_date < start_date:
                                    continue
                        except:
                            pass

                        seen_keys.add(key)
                        collected.append(tweet)

                except Exception as e:
                    print(f"Error processing tweet element: {str(e)[:200]} - skipping")
                    continue

        except Exception as e:
            print(f"Error collecting tweets: {e}")

        print(f"Successfully processed {len(collected)} tweets")
        return collected

    def smart_scroll_and_collect(self, username, start_date, end_date, max_scrolls=10000, slow_mode=False):
        """Enhanced scrolling with error recovery and anti-detection."""
        seen_keys = set()
        all_tweets = []
        no_new_count = 0
        scroll_num = 0

        # Configure scroll parameters
        scroll_step = 400 if slow_mode else 600
        base_delay = (4.0, 6.0) if slow_mode else (2.0, 3.0)

        # Collect initial tweets
        initial_tweets = self.collect_loaded_tweets(seen_keys, start_date, username, end_date)
        if initial_tweets:
            all_tweets.extend(initial_tweets)

        while scroll_num < max_scrolls:
            try:
                # Check for errors before scrolling
                if not self.handle_errors():
                    continue

                # Human-like scrolling
                for _ in range(3):
                    self.driver.execute_script(f"window.scrollBy(0, {scroll_step})")
                    time.sleep(random.uniform(base_delay[0]/2, base_delay[1]/2))

                # Wait for content to load
                time.sleep(random.uniform(*base_delay))

                # Check if reached bottom
                current_height = self.driver.execute_script("return document.body.scrollHeight")
                time.sleep(1)
                new_height = self.driver.execute_script("return document.body.scrollHeight")

                if current_height == new_height:
                    # Double wait for dynamic content
                    time.sleep(random.uniform(base_delay[1], base_delay[1]*2))

                # Check for end markers
                end_markers = self.driver.find_elements(By.XPATH,
                    "//span[contains(., \"You're caught up\") or contains(., \"Nothing to see here\")]")
                if end_markers:
                    print("✓ Reached end of results")
                    break

                # Collect new tweets
                new_tweets = self.collect_loaded_tweets(seen_keys, start_date, username, end_date)
                if new_tweets:
                    all_tweets.extend(new_tweets)

                if not new_tweets:
                    no_new_count += 1
                else:
                    no_new_count = 0

                if no_new_count >= 5:
                    print("No new tweets for 5 consecutive scrolls - stopping")
                    break

                scroll_num += 1

            except Exception as e:
                print(f"Scroll error: {e} - retrying...")
                time.sleep(base_delay[1] * 2)
                continue

        return all_tweets

    def extract_tweet_data(self, html):
        """Enhanced tweet extraction with robust reply context handling."""
        try:
            soup = BeautifulSoup(html, 'html.parser')

            # 1. AUTHOR EXTRACTION
            author_name = ''
            author_handle = ''

            # Primary method: User-Name container
            user_div = soup.select_one('div[data-testid="User-Name"]')
            if user_div:
                # Name extraction
                name_span = user_div.select_one('span[dir="ltr"]')
                if name_span:
                    author_name = name_span.get_text(strip=True)
                    # Clean emoji artifacts
                    author_name = re.sub(r'[^\w\s\u0600-\u06FF]', '', author_name).strip()

                # Handle extraction
                handle_link = user_div.select_one('a[href^="/"]')
                if handle_link and handle_link.get('href'):
                    author_handle = handle_link['href'].strip('/')

            # Fallback method
            if not author_name or not author_handle:
                author_link = soup.select_one('a[role="link"][tabindex="-1"]')
                if author_link:
                    name_span = author_link.select_one('span[dir="ltr"]')
                    if name_span:
                        author_name = name_span.get_text(strip=True)
                    if author_link.get('href'):
                        author_handle = author_link['href'].strip('/')

            # 2. TIMESTAMP
            timestamp = ''
            time_tag = soup.find('time')
            if time_tag and time_tag.get('datetime'):
                timestamp = time_tag['datetime']

            # 3. MAIN CONTENT EXTRACTION
            text = ''
            text_div = soup.select_one('div[data-testid="tweetText"]')
            if text_div:
                text = text_div.get_text(" ", strip=True)

            # 4. REPLY CONTEXT HANDLING (FIXES URL ISSUE)
            reply_to = []
            reply_text = ""

            # Find the reply context container
            reply_context = None

            # Look for new X.com reply structure
            if not reply_context:
                reply_context = soup.select_one('div[data-testid="reply"]')

            # Look for "Replying to" text element (English and Arabic)
            if not reply_context:
                reply_text_element = soup.find(string=re.compile(r'Replying to|رداً على', re.IGNORECASE))
                if reply_text_element:
                    reply_context = reply_text_element.find_parent()

            # Process reply context if found
            if reply_context:
                # Extract mentioned users
                user_links = reply_context.find_all('a', href=re.compile(r'^/[^/]+$'))
                reply_to = [f"@{link['href'].strip('/')}" for link in user_links if link.get('href')]

                # Extract the actual reply text snippet
                next_element = reply_context.find_next_sibling()
                while next_element:
                    if next_element.get_text(strip=True):
                        reply_text = next_element.get_text(" ", strip=True)
                        break
                    next_element = next_element.find_next_sibling()

            # 5. HANDLE QUOTED TWEETS SEPARATELY
            quoted_block = soup.select_one('div[role="blockquote"]') or soup.select_one('div[data-testid="tweetQuote"]')
            if quoted_block:
                # Extract quoted author
                quoted_author = quoted_block.select_one('a[href^="/"]')
                if quoted_author and quoted_author.get('href'):
                    handle = quoted_author['href'].strip('/')
                    if handle and handle not in reply_to:
                        reply_to.append(f"@{handle}")

                # Extract quoted text
                quoted_text_div = quoted_block.select_one('div[data-testid="tweetText"]')
                if quoted_text_div:
                    reply_text = quoted_text_div.get_text(" ", strip=True)[:280]

            return {
                'author_name': author_name,
                'author_handle': author_handle,
                'timestamp': timestamp,
                'text': text,
                'reply_to': reply_to,
                'reply_text': reply_text
            } if text else None

        except Exception as e:
            print(f"Error parsing tweet: {e}")
            return None

    def save_tweets(self, tweets, username, start_date, end_date):
        """Save collected tweets with enhanced formatting including reply context."""
        if not tweets:
            return 0

        filename = f"tweets_{username}_{start_date.strftime('%Y%m%d')}_to_{end_date.strftime('%Y%m%d')}.txt"

        try:
            with open(filename, 'w', encoding='utf-8') as f:
                f.write(f"ENHANCED TWEETS WITH REPLY CONTEXT\n")
                f.write(f"Username: @{username}\n")
                f.write(f"Date Range: {start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}\n")
                f.write(f"Total Tweets: {len(tweets)}\n")
                f.write("=" * 80 + "\n\n")

                for i, tweet in enumerate(tweets, 1):
                    # Tweet header
                    f.write(f"TWEET {i}\n")

                    # Author and username
                    author_name = tweet.get('author_name', 'Unknown author')
                    author_handle = tweet.get('author_handle', username)
                    f.write(f"Author: {author_name} (@{author_handle})\n")

                    # Date
                    timestamp = tweet.get('timestamp', '')
                    if timestamp:
                        date_str = timestamp.split('T')[0]
                        f.write(f"Date: {date_str}\n")
                    else:
                        f.write("Date: Unknown\n")

                    # Reply context (username and text)
                    reply_to = tweet.get('reply_to', '')
                    if reply_to:
                        # Extract username from reply_to
                        usernames = re.findall(r'@(\w+)', str(reply_to))
                        if usernames:
                            f.write(f"Replying to: @{', @'.join(usernames)}\n")

                    # Reply text (the tweet inside the main tweet)
                    reply_text = tweet.get('reply_text', '')
                    if reply_text:
                        f.write(f"Reply Text: {reply_text}\n")

                    # Main tweet text
                    f.write("Main Tweet:\n")
                    main_text = tweet.get('text', '')

                    # Clean up the text to remove reply mentions at the beginning
                    if reply_to and main_text:
                        # Remove @username patterns from the beginning
                        cleaned_text = re.sub(r'^(@\w+\s*)+', '', main_text).strip()
                        f.write(f"{cleaned_text}\n")
                    else:
                        f.write(f"{main_text}\n")

                    # URLs if any
                    urls = tweet.get('urls', [])
                    if urls:
                        f.write("\nURLs:\n")
                        for url in urls:
                            f.write(f"- {url}\n")

                    # Separator
                    f.write("\n" + "=" * 80 + "\n\n")

            print(f"✓ Saved {len(tweets)} tweets to {filename}")
            return len(tweets)

        except Exception as e:
            print(f"Error saving tweets: {e}")
            return 0

    def scrape_tweets(self, username, start_date, end_date, max_scrolls=10000, slow_mode=False):
        """Main scraping function with all enhancements."""
        total_collected = 0

        try:
            self.setup_driver()

            # Login with cookie support
            self.wait_for_manual_login()

            # Navigate to search
            start_str = start_date.strftime("%Y-%m-%d")
            end_str = end_date.strftime("%Y-%m-%d")
            search_url = (
                f"https://x.com/search?q=from%3A{username}%20"
                f"since%3A{start_str}%20until%3A{end_str}"
                "&src=typed_query&f=live"
            )

            self.driver.get(search_url)

            # Wait for tweets to load
            try:
                self.wait.until(EC.presence_of_element_located((By.XPATH, "//article")))
                time.sleep(3)
            except TimeoutException:
                print("⚠ Timed out waiting for tweets to load")

            # Check if account is protected
            protected = self.driver.find_elements(By.XPATH,
                "//span[contains(., 'These posts are protected')]")
            if protected:
                print("✗ Account is protected. Cannot scrape tweets.")
                return 0

            # Collect tweets
            tweets = self.smart_scroll_and_collect(username, start_date, end_date, max_scrolls, slow_mode)

            # Save tweets
            if tweets:
                total_collected = self.save_tweets(tweets, username, start_date, end_date)
                print(f"\n✓ Total tweets collected and saved: {total_collected}")

            return total_collected

        except Exception as e:
            print(f"\nError during scraping: {e}")
            return total_collected
        finally:
            if self.driver:
                response = input("Press 'q' to quit browser, or any other key to keep it open: ").strip().lower()
                if response == 'q':
                    self.driver.quit()
                    print("Browser closed.")


def main():
    """Main execution function."""
    scraper = TwitterScraper()
#Enter the User Name You Want To Scrap Below
    username = "UserName"
    start_date = datetime(2024,1,1)
    end_date = datetime(2024,9,17)

    while True:
        start_time = time.time()
        total_tweets = scraper.scrape_tweets(username, start_date, end_date)
        elapsed = time.time() - start_time
        print(f"\nCompleted in {elapsed:.1f} seconds, total tweets: {total_tweets}")

        response = input("\nScraping completed. Press ENTER to exit, or type 'r' to restart: ").strip().lower()
        if response != 'r':
            break


if __name__ == "__main__":
    main()
