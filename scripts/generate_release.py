#!/usr/bin/env python3
"""
Generate changelog and release notes for the Universal DDI Ansible Collection.

This script:
1. Collects merged PRs between two git refs using `gh` CLI
2. Filters out PRs that opted out of changelog inclusion
3. Sends PR data to an AI model for analysis and grouping
4. Renders changelog.yaml entry and release_notes.md using Jinja2 templates
5. Produces reference artifacts (verbatim PR titles, grouped entries log, ignored PRs)
"""

import argparse
import json
import os
import re
import subprocess
import sys
from datetime import date
from pathlib import Path

import yaml
from jinja2 import Environment, FileSystemLoader
from openai import OpenAI

SCRIPT_DIR = Path(__file__).parent
TEMPLATES_DIR = SCRIPT_DIR / "templates"
REPO_ROOT = SCRIPT_DIR.parent
CHANGELOG_PATH = REPO_ROOT / "changelogs" / "changelog.yaml"
OUTPUT_DIR = REPO_ROOT / "release_output"


def get_merged_prs(base_ref: str, head_ref: str, repo: str) -> list[dict]:
    """Fetch merged PRs between two refs using gh CLI."""
    result = subprocess.run(
        [
            "gh", "pr", "list",
            "--repo", repo,
            "--state", "merged",
            "--base", "master",
            "--json", "number,title,body,labels,comments",
            "--limit", "200",
            "--search", f"merged:>={_get_tag_date(base_ref, repo)}",
        ],
        capture_output=True, text=True, check=True
    )
    prs = json.loads(result.stdout)
    return prs


def _get_tag_date(tag: str, repo: str) -> str:
    """Get the date of a tag to use as search filter."""
    result = subprocess.run(
        ["gh", "api", f"repos/{repo}/releases/tags/{tag}", "--jq", ".published_at"],
        capture_output=True, text=True, check=True
    )
    return result.stdout.strip()[:10]


def extract_copilot_review(pr: dict) -> str | None:
    """Extract Copilot review summary from PR comments."""
    comments = pr.get("comments", [])
    for comment in comments:
        body = comment.get("body", "")
        author = comment.get("author", {}).get("login", "")
        if "copilot" in author.lower() or "## PR Description" in body:
            return body
    return None


def is_changelog_included(pr: dict) -> bool:
    """Check if the PR opted into changelog inclusion via the checkbox."""
    body = pr.get("body", "") or ""
    # Match checked checkbox for changelog consideration
    # [x] or [X] means include, [ ] means exclude
    pattern = r"\-\s*\[([xX ])\]\s*Consider for changelog"
    match = re.search(pattern, body)
    if match:
        return match.group(1).lower() == "x"
    # Default to include if checkbox not found (backward compat)
    return True


def extract_issue_number(pr: dict) -> str | None:
    """Extract linked GitHub issue number from PR body."""
    body = pr.get("body", "") or ""
    # Look for patterns like "Fixes #123", "Closes #456", or just "#123" in the ticket section
    patterns = [
        r"Fixes\s+#(\d+)",
        r"Closes\s+#(\d+)",
        r"Resolves\s+#(\d+)",
        r"##\s*Ticket\s*/\s*Issue[^\n]*\n[^#]*?#(\d+)",
    ]
    for pattern in patterns:
        match = re.search(pattern, body, re.IGNORECASE)
        if match:
            return match.group(1)
    return None


def prepare_pr_data(prs: list[dict]) -> list[dict]:
    """Prepare PR data for AI analysis."""
    prepared = []
    for pr in prs:
        copilot_review = extract_copilot_review(pr)
        labels = [label.get("name", "") for label in pr.get("labels", [])]
        issue_number = extract_issue_number(pr)
        prepared.append({
            "number": pr["number"],
            "title": pr["title"],
            "body": pr.get("body", "") or "",
            "labels": labels,
            "copilot_review": copilot_review,
            "issue_number": issue_number,
        })
    return prepared


