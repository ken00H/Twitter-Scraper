#!/usr/bin/env python3
"""
Enhanced Duplicate Tweet Detection System
Considers both tweet content and date for duplicate verification
"""

import re
import json
import hashlib
from datetime import datetime, timedelta
from typing import List, Dict, Tuple, Set
from difflib import SequenceMatcher
import argparse
import os


class Tweet:
    """Represents a parsed tweet with enhanced duplicate detection capabilities."""
    
    def __init__(self, date: str, content: str, reply_to: str = "", urls: List[str] = None):
        self.date = self._parse_date(date)
        self.original_content = content
        self.reply_to = self._extract_reply_to(content) if not reply_to else reply_to
        self.content = self._normalize_content(content)
        self.urls = urls or []
        self.signature = self._generate_signature()
        
    def _parse_date(self, date_str: str) -> datetime:
        """Parse date string to datetime object."""
        try:
            # Handle ISO format: 2024-01-31T10:46:43.000Z
            if 'T' in date_str and 'Z' in date_str:
                return datetime.fromisoformat(date_str.replace('Z', '+00:00'))
            # Handle simple date format: 2024-01-31
            elif len(date_str) == 10:
                return datetime.strptime(date_str, "%Y-%m-%d")
            else:
                return datetime.now()
        except:
            return datetime.now()
    
    def _extract_reply_to(self, content: str) -> str:
        """Extract @username mentions from tweet content for REPLY TO field."""
        if not content:
            return ""
        
        # Find @username patterns at the beginning of the content (most likely replies)
        match = re.match(r'^(@\w+(?:\s+@\w+)*)\s*', content.strip())
        if match:
            usernames = re.findall(r'@\w+', match.group(1))
            return ', '.join(usernames)
        
        # Check for @username patterns anywhere in the content
        usernames = re.findall(r'@\w+', content)
        if usernames:
            return ', '.join(set(usernames))  # Remove duplicates
        
        return ""

    def _normalize_content(self, content: str) -> str:
        """Normalize tweet content for better comparison."""
        if not content:
            return ""
        
        # Remove extra whitespace
        content = re.sub(r'\s+', ' ', content.strip())
        
        # Normalize Arabic characters
        arabic_norm_map = {
            'أ': 'ا', 'إ': 'ا', 'آ': 'ا',
            'ة': 'ه', 'ى': 'ي',
            'ئ': 'ي', 'ؤ': 'و'
        }
        
        for original, normalized in arabic_norm_map.items():
            content = content.replace(original, normalized)
        
        # Remove URLs for content comparison
        content = re.sub(r'https?://\S+', '', content)
        
        # Remove @username patterns from content for comparison (but keep them in reply_to)
        content = re.sub(r'@\w+', '', content)
        
        # Clean up extra spaces
        content = re.sub(r'\s+', ' ', content).strip()
        
        return content
    
    def _generate_signature(self) -> str:
        """Generate a unique signature for this tweet."""
        # Create a normalized signature for exact matching
        normalized = f"{self.date.strftime('%Y-%m-%d')}_{self.content}"
        return hashlib.md5(normalized.encode('utf-8')).hexdigest()
    
    def get_content_hash(self) -> str:
        """Get hash of normalized content only."""
        return hashlib.md5(self.content.encode('utf-8')).hexdigest()
    
    def __str__(self):
        return f"{self.date.strftime('%Y-%m-%d %H:%M')} - {self.content[:50]}..."


