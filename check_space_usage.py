#!/usr/bin/env python3
"""
Nagios Plugin for Disk Space Usage Analysis
Identifies directories consuming the most disk space while respecting mount points.

This plugin scans the filesystem and reports the top directories by size,
ensuring that mounted filesystems are not counted towards their parent directories.

Dependencies:
- psutil (for mount point detection)

Copyright (C) 2024 - GPLv3 License
"""

import argparse
import os
import sys
import subprocess
from pathlib import Path
from typing import List, Dict, Tuple, Set
from dataclasses import dataclass

try:
    import psutil
except ImportError:
    print("UNKNOWN - psutil module not installed. Install with: pip install psutil")
    sys.exit(3)

# Nagios exit codes
NAGIOS_OK = 0
NAGIOS_WARNING = 1
NAGIOS_CRITICAL = 2
NAGIOS_UNKNOWN = 3


@dataclass
class DirectorySize:
    """Represents a directory and its size"""
    path: str
    size_bytes: int
    size_human: str
    is_mountpoint: bool = False


class SpaceUsageChecker:
    """Analyzes disk space usage by directory"""
    
    def __init__(self, path: str, depth: int = 2, top_n: int = 10, 
                 exclude_paths: List[str] = None, verbose: bool = False):
        self.path = Path(path).resolve()
        self.depth = depth
        self.top_n = top_n
        self.exclude_paths = exclude_paths or []
        self.verbose = verbose
        self.mountpoints = self._get_mountpoints()
        
        if self.verbose:
            print(f"DEBUG: Analyzing path: {self.path}")
            print(f"DEBUG: Mount points detected: {len(self.mountpoints)}")
            for mp in sorted(self.mountpoints):
                print(f"DEBUG:   - {mp}")
    
    def _get_mountpoints(self) -> Set[str]:
        """Get all mount points on the system"""
        mountpoints = set()
        
        try:
            # Use psutil to get mount points
            partitions = psutil.disk_partitions(all=True)
            for partition in partitions:
                mountpoints.add(str(Path(partition.mountpoint).resolve()))
                
        except Exception as e:
            if self.verbose:
                print(f"DEBUG: Error getting mount points: {e}")
        
        return mountpoints
    
    def _is_mountpoint(self, path: Path) -> bool:
        """Check if a path is a mount point"""
        resolved = str(path.resolve())
        return resolved in self.mountpoints
    
    def _should_exclude(self, path: Path) -> bool:
        """Check if a path should be excluded from analysis"""
        path_str = str(path)
        
        # Check explicit exclusions
        for exclude in self.exclude_paths:
            if path_str.startswith(exclude):
                return True
        
        # Always exclude these system directories
        system_excludes = [
            '/proc', '/sys', '/dev', '/run', '/tmp',
            '/sys/firmware/efi/efivars'
        ]
        
        for exclude in system_excludes:
            if path_str.startswith(exclude):
                return True
        
        return False
    
    def _get_directory_size_du(self, path: Path) -> int:
        """Get directory size using du command (respects mount points)"""
        try:
            # Use du with --one-file-system to respect mount points
            result = subprocess.run(
                ['du', '-sb', '--one-file-system', str(path)],
                capture_output=True,
                text=True,
                timeout=300  # 5 minute timeout
            )
            
            if result.returncode == 0:
                # Parse output: "size\tpath"
                size_str = result.stdout.split()[0]
                return int(size_str)
            else:
                if self.verbose:
                    print(f"DEBUG: du failed for {path}: {result.stderr}")
                return 0
                
        except subprocess.TimeoutExpired:
            if self.verbose:
                print(f"DEBUG: Timeout calculating size for {path}")
            return 0
        except Exception as e:
            if self.verbose:
                print(f"DEBUG: Error calculating size for {path}: {e}")
            return 0
    
    def _format_size(self, size_bytes: int) -> str:
        """Format bytes to human readable format"""
        for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
            if size_bytes < 1024.0:
                return f"{size_bytes:.1f}{unit}"
            size_bytes /= 1024.0
        return f"{size_bytes:.1f}PB"
    
    def _analyze_directory(self, path: Path, current_depth: int = 0) -> List[DirectorySize]:
        """Recursively analyze directory sizes"""
        results = []
        
        if current_depth > self.depth:
            return results
        
        try:
            # Get immediate subdirectories
            subdirs = [d for d in path.iterdir() if d.is_dir()]
            
            for subdir in subdirs:
                # Skip excluded paths
                if self._should_exclude(subdir):
                    if self.verbose:
                        print(f"DEBUG: Skipping excluded: {subdir}")
                    continue
                
                # Check if it's a mount point
                is_mount = self._is_mountpoint(subdir)
                
                if is_mount:
                    # For mount points, get the filesystem size instead of directory size
                    if self.verbose:
                        print(f"DEBUG: {subdir} is a mount point, getting filesystem usage")
                    
                    try:
                        stat = psutil.disk_usage(str(subdir))
                        size_bytes = stat.used
                    except Exception as e:
                        if self.verbose:
                            print(f"DEBUG: Error getting mount stats for {subdir}: {e}")
                        size_bytes = 0
                else:
                    # For regular directories, use du to get size (respecting nested mounts)
                    if self.verbose:
                        print(f"DEBUG: Calculating size for {subdir} (depth {current_depth})")
                    size_bytes = self._get_directory_size_du(subdir)
                
                if size_bytes > 0:
                    results.append(DirectorySize(
                        path=str(subdir),
                        size_bytes=size_bytes,
                        size_human=self._format_size(size_bytes),
                        is_mountpoint=is_mount
                    ))
                
                # Recurse into subdirectories if not a mount point and not at max depth
                if not is_mount and current_depth < self.depth:
                    results.extend(self._analyze_directory(subdir, current_depth + 1))
                    
        except PermissionError:
            if self.verbose:
                print(f"DEBUG: Permission denied: {path}")
        except Exception as e:
            if self.verbose:
                print(f"DEBUG: Error analyzing {path}: {e}")
        
        return results
    
    def analyze(self) -> List[DirectorySize]:
        """Perform the space usage analysis"""
        if not self.path.exists():
            raise ValueError(f"Path does not exist: {self.path}")
        
        if not self.path.is_dir():
            raise ValueError(f"Path is not a directory: {self.path}")
        
        if self.verbose:
            print(f"DEBUG: Starting analysis at depth {self.depth}")
        
        # Analyze the directory tree
        results = self._analyze_directory(self.path, current_depth=0)
        
        # Sort by size (descending) and return top N
        results.sort(key=lambda x: x.size_bytes, reverse=True)
        
        if self.verbose:
            print(f"DEBUG: Found {len(results)} directories, returning top {self.top_n}")
        
        return results[:self.top_n]


