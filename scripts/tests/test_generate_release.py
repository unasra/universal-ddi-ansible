#!/usr/bin/env python3
"""
Test script for the release notes generator.
Mocks the GitHub API and AI responses to test the full pipeline locally.
"""

import json
import sys
from pathlib import Path
from unittest.mock import patch

# Add scripts to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from generate_release import (
    is_changelog_included,
    extract_issue_number,
    extract_copilot_review,
    prepare_pr_data,
    render_release_notes,
    render_changelog_entry,
    generate_verbatim_log,
    generate_combined_log,
    generate_ignored_log,
)

# --- Mock Data ---

MOCK_PRS = [
    {
        "number": 101,
        "title": "Add DHCP Lease module",
        "body": """## Summary
Added new DHCP Lease module for managing leases.

## Type of Change
- [x] 🆕 New Module

## Module Details
- **Module Name**: `infoblox.universal_ddi.dhcp_lease`
- **Category**: DHCP
- **Description**: Manage DHCP Lease on Universal DDI

## Ticket / Issue
Fixes #45

## Changelog Inclusion
- [x] Consider for changelog and release notes addition
""",
        "labels": [{"name": "new-module"}],
        "comments": [],
    },
    {
        "number": 102,
        "title": "Add DHCP Lease info module",
        "body": """## Summary
Added DHCP Lease info module.

## Type of Change
- [x] 🆕 New Module

## Module Details
- **Module Name**: `infoblox.universal_ddi.dhcp_lease_info`
- **Category**: DHCP
- **Description**: Get DHCP Lease information from Universal DDI

## Ticket / Issue
Fixes #45

## Changelog Inclusion
- [x] Consider for changelog and release notes addition
""",
        "labels": [{"name": "new-module"}],
        "comments": [],
    },
    {
        "number": 103,
        "title": "Fix DNS record creation with special characters",
        "body": """## Summary
Fixed a bug where DNS records with special characters in names would fail.

## Type of Change
- [x] 🐛 Bug Fix

## Ticket / Issue
Fixes #67

## Changelog Inclusion
- [x] Consider for changelog and release notes addition
""",
        "labels": [{"name": "bug"}],
        "comments": [],
    },
    {
        "number": 104,
        "title": "Update universal-ddi-python SDK to v2.1.0",
        "body": """## Summary
Bumped the SDK dependency version.

## Type of Change
- [x] 🧹 Maintenance (dependency upgrades, CI, refactoring)

## Changelog Inclusion
- [x] Consider for changelog and release notes addition
""",
        "labels": [{"name": "maintenance"}],
        "comments": [],
    },
    {
        "number": 105,
        "title": "Add tag filter support to ipam_address_block",
        "body": """## Summary
Added tag_filters parameter to ipam_address_block module.

## Type of Change
- [x] 🔧 Updating Existing Modules

## Ticket / Issue
Fixes #78

## Changelog Inclusion
- [x] Consider for changelog and release notes addition
""",
        "labels": [{"name": "enhancement"}],
        "comments": [],
    },
    {
        "number": 106,
        "title": "Fix typo in internal helper function",
        "body": """## Summary
Fixed a typo in an internal utility. No user-facing change.

## Type of Change
- [x] 🧹 Maintenance (dependency upgrades, CI, refactoring)

## Changelog Inclusion
- [ ] Consider for changelog and release notes addition
""",
        "labels": [],
        "comments": [],
    },
    {
        "number": 107,
        "title": "Update installation guide for v1.2",
        "body": """## Summary
Updated docs with new installation instructions.

## Type of Change
- [x] 📝 Documentation

## Changelog Inclusion
- [x] Consider for changelog and release notes addition
""",
        "labels": [{"name": "documentation"}],
        "comments": [],
    },
    {
        "number": 108,
        "title": "Fix CI badge in README",
        "body": """## Summary
Minor README fix.

## Type of Change
- [x] 📝 Documentation

## Changelog Inclusion
- [ ] Consider for changelog and release notes addition
""",
        "labels": [],
        "comments": [],
    },
]

# Mock AI analysis response
MOCK_AI_RESPONSE = {
    "release_summary": "Added DHCP Lease modules, improved existing module functionality with tag filter support, and fixed DNS record handling.",
    "new_modules": [
        {"name": "dhcp_lease", "category": "DHCP", "description": "Manage DHCP Lease on Universal DDI."},
        {"name": "dhcp_lease_info", "category": "DHCP", "description": "Get DHCP Lease information from Universal DDI."},
    ],
    "module_updates": [
        "Added tag filter support to `ipam_address_block` module (#78)",
    ],
    "bugfixes": [
        "Fixed DNS record creation with special characters in names (#67)",
    ],
    "documentation": [
        "Updated installation guide for v1.2",
    ],
    "maintenance": [
        "Updated universal-ddi-python SDK to v2.1.0",
    ],
    "grouping_log": [
        {
            "combined_entry": "Added DHCP Lease modules",
            "source_prs": ["#101", "#102"],
            "reason": "Both PRs add related DHCP Lease module and info module",
        }
    ],
}


