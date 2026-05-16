#!/usr/bin/env python3
"""
Log analyzer for Google Form Bot submissions
Helps analyze and visualize submission results
"""

import re
from pathlib import Path
from collections import defaultdict
from datetime import datetime


def analyze_log(log_file: str = 'log.txt') -> dict:
    """Analyze log file and extract statistics"""
    log_path = Path(log_file)
    
    if not log_path.exists():
        print(f"No log file found: {log_file}")
        return {}
    
    with open(log_path, 'r') as f:
        lines = f.readlines()
    
    stats = {
        'total_submissions': 0,
        'successful': 0,
        'failed': 0,
        'retries': 0,
        'errors': defaultdict(int),
        'timestamps': [],
        'durations': []
    }
    
    submission_start = None
    submission_num = 0
    
    for line in lines:
        # Count successful submissions
        if '✓ Submission successful' in line:
            stats['successful'] += 1
            submission_num += 1
        
        # Count failed submissions
        elif '✗' in line and ('Failed' in line or 'error' in line.lower()):
            stats['failed'] += 1
        
        # Count retries
        elif 'Retrying' in line:
            stats['retries'] += 1
        
        # Extract errors
        error_match = re.search(r'Error:|error:', line)
        if error_match:
            error_type = line.split('Error:' if 'Error:' in line else 'error:')[1].strip()
            if error_type:
                stats['errors'][error_type[:50]] += 1
        
        # Extract timestamp
        timestamp_match = re.match(r'(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})', line)
        if timestamp_match:
            stats['timestamps'].append(timestamp_match.group(1))
        
        # Count total submissions
        if '--- Submission' in line:
            submission_start = datetime.now()
    
    stats['total_submissions'] = stats['successful'] + stats['failed']
    
    return stats


def print_report(stats: dict):
    """Print formatted report"""
    print("\n" + "="*60)
    print("SUBMISSION REPORT")
    print("="*60)
    
    if not stats or stats['total_submissions'] == 0:
        print("No submissions found in log file")
        print("="*60 + "\n")
        return
    
    total = stats['total_submissions']
    successful = stats['successful']
    failed = stats['failed']
    success_rate = (successful / total * 100) if total > 0 else 0
    
    print(f"\nTotal Submissions: {total}")
    print(f"  ✓ Successful: {successful}")
    print(f"  ✗ Failed: {failed}")
    print(f"  → Success Rate: {success_rate:.1f}%")
    
    if stats['retries'] > 0:
        print(f"\nRetries: {stats['retries']}")
    
    if stats['errors']:
        print(f"\nErrors Encountered:")
        for error_msg, count in sorted(stats['errors'].items(), key=lambda x: x[1], reverse=True):
            print(f"  • {error_msg}: {count}x")
    
    if stats['timestamps']:
        print(f"\nFirst submission: {stats['timestamps'][0]}")
        print(f"Last submission: {stats['timestamps'][-1]}")
    
    print("\n" + "="*60 + "\n")


def tail_log(log_file: str = 'log.txt', lines: int = 20):
    """Show last N lines of log file"""
    log_path = Path(log_file)
    
    if not log_path.exists():
        print(f"No log file found: {log_file}")
        return
    
    with open(log_path, 'r') as f:
        all_lines = f.readlines()
    
    print(f"\nLast {lines} lines of {log_file}:")
    print("="*60)
    
    for line in all_lines[-lines:]:
        print(line.rstrip())
    
    print("="*60 + "\n")


def main():
    """Main entry point"""
    import sys
    
    print("\nGoogle Form Bot - Log Analyzer")
    print("="*60)
    
    cmd = sys.argv[1] if len(sys.argv) > 1 else 'report'
    
    if cmd == 'report':
        stats = analyze_log()
        print_report(stats)
    
    elif cmd == 'tail':
        lines = int(sys.argv[2]) if len(sys.argv) > 2 else 20
        tail_log(lines=lines)
    
    elif cmd == 'analyze':
        stats = analyze_log()
        print_report(stats)
        tail_log()
    
    elif cmd == 'help':
        print("\nUsage: python log_analyzer.py [command]\n")
        print("Commands:")
        print("  report  - Show submission statistics (default)")
        print("  tail    - Show last 20 lines")
        print("  analyze - Show full report + last lines")
        print("  help    - Show this help message\n")
    
    else:
        print(f"Unknown command: {cmd}")
        print("Use 'python log_analyzer.py help' for usage\n")


if __name__ == '__main__':
    main()