def analyze_prs_with_ai(prs_data: list[dict], model: str = "gpt-4o") -> dict:
    """Send PR data to AI model for analysis and categorization."""
    prompt_template = (TEMPLATES_DIR / "agent_prompt.txt").read_text()
    prompt = prompt_template.replace("{{ prs_json }}", json.dumps(prs_data, indent=2))

    client = OpenAI(
        base_url=os.environ.get("AI_API_BASE_URL", "https://models.github.ai/inference"),
        api_key=os.environ.get("AI_API_KEY", os.environ.get("GITHUB_TOKEN", "")),
    )

    response = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": "You are a release notes generator. Always respond with valid JSON only."},
            {"role": "user", "content": prompt},
        ],
        temperature=0.2,
        response_format={"type": "json_object"},
    )

    result = json.loads(response.choices[0].message.content)
    return result


def render_release_notes(data: dict, version: str) -> str:
    """Render release notes markdown from AI output."""
    env = Environment(loader=FileSystemLoader(str(TEMPLATES_DIR)))
    template = env.get_template("release_notes.md.j2")

    new_modules_by_category = {}
    for module in data.get("new_modules", []):
        category = module.get("category", "Other")
        new_modules_by_category.setdefault(category, []).append(module)

    rendered = template.render(
        version=version,
        date=date.today().strftime("%B %d, %Y"),
        release_summary=data.get("release_summary", ""),
        new_modules=new_modules_by_category if new_modules_by_category else None,
        module_updates=data.get("module_updates", []),
        bugfixes=data.get("bugfixes", []),
        documentation=data.get("documentation", []),
        maintenance=data.get("maintenance", []),
    )
    return rendered


def render_changelog_entry(data: dict, version: str) -> str:
    """Render changelog YAML entry from AI output."""
    env = Environment(loader=FileSystemLoader(str(TEMPLATES_DIR)))
    template = env.get_template("changelog_entry.yaml.j2")

    all_modules = data.get("new_modules", [])
    new_modules_by_category = {}
    for module in all_modules:
        category = module.get("category", "Other")
        new_modules_by_category.setdefault(category, []).append(module)

    rendered = template.render(
        version=version,
        release_summary=data.get("release_summary", ""),
        new_modules=new_modules_by_category if new_modules_by_category else None,
        all_modules=all_modules,
        module_updates=data.get("module_updates", []),
        bugfixes=data.get("bugfixes", []),
        documentation=data.get("documentation", []),
        maintenance=data.get("maintenance", []),
        release_date=date.today().strftime("%Y-%m-%d"),
    )
    return rendered


def generate_verbatim_log(prs: list[dict]) -> str:
    """Generate a log of PR titles as-is."""
    lines = ["# PR Titles (Verbatim)", ""]
    lines.append("These PR titles were included in this release as-is or used as input for changelog generation.")
    lines.append("")
    for pr in prs:
        issue_ref = f" (#{pr['issue_number']})" if pr.get("issue_number") else ""
        lines.append(f"- #{pr['number']}: {pr['title']}{issue_ref}")
    return "\n".join(lines)


def generate_combined_log(data: dict) -> str:
    """Generate a log showing which PRs were combined."""
    lines = ["# PR Grouping Log", ""]
    lines.append("This file shows which PR titles were combined into single changelog entries.")
    lines.append("")

    grouping_log = data.get("grouping_log", [])
    if not grouping_log:
        lines.append("No PRs were combined in this release.")
    else:
        for entry in grouping_log:
            lines.append(f"## {entry['combined_entry']}")
            lines.append(f"**Source PRs:** {', '.join(entry['source_prs'])}")
            lines.append(f"**Reason:** {entry.get('reason', 'Related changes')}")
            lines.append("")

    return "\n".join(lines)


def generate_ignored_log(ignored_prs: list[dict]) -> str:
    """Generate a log of PRs that were excluded from changelog."""
    lines = ["# Ignored PRs (Excluded from Changelog)", ""]
    lines.append("These PRs had the changelog inclusion checkbox unchecked and were not included in the release notes.")
    lines.append("")

    if not ignored_prs:
        lines.append("No PRs were ignored in this release.")
    else:
        for pr in ignored_prs:
            lines.append(f"- #{pr['number']}: {pr['title']}")

    return "\n".join(lines)