def check_space_usage(args) -> Tuple[int, str]:
    """Check disk space usage and return Nagios result"""
    try:
        checker = SpaceUsageChecker(
            path=args.path,
            depth=args.depth,
            top_n=args.top,
            exclude_paths=args.exclude,
            verbose=args.verbose
        )
        
        results = checker.analyze()
        
        if not results:
            return NAGIOS_UNKNOWN, "UNKNOWN - No directories found or analysis failed"
        
        # Build output message
        total_analyzed = sum(r.size_bytes for r in results)
        total_formatted = checker._format_size(total_analyzed)
        
        # Get filesystem info for the target path
        try:
            disk_usage = psutil.disk_usage(args.path)
            fs_total = checker._format_size(disk_usage.total)
            fs_used = checker._format_size(disk_usage.used)
            fs_percent = disk_usage.percent
        except Exception:
            fs_total = "unknown"
            fs_used = "unknown"
            fs_percent = 0
        
        # Determine status based on thresholds
        exit_code = NAGIOS_OK
        status_prefix = "OK"
        
        if args.warning and fs_percent >= args.warning:
            exit_code = NAGIOS_WARNING
            status_prefix = "WARNING"
        
        if args.critical and fs_percent >= args.critical:
            exit_code = NAGIOS_CRITICAL
            status_prefix = "CRITICAL"
        
        # Build status message
        status_msg = f"{status_prefix} - {args.path}: {fs_used}/{fs_total} ({fs_percent:.1f}%) used"
        
        # Add top directories
        if args.show_details:
            status_msg += f" | Top {len(results)} directories:"
            for i, dir_info in enumerate(results, 1):
                mount_marker = " [MOUNT]" if dir_info.is_mountpoint else ""
                status_msg += f"\n  {i}. {dir_info.path}: {dir_info.size_human}{mount_marker}"
        else:
            # Compact format
            top_3 = results[:3]
            dir_list = ", ".join([f"{d.path}: {d.size_human}" for d in top_3])
            status_msg += f" | Top 3: {dir_list}"
        
        # Add performance data
        perf_data = []
        perf_data.append(f"used={disk_usage.used}B;;;0;{disk_usage.total}")
        perf_data.append(f"percent={fs_percent}%;{args.warning or ''};{args.critical or ''};0;100")
        
        # Add top directories as perfdata
        for i, dir_info in enumerate(results[:5], 1):
            # Sanitize path for perfdata (remove special chars)
            label = dir_info.path.replace('/', '_').replace(' ', '_').strip('_')
            if len(label) > 20:
                label = label[:20]
            perf_data.append(f"dir{i}_{label}={dir_info.size_bytes}B;;;;")
        
        final_message = status_msg
        if perf_data:
            final_message += f" | {' '.join(perf_data)}"
        
        return exit_code, final_message
        
    except Exception as e:
        error_msg = f"UNKNOWN - Error analyzing disk space: {str(e)}"
        if args.verbose:
            import traceback
            traceback.print_exc()
        return NAGIOS_UNKNOWN, error_msg


