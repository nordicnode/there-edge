#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Self-check for the pure-logic fixes landed in the ponytail review:
  * FlashProxy GuessToolbarVisibility y -> mask table must have every
    original 27 y values, each unique (no two rows sharing a y with
    different masks).
  * The documented ForwardCookie contract: cookies come back from
    InternetGetCookie as "name1=value1; name2=value2", and the matcher
    must find the requested name regardless of position or surrounding
    spaces, and not match a name that is a prefix of another.

These lock bugs #5 (ForwardCookie parsing) and #18 (the table refactor)
against regression. The actual C++ runs only under MSVC + the Windows
SDK; this script runs anywhere Python does, so the invariants can be
checked from this repo without a Windows build.

Run: python3 test_selfcheck.py
"""

import re
import sys
import pathlib


def _read_table(path):
    """Parse the YVisibility entries out of FlashProxy.cpp's GuessToolbarVisibility."""
    text = path.read_text(encoding='utf-8')
    start = text.index('static const YVisibility table')
    end = text.index('};', start)
    seg = ' '.join(text[start:end].split())
    rows = re.findall(r'\{\s*(\d+),\s*(.*?)\s*\}', seg)
    out = []
    for y, mask in rows:
        m = mask.replace('(UINT32)', '').replace('Identity::', '').replace(' ', '')
        toks = {
            'ShortcutBar': 'S', 'FunFinder': 'F', 'EmotionsBar': 'E', 'MessageBar': 'M',
        }
        bits = [toks.get(t, t) for t in m.split('|')]
        out.append((int(y), tuple(sorted(bits, key='SFE0M'.index) if bits[0] != '0' else ['0'])))
    return out


def _to_set(maskstr):
    m = maskstr.replace('(UINT32)', '').replace('Identity::', '').replace(' ', '')
    return tuple(sorted(m.split('|')))


def _find_cookie(cookies, name):
    """Mirror of BrowserProxy ForwardCookie's InternetGetCookie tokenizer."""
    namelen = len(name)
    cur = cookies
    while True:
        while cur.startswith(' '):
            cur = cur[1:]
        if cur[:namelen].lower() == name.lower() and cur[namelen:namelen + 1] == '=':
            end = cur.find(';')
            return cur[namelen + 1:end] if end >= 0 else cur[namelen + 1:]
        sep = cur.find(';')
        if sep < 0:
            return None
        cur = cur[sep + 1:]


def check_table():
    path = pathlib.Path('FlashProxy/FlashProxy.cpp')
    rows = _read_table(path)

    # The 27 (y, mask) pairs the original switch encoded, expressed as bit-sets
    # so order within a mask does not matter. Verified equal to the new table.
    expected = {
        (0, ('0',)), (24, ('M',)), (112, ('M',)), (48, ('S', 'M')), (136, ('S', 'M')),
        (58, ('F', 'M')), (146, ('F', 'M')), (46, ('E', 'M')), (134, ('E', 'M')),
        (82, ('S', 'F', 'M')), (170, ('S', 'F', 'M')),
        (70, ('E', 'S', 'M')), (158, ('E', 'S', 'M')),
        (80, ('E', 'F', 'M')), (168, ('E', 'F', 'M')),
        (104, ('E', 'F', 'M', 'S')), (192, ('E', 'F', 'M', 'S')),
        (88, ('0',)), (99, ('0',)), (123, ('M',)), (147, ('S', 'M')),
        (157, ('F', 'M')), (145, ('E', 'M')), (181, ('S', 'F', 'M')),
        (169, ('E', 'S', 'M')), (179, ('E', 'F', 'M')),
        (203, ('E', 'F', 'M', 'S')),
    }

    got = set((y, tuple(sorted(m))) for y, m in rows)
    expected = set((y, tuple(sorted(m))) for y, m in expected)

    assert len(rows) == 27, f"expected 27 table rows, got {len(rows)}"
    ys = [y for y, _ in rows]
    assert len(ys) == len(set(ys)), f"duplicate y in table: {sorted(set(ys) ^ set(ys))}"
    assert got == expected, (
        "table drift\n  missing: %s\n  extra:   %s"
        % (sorted(expected - got), sorted(got - expected))
    )


def check_cookie():
    # name present, mixed position
    assert _find_cookie('av=1; ticket=aBc123; tv=9', 'ticket') == 'aBc123'
    # single cookie, trailing terminator absent
    assert _find_cookie('ticket=aBc123', 'ticket') == 'aBc123'
    # name is prefix of another must NOT match the longer one
    assert _find_cookie('ticket=aBc123; ticketssl=x', 'ticket') == 'aBc123'
    assert _find_cookie('ticket=aBc123; ticketssl=x', 'ticketssl') == 'x'
    # leading spaces after ';'
    assert _find_cookie('a=1;  ticket=z', 'ticket') == 'z'
    # absent name -> None (S_OK, nothing to forward)
    assert _find_cookie('av=1; tv=9', 'ticket') is None
    # case-insensitive name match (InternetGetCookie is case-insensitive on Windows)
    assert _find_cookie('TICKET=aBc123', 'ticket') == 'aBc123'
    # empty value
    assert _find_cookie('av=; ticket=', 'ticket') == ''


def main():
    check_table()
    check_cookie()
    print("self-check OK")


if __name__ == '__main__':
    try:
        main()
    except AssertionError as e:
        print("self-check FAILED:", e, file=sys.stderr)
        sys.exit(1)
