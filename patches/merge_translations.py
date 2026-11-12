#!/usr/bin/env python3
"""Add the strings of a patch to Music Assistant's English translation file.

Usage: merge_translations.py path/to/translations/en.json strings/<patch>.json
"""
import json
import sys

target, extra = sys.argv[1], sys.argv[2]
with open(target, encoding="utf-8") as fh:
    catalog = json.load(fh)
with open(extra, encoding="utf-8") as fh:
    catalog.update(json.load(fh))
with open(target, "w", encoding="utf-8") as fh:
    json.dump(dict(sorted(catalog.items())), fh, indent=2, ensure_ascii=False)
    fh.write("\n")
