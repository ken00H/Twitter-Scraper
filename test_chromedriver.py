#!/usr/bin/env python3
"""
Test script to verify ChromeDriver version compatibility fix
"""

from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
import time

def test_chromedriver_setup():
    """Test ChromeDriver setup with automatic version matching"""
    print("Testing ChromeDriver version compatibility...")
    
    try:
        # Use webdriver-manager to automatically download correct ChromeDriver
        service = Service(ChromeDriverManager().install())
        options = webdriver.ChromeOptions()
        options.add_argument('--headless')  # Run in headless mode for testing
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        
        driver = webdriver.Chrome(service=service, options=options)
        
        # Test basic functionality
        driver.get("https://www.google.com")
        print(f"✓ Successfully launched Chrome browser")
        print(f"✓ ChromeDriver version: {driver.capabilities['chrome']['chromedriverVersion']}")
        print(f"✓ Chrome browser version: {driver.capabilities['browserVersion']}")
        
        driver.quit()
        print("✓ ChromeDriver compatibility test passed!")
        return True
        
    except Exception as e:
        print(f"✗ ChromeDriver test failed: {e}")
        return False

if __name__ == "__main__":
    test_chromedriver_setup()