def update_changelog(new_entry: str):
    """Append new version entry to the existing changelog.yaml."""
    if not CHANGELOG_PATH.exists():
        CHANGELOG_PATH.parent.mkdir(parents=True, exist_ok=True)
        CHANGELOG_PATH.write_text("ancestor: null\nreleases:\n")

    content = CHANGELOG_PATH.read_text()
    content = content.rstrip() + "\n" + new_entry + "\n"
    CHANGELOG_PATH.write_text(content)


def main():
    parser = argparse.ArgumentParser(description="Generate changelog and release notes")
    parser.add_argument("--version", required=True, help="Release version (e.g., 1.2.0)")
    parser.add_argument("--base-ref", required=True, help="Base git ref (previous release tag, e.g., v1.1.0)")
    parser.add_argument("--head-ref", default="HEAD", help="Head git ref (default: HEAD)")
    parser.add_argument("--repo", default="infobloxopen/universal-ddi-ansible", help="GitHub repo (owner/name)")
    parser.add_argument("--model", default="gpt-4o", help="AI model to use")
    parser.add_argument("--dry-run", action="store_true", help="Print output without writing files")
    args = parser.parse_args()

    print(f"📦 Generating release notes for v{args.version}")
    print(f"   Range: {args.base_ref}..{args.head_ref}")
    print()

    # Step 1: Collect PRs
    print("🔍 Fetching merged PRs...")
    prs = get_merged_prs(args.base_ref, args.head_ref, args.repo)
    print(f"   Found {len(prs)} merged PRs")

    if not prs:
        print("❌ No merged PRs found in the given range. Exiting.")
        sys.exit(1)

    # Step 2: Filter by changelog inclusion checkbox
    included_prs = [pr for pr in prs if is_changelog_included(pr)]
    ignored_prs = [pr for pr in prs if not is_changelog_included(pr)]
    print(f"   ✅ {len(included_prs)} PRs included for changelog")
    print(f"   ⏭️  {len(ignored_prs)} PRs excluded (checkbox unchecked)")

    # Step 3: Prepare data
    prs_data = prepare_pr_data(included_prs)
    ignored_data = [{"number": pr["number"], "title": pr["title"]} for pr in ignored_prs]

    # Step 4: AI Analysis
    print("🤖 Analyzing PRs with AI...")
    analysis = analyze_prs_with_ai(prs_data, model=args.model)
    print("   Analysis complete")

    # Step 5: Generate outputs
    print("📝 Generating outputs...")
    release_notes = render_release_notes(analysis, args.version)
    changelog_entry = render_changelog_entry(analysis, args.version)
    verbatim_log = generate_verbatim_log(prs_data)
    combined_log = generate_combined_log(analysis)
    ignored_log = generate_ignored_log(ignored_data)

    if args.dry_run:
        print("\n--- Release Notes ---")
        print(release_notes)
        print("\n--- Changelog Entry ---")
        print(changelog_entry)
        print("\n--- Verbatim Log ---")
        print(verbatim_log)
        print("\n--- Combined Log ---")
        print(combined_log)
        print("\n--- Ignored PRs ---")
        print(ignored_log)
        return

    # Step 6: Write outputs
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    (OUTPUT_DIR / "release_notes.md").write_text(release_notes)
    (OUTPUT_DIR / "pr_titles_verbatim.md").write_text(verbatim_log)
    (OUTPUT_DIR / "pr_titles_combined.md").write_text(combined_log)
    (OUTPUT_DIR / "pr_titles_ignored.md").write_text(ignored_log)

    # Update changelog
    update_changelog(changelog_entry)

    print(f"✅ Done! Outputs written to {OUTPUT_DIR}/")
    print(f"   - release_notes.md")
    print(f"   - pr_titles_verbatim.md")
    print(f"   - pr_titles_combined.md")
    print(f"   - pr_titles_ignored.md")
    print(f"   - changelogs/changelog.yaml (updated)")


if __name__ == "__main__":
    main()