def main():
    parser = argparse.ArgumentParser(
        description="Nagios plugin to identify directories consuming the most disk space",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
This plugin analyzes directory sizes while respecting mount points. Mounted
filesystems are not counted towards their parent directories.

Examples:
  %(prog)s -p / --top 10 --depth 2
  %(prog)s -p /var --top 5 --depth 3 --show-details
  %(prog)s -p / --exclude /tmp --exclude /var/tmp
  %(prog)s -p / -w 80 -c 90 --top 15
  %(prog)s -p /var/lib --depth 2 -v
        """
    )
    
    parser.add_argument(
        "-p", "--path",
        default="/",
        help="Path to analyze (default: /)"
    )
    
    parser.add_argument(
        "-d", "--depth",
        type=int,
        default=2,
        help="Maximum directory depth to analyze (default: 2)"
    )
    
    parser.add_argument(
        "-t", "--top",
        type=int,
        default=10,
        help="Number of top directories to report (default: 10)"
    )
    
    parser.add_argument(
        "-w", "--warning",
        type=float,
        help="Warning threshold for filesystem usage in percent"
    )
    
    parser.add_argument(
        "-c", "--critical",
        type=float,
        help="Critical threshold for filesystem usage in percent"
    )
    
    parser.add_argument(
        "-e", "--exclude",
        action="append",
        default=[],
        help="Exclude paths from analysis (can be specified multiple times)"
    )
    
    parser.add_argument(
        "--show-details",
        action="store_true",
        help="Show detailed list of top directories in output"
    )
    
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Verbose output for debugging"
    )
    
    parser.add_argument(
        "-V", "--version",
        action="version",
        version="%(prog)s 1.0 - Disk space usage analysis for Nagios"
    )
    
    args = parser.parse_args()
    
    # Validate arguments
    if args.warning and args.critical:
        if args.critical <= args.warning:
            print("ERROR: Critical threshold must be higher than warning threshold")
            sys.exit(NAGIOS_UNKNOWN)
    
    if args.depth < 1:
        print("ERROR: Depth must be at least 1")
        sys.exit(NAGIOS_UNKNOWN)
    
    if args.top < 1:
        print("ERROR: Top must be at least 1")
        sys.exit(NAGIOS_UNKNOWN)
    
    # Perform the check
    exit_code, message = check_space_usage(args)
    print(message)
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