def test_changelog_inclusion():
    """Test the changelog inclusion checkbox parsing."""
    print("=" * 60)
    print("TEST: Changelog Inclusion Parsing")
    print("=" * 60)

    included = [pr for pr in MOCK_PRS if is_changelog_included(pr)]
    excluded = [pr for pr in MOCK_PRS if not is_changelog_included(pr)]

    print(f"  Total PRs: {len(MOCK_PRS)}")
    print(f"  Included:  {len(included)} ✅")
    for pr in included:
        print(f"    - #{pr['number']}: {pr['title']}")
    print(f"  Excluded:  {len(excluded)} ⏭️")
    for pr in excluded:
        print(f"    - #{pr['number']}: {pr['title']}")

    assert len(included) == 6, f"Expected 6 included, got {len(included)}"
    assert len(excluded) == 2, f"Expected 2 excluded, got {len(excluded)}"
    assert 106 in [pr["number"] for pr in excluded]
    assert 108 in [pr["number"] for pr in excluded]
    print("  ✅ PASSED\n")


def test_issue_extraction():
    """Test GitHub issue number extraction."""
    print("=" * 60)
    print("TEST: Issue Number Extraction")
    print("=" * 60)

    results = {}
    for pr in MOCK_PRS:
        issue = extract_issue_number(pr)
        if issue:
            results[pr["number"]] = issue
            print(f"  PR #{pr['number']}: Issue #{issue}")

    assert results.get(101) == "45", f"Expected '45', got {results.get(101)}"
    assert results.get(103) == "67", f"Expected '67', got {results.get(103)}"
    assert results.get(105) == "78", f"Expected '78', got {results.get(105)}"
    assert 106 not in results
    print("  ✅ PASSED\n")


def test_prepare_pr_data():
    """Test PR data preparation."""
    print("=" * 60)
    print("TEST: PR Data Preparation")
    print("=" * 60)

    included = [pr for pr in MOCK_PRS if is_changelog_included(pr)]
    prepared = prepare_pr_data(included)

    print(f"  Prepared {len(prepared)} PRs")
    for p in prepared:
        issue_str = f" (Issue #{p['issue_number']})" if p.get("issue_number") else ""
        print(f"    - #{p['number']}: {p['title']}{issue_str}")

    assert len(prepared) == 6
    assert prepared[0]["issue_number"] == "45"
    print("  ✅ PASSED\n")


def test_render_release_notes():
    """Test release notes rendering."""
    print("=" * 60)
    print("TEST: Release Notes Rendering")
    print("=" * 60)

    output = render_release_notes(MOCK_AI_RESPONSE, "1.2.0")
    print(output)

    assert "v1.2.0" in output
    assert "DHCP Lease" in output
    assert "Bug Fixes" in output
    assert "Updated Modules" in output
    assert "Documentation" in output
    assert "Maintenance" in output
    print("  ✅ PASSED\n")


def test_render_changelog_entry():
    """Test changelog YAML entry rendering."""
    print("=" * 60)
    print("TEST: Changelog Entry Rendering")
    print("=" * 60)

    output = render_changelog_entry(MOCK_AI_RESPONSE, "1.2.0")
    print(output)

    assert "1.2.0:" in output
    assert "dhcp_lease" in output
    assert "bugfixes:" in output
    assert "module_updates:" in output
    print("  ✅ PASSED\n")


def test_generate_artifacts():
    """Test artifact generation."""
    print("=" * 60)
    print("TEST: Artifact Generation")
    print("=" * 60)

    included = [pr for pr in MOCK_PRS if is_changelog_included(pr)]
    excluded = [pr for pr in MOCK_PRS if not is_changelog_included(pr)]

    prs_data = prepare_pr_data(included)
    ignored_data = [{"number": pr["number"], "title": pr["title"]} for pr in excluded]

    verbatim = generate_verbatim_log(prs_data)
    combined = generate_combined_log(MOCK_AI_RESPONSE)
    ignored = generate_ignored_log(ignored_data)

    print("--- Verbatim Log ---")
    print(verbatim)
    print("\n--- Combined Log ---")
    print(combined)
    print("\n--- Ignored Log ---")
    print(ignored)

    assert "#101" in verbatim
    assert "#45" in verbatim  # issue number
    assert "DHCP Lease modules" in combined
    assert "#106" in ignored
    assert "#108" in ignored
    print("\n  ✅ PASSED\n")


def test_full_pipeline():
    """Test the full pipeline end-to-end with mocked AI."""
    print("=" * 60)
    print("TEST: Full Pipeline (Mocked AI + Dry Run)")
    print("=" * 60)

    from generate_release import main

    with patch("generate_release.get_merged_prs", return_value=MOCK_PRS), \
         patch("generate_release.analyze_prs_with_ai", return_value=MOCK_AI_RESPONSE):

        sys.argv = [
            "generate_release.py",
            "--version", "1.2.0",
            "--base-ref", "v1.1.0",
            "--dry-run",
        ]
        main()

    print("\n  ✅ PASSED\n")


if __name__ == "__main__":
    print("\n🧪 Running Release Generator Tests\n")

    test_changelog_inclusion()
    test_issue_extraction()
    test_prepare_pr_data()
    test_render_release_notes()
    test_render_changelog_entry()
    test_generate_artifacts()
    test_full_pipeline()

    print("=" * 60)
    print("🎉 ALL TESTS PASSED!")
    print("=" * 60)