class DuplicateDetector:
    """Enhanced duplicate detection with fuzzy matching and date proximity."""
    
    def __init__(self, content_threshold: float = 0.85, date_window_hours: int = 24):
        self.content_threshold = content_threshold
        self.date_window = timedelta(hours=date_window_hours)
        self.tweets = []
        self.duplicate_groups = []
        
    def load_from_file(self, filename: str) -> List[Tweet]:
        """Load tweets from text file format."""
        tweets = []
        current_tweet = {}
        
        try:
            with open(filename, 'r', encoding='utf-8') as f:
                lines = f.readlines()
                
            for line in lines:
                line = line.strip()
                
                if line.startswith("Date:"):
                    if current_tweet and 'content' in current_tweet:
                        tweets.append(Tweet(
                            current_tweet.get('date', ''),
                            current_tweet.get('content', ''),
                            current_tweet.get('reply_to', ''),
                            current_tweet.get('urls', [])
                        ))
                    current_tweet = {'date': line[6:].strip()}
                    
                elif line.startswith("REPLY TO:"):
                    current_tweet['reply_to'] = line[10:].strip()
                    
                elif line == "CONTENT:":
                    # Collect content until next separator
                    content_lines = []
                    continue
                    
                elif line.startswith("URLS:"):
                    # Skip URLS section for now
                    continue
                    
                elif line.startswith("http") and 'urls' not in current_tweet:
                    if 'urls' not in current_tweet:
                        current_tweet['urls'] = []
                    current_tweet['urls'].append(line)
                    
                elif line.startswith("- http"):
                    if 'urls' not in current_tweet:
                        current_tweet['urls'] = []
                    current_tweet['urls'].append(line[2:])
                    
                elif line and '=' not in line and 'TWEET' not in line and 'Archive' not in line:
                    if 'content' not in current_tweet:
                        current_tweet['content'] = line
                    else:
                        current_tweet['content'] += ' ' + line
                        
            # Add last tweet
            if current_tweet and 'content' in current_tweet:
                tweets.append(Tweet(
                    current_tweet.get('date', ''),
                    current_tweet.get('content', ''),
                    current_tweet.get('reply_to', ''),
                    current_tweet.get('urls', [])
                ))
                
        except Exception as e:
            print(f"Error loading file {filename}: {e}")
            
        return tweets
    
    def calculate_content_similarity(self, text1: str, text2: str) -> float:
        """Calculate similarity between two text strings."""
        if not text1 or not text2:
            return 0.0
            
        # Use SequenceMatcher for fuzzy string matching
        similarity = SequenceMatcher(None, text1, text2).ratio()
        
        # Additional check for substring containment
        if text1 in text2 or text2 in text1:
            similarity = max(similarity, 0.9)
            
        return similarity
    
    def are_dates_close(self, date1: datetime, date2: datetime) -> bool:
        """Check if two dates are within the configured time window."""
        return abs(date1 - date2) <= self.date_window
    
    def find_duplicates(self, tweets: List[Tweet]) -> List[List[int]]:
        """Find duplicate tweet groups based on content and date."""
        n = len(tweets)
        duplicates = []
        processed = set()
        
        for i in range(n):
            if i in processed:
                continue
                
            group = [i]
            
            for j in range(i + 1, n):
                if j in processed:
                    continue
                    
                # Check if dates are close
                if not self.are_dates_close(tweets[i].date, tweets[j].date):
                    continue
                
                # Check content similarity
                similarity = self.calculate_content_similarity(
                    tweets[i].content, tweets[j].content
                )
                
                if similarity >= self.content_threshold:
                    group.append(j)
                    processed.add(j)
            
            if len(group) > 1:
                duplicates.append(group)
                processed.update(group)
                
        return duplicates
    
    def remove_duplicates(self, tweets: List[Tweet]) -> Tuple[List[Tweet], List[List[Tweet]]]:
        """Remove duplicates and return cleaned list with duplicate groups."""
        if not tweets:
            return [], []
            
        self.tweets = tweets
        duplicate_indices = self.find_duplicates(tweets)
        
        # Get actual tweet objects for duplicate groups
        duplicate_groups = [[tweets[i] for i in group] for group in duplicate_indices]
        
        # Keep first tweet from each group (earliest date)
        to_keep = set(range(len(tweets)))
        for group in duplicate_indices:
            # Keep the tweet with earliest date
            earliest_idx = min(group, key=lambda i: tweets[i].date)
            to_remove = set(group) - {earliest_idx}
            to_keep -= to_remove
        
        cleaned_tweets = [tweets[i] for i in sorted(to_keep)]
        
        return cleaned_tweets, duplicate_groups
    
    def generate_report(self, original_count: int, cleaned_tweets: List[Tweet], 
                       duplicate_groups: List[List[Tweet]], output_file: str = None):
        """Generate a detailed report of duplicate detection."""
        removed_count = original_count - len(cleaned_tweets)
        
        report = {
            'original_count': original_count,
            'cleaned_count': len(cleaned_tweets),
            'removed_count': removed_count,
            'duplicate_groups': len(duplicate_groups),
            'duplicate_details': []
        }
        
        for i, group in enumerate(duplicate_groups, 1):
            group_info = {
                'group_id': i,
                'duplicate_count': len(group),
                'kept_tweet': str(group[0]),
                'removed_tweets': [str(tweet) for tweet in group[1:]]
            }
            report['duplicate_details'].append(group_info)
        
        if output_file:
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(report, f, ensure_ascii=False, indent=2, default=str)
        
        return report
    
    def save_cleaned_tweets(self, tweets: List[Tweet], output_filename: str):
        """Save cleaned tweets to file in the same format."""
        try:
            with open(output_filename, 'w', encoding='utf-8') as f:
                f.write("CLEANED TWEETS - DUPLICATES REMOVED\n")
                f.write(f"Total tweets: {len(tweets)}\n")
                f.write("=" * 80 + "\n\n")
                
                for i, tweet in enumerate(tweets, 1):
                    f.write(f"TWEET {i}\n")
                    f.write(f"Date: {tweet.date.isoformat()}\n")
                    f.write(f"REPLY TO: {tweet.reply_to}\n")
                    f.write("CONTENT:\n")
                    f.write(f"{tweet.content}\n")
                    
                    if tweet.urls:
                        f.write("\nURLS:\n")
                        for url in tweet.urls:
                            f.write(f"- {url}\n")
                    
                    f.write("\n" + "=" * 80 + "\n\n")
                    
            print(f"Cleaned tweets saved to: {output_filename}")
            
        except Exception as e:
            print(f"Error saving cleaned tweets: {e}")


