#!/usr/bin/env python3
"""
offline_time.py - epoch <-> Paris time helper for offline-earnings testing.

Usage (run with `py` on Windows to dodge pyenv):
    py tools/offline_time.py                # current epoch + UTC + Paris
    py tools/offline_time.py 1h             # epoch 1 hour ago  (set last_seen to this)
    py tools/offline_time.py 1h58m          # epoch 1h58m ago
    py tools/offline_time.py 90m            # epoch 90 min ago
    py tools/offline_time.py 1781261217     # convert an epoch to UTC + Paris

The "N ago" value is what you'd put in offline_last_seen to simulate that much
AFK. Remember: setting the save while connected won't show the popup (heartbeat
overwrites it + compute only runs at join). Prefer the in-game /sim_offline <hours>
command, which sets it AND re-runs compute in one shot.
"""
import re
import sys
import time
import datetime


def last_sunday(year, month):
    if month == 12:
        d = datetime.date(year, 12, 31)
    else:
        d = datetime.date(year, month + 1, 1) - datetime.timedelta(days=1)
    return d - datetime.timedelta(days=(d.weekday() - 6) % 7)  # Mon=0..Sun=6


def paris_offset_hours(utc_dt):
    """Europe/Paris: CEST (+2) last Sun Mar 01:00 UTC .. last Sun Oct 01:00 UTC, else CET (+1)."""
    y = utc_dt.year
    start = datetime.datetime.combine(last_sunday(y, 3), datetime.time(1, 0))
    end = datetime.datetime.combine(last_sunday(y, 10), datetime.time(1, 0))
    return 2 if start <= utc_dt < end else 1


def parse_duration(s):
    total, matched = 0.0, False
    for num, unit in re.findall(r'([0-9]*\.?[0-9]+)\s*([hms])', s.lower()):
        matched = True
        v = float(num)
        total += v * 3600 if unit == 'h' else v * 60 if unit == 'm' else v
    return total if matched else None


def show(epoch, label):
    utc = datetime.datetime.utcfromtimestamp(epoch)
    off = paris_offset_hours(utc)
    paris = utc + datetime.timedelta(hours=off)
    tz = "CEST" if off == 2 else "CET"
    print(f"  epoch : {epoch:.6f}   ({label})")
    print(f"  UTC   : {utc:%Y-%m-%d %H:%M:%S}")
    print(f"  Paris : {paris:%Y-%m-%d %H:%M:%S} ({tz}, UTC+{off})")


def handle(arg):
    """Process one input: an epoch to convert, or a duration to subtract from now."""
    now = time.time()

    # Bare number that looks like an epoch -> convert it.
    try:
        val = float(arg)
        if val > 1_000_000_000:
            show(val, "given epoch")
            return
    except ValueError:
        pass

    dur = parse_duration(arg)
    if dur is None:
        print(f"don't understand '{arg}'. try: 1h, 1h58m, 90m, 30s, or an epoch like 1781261217")
        return

    print("now:")
    show(now, "now")
    print(f"\n{arg} ago  -> set offline_last_seen to this:")
    show(now - dur, f"{arg} ago")


def interactive():
    print("offline_time tinker mode. enter a duration (1h, 1h58m, 90m, 30s) or an epoch.")
    print("'q' or empty line to quit.\n")
    while True:
        try:
            arg = input("> ").strip().lstrip("﻿")
        except (EOFError, KeyboardInterrupt):
            print()
            break
        if arg == "" or arg.lower() in ("q", "quit", "exit"):
            break
        handle(arg)
        print()


def main():
    if len(sys.argv) < 2:
        interactive()
        return
    handle(sys.argv[1])


if __name__ == "__main__":
    main()
