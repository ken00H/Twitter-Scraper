# Twitter-Scraper

[![License: MIT](https://img.shields.io/badge/license-MIT-blue.svg)](#license)  
[![Python Version](https://img.shields.io/badge/python-3.8%2B-blue.svg)](#requirements)  
[![Build Status](https://img.shields.io/badge/build-passing-brightgreen.svg)](#) *(add CI badge if applicable)*

## Overview

**Twitter-Scraper** is a lightweight Python utility that fetches tweets from X (formerly Twitter) and saves them into a plain text (`.txt`) file. Ideal for quick data collection, offline analysis, or logging tweet history.

## Features

- Fetch tweets from a specified user or search query.
- Optionally detect and skip duplicate tweets using `duplicate_detector.py`.
- Tested setup for Chrome WebDriver (`test_chromedriver.py`).
- Minimal dependencies for simple integration.

## Table of Contents

- [Installation](#installation)  
- [Usage](#usage)  
  - [Command-Line Interface](#command-line-interface)  
  - [Programmatic Use](#programmatic-use)  
- [Configuration](#configuration)  
- [Development](#development)  
- [Contributing](#contributing)  
- [License](#license)

---

## Installation

### Prerequisites

- Python 3.8+  
- [ChromeDriver](https://chromedriver.chromium.org/) installed and in your PATH

```bash
git clone https://github.com/ken00H/Twitter-Scraper.git
cd Twitter-Scraper
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