def main():
    """Main function for standalone duplicate detection."""
    parser = argparse.ArgumentParser(description='Detect and remove duplicate tweets')
    parser.add_argument('input_file', help='Input tweet file')
    parser.add_argument('--output', '-o', help='Output file for cleaned tweets')
    parser.add_argument('--report', '-r', help='Output file for duplicate report (JSON)')
    parser.add_argument('--threshold', '-t', type=float, default=0.85, 
                       help='Content similarity threshold (0.0-1.0)')
    parser.add_argument('--window', '-w', type=int, default=24,
                       help='Date window in hours for comparison')
    
    args = parser.parse_args()
    
    if not os.path.exists(args.input_file):
        print(f"Error: File {args.input_file} not found")
        return
    
    detector = DuplicateDetector(
        content_threshold=args.threshold,
        date_window_hours=args.window
    )
    
    print(f"Loading tweets from {args.input_file}...")
    tweets = detector.load_from_file(args.input_file)
    
    if not tweets:
        print("No tweets found in file")
        return
    
    print(f"Loaded {len(tweets)} tweets")
    print(f"Using similarity threshold: {args.threshold}")
    print(f"Date window: {args.window} hours")
    
    print("\nDetecting duplicates...")
    cleaned_tweets, duplicate_groups = detector.remove_duplicates(tweets)
    
    print(f"\nResults:")
    print(f"Original tweets: {len(tweets)}")
    print(f"Cleaned tweets: {len(cleaned_tweets)}")
    print(f"Removed duplicates: {len(tweets) - len(cleaned_tweets)}")
    print(f"Duplicate groups found: {len(duplicate_groups)}")
    
    if args.output:
        detector.save_cleaned_tweets(cleaned_tweets, args.output)
    
    if args.report:
        report = detector.generate_report(len(tweets), cleaned_tweets, duplicate_groups, args.report)
        print(f"\nDetailed report saved to: {args.report}")
    
    # Show sample duplicates
    if duplicate_groups:
        print("\nSample duplicate groups:")
        for i, group in enumerate(duplicate_groups[:3], 1):
            print(f"\nGroup {i} ({len(group)} duplicates):")
            print(f"  Kept: {group[0]}")
            if len(group) > 1:
                print(f"  Removed: {len(group)-1} similar tweets")


if __name__ == "__main__":
    main()
