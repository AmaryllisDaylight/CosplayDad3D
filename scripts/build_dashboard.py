#!/usr/bin/env python3
"""Shortcut wrapper to rebuild TRACKER.md and CosplayDad_Dashboard.html."""

from cms_manager import ensure_directories, build_tracker_and_dashboard

if __name__ == "__main__":
    ensure_directories()
    build_tracker_and_dashboard()
