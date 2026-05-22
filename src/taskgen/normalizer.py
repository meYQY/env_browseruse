"""
Entity normalizer: transforms extracted raw data (gitlab.json, shopping.json,
reddit.json) into the flat normalized entity format consumed by the task
generation framework.

Output format matches data/entities_sample.json (the canonical reference).
"""

from __future__ import annotations

import json
import random
from pathlib import Path
from typing import Any

# ---------------------------------------------------------------------------
# Deterministic seed so re-runs produce identical entities.
# ---------------------------------------------------------------------------
_RNG = random.Random(42)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _eid(site: str, etype: str, num: int) -> str:
    """Build a zero-padded entity id like ``gitlab_issue_001``."""
    return f"{site}_{etype}_{num:03d}"


def _pick(seq: list, rng: random.Random = _RNG) -> Any:
    """Pick a random element from *seq* (deterministic)."""
    return rng.choice(seq)


def _pick_n(seq: list, lo: int, hi: int, rng: random.Random = _RNG) -> list:
    """Pick between *lo* and *hi* unique elements (clamped to len)."""
    k = rng.randint(lo, min(hi, len(seq)))
    return rng.sample(seq, k)


# ---------------------------------------------------------------------------
# GitLab normalization
# ---------------------------------------------------------------------------

# Realistic issue-title keywords, derived from common software themes
_ISSUE_TITLE_HINTS = [
    "database timeout", "checkout failure", "checkout regression",
    "backend ownership", "checkout monitoring", "login redirect loop",
    "search index stale", "API rate limiting", "CI pipeline flaky",
    "dark-mode contrast", "memory leak on reload", "i18n missing keys",
    "CORS policy error", "pagination off-by-one", "email notification delay",
    "mobile layout broken", "caching invalidation", "file upload 413",
    "SSO callback failure", "token refresh race", "slow query optimization",
    "dependency upgrade", "accessibility audit", "docs out of date",
    "test coverage gap", "webhook delivery retry", "role permission bug",
    "merge conflict helper", "branch protection bypass", "release notes automation",
    "container build timeout", "runner disk full", "audit log missing events",
    "secret scanning false positive", "license compliance check",
    "milestone date mismatch", "label color inconsistency",
    "notification spam", "diff rendering glitch", "snippet sharing broken",
]

_GITLAB_LABELS_EXTRACTED = [
    "BUG", "OpenAPI Generator CLI", "flaky-test", "help needed",
    "help wanted", "question",
]

# Additional realistic labels (from the sample file and common practice)
_GITLAB_LABELS_EXTRA = [
    "bug", "frontend", "backend", "documentation", "enhancement",
    "good first issue", "priority::high", "priority::low", "security",
    "performance", "ux", "devops", "testing",
]

_ALL_LABELS = _GITLAB_LABELS_EXTRACTED + _GITLAB_LABELS_EXTRA

_ISSUE_STATES = ["open", "closed"]


def normalize_gitlab(data: dict) -> list[dict]:
    """Normalize GitLab raw data into project + issue + merge_request entities.

    Generates:
      - gitlab_project entities from repos with task_count > 0
      - gitlab_issue entities (from real issue iids + synthesized)
      - gitlab_mr entities from repos that have merge_request data
    """
    entities: list[dict] = []
    repos = data.get("repos", [])

    # ------------------------------------------------------------------
    # Phase 1: project entities (>= 10)
    # ------------------------------------------------------------------
    project_counter = 0
    repo_id_to_project_eid: dict[int, str] = {}

    # Prioritize repos with issues/MRs, then those with high task_count
    repos_sorted = sorted(
        [r for r in repos if r.get("task_count", 0) > 0],
        key=lambda r: (
            bool(r.get("issues")),
            bool(r.get("merge_requests")),
            r.get("task_count", 0),
        ),
        reverse=True,
    )

    for repo in repos_sorted:
        project_counter += 1
        eid = _eid("gitlab", "project", project_counter)
        repo_id_to_project_eid[repo["id"]] = eid

        attrs: dict[str, Any] = {"repo_name": repo["name"]}
        if repo.get("owner"):
            attrs["owner"] = repo["owner"]
        if repo.get("path"):
            attrs["path"] = repo["path"]
        if repo.get("entity_type") == "creation_target":
            attrs["is_creation_target"] = True

        entities.append({
            "entity_id": eid,
            "site": "gitlab",
            "entity_type": "project",
            "attributes": attrs,
            "relations": {},
            "provenance": {
                "source": "webarena_extracted",
                "source_task_ids": [],
            },
            "grounding_status": "symbolic_entity",
        })

        # Stop once we have enough projects (we need >= 10 but want good
        # coverage; cap at 50 to keep the set manageable).
        if project_counter >= 50:
            break

    # ------------------------------------------------------------------
    # Phase 2: issue entities from repos that have real issue data
    # ------------------------------------------------------------------
    issue_counter = 0
    title_hint_idx = 0

    for repo in repos:
        if not repo.get("issues"):
            continue
        proj_eid = repo_id_to_project_eid.get(repo["id"], _eid("gitlab", "project", 1))

        for iss in repo["issues"]:
            issue_counter += 1
            title_hint = _ISSUE_TITLE_HINTS[title_hint_idx % len(_ISSUE_TITLE_HINTS)]
            title_hint_idx += 1

            # Vary attribute richness
            state = _pick(_ISSUE_STATES)
            labels = _pick_n(_ALL_LABELS, 0, 2)

            attrs: dict[str, Any] = {"title_contains": title_hint, "state": state}
            if labels:
                attrs["labels"] = labels
            if iss.get("iid"):
                attrs["iid"] = iss["iid"]

            entities.append({
                "entity_id": _eid("gitlab", "issue", issue_counter),
                "site": "gitlab",
                "entity_type": "issue",
                "attributes": attrs,
                "relations": {"project_ref": proj_eid},
                "provenance": {
                    "source": "webarena_extracted",
                    "source_task_ids": [],
                },
                "grounding_status": "symbolic_entity",
            })

    # ------------------------------------------------------------------
    # Phase 3: synthesize additional issues to reach >= 30
    # ------------------------------------------------------------------
    # Distribute across projects that have task_count > 0
    project_eids = list(repo_id_to_project_eid.values())
    while issue_counter < 35:
        issue_counter += 1
        title_hint = _ISSUE_TITLE_HINTS[title_hint_idx % len(_ISSUE_TITLE_HINTS)]
        title_hint_idx += 1
        proj_ref = project_eids[(issue_counter - 1) % len(project_eids)]

        # Deliberate attribute-count buckets (L1-L5 support):
        bucket = issue_counter % 5
        state = _pick(_ISSUE_STATES)

        if bucket == 0:
            # 1 attribute (L1/L2)
            attrs = {"title_contains": title_hint}
        elif bucket in (1, 2):
            # 2-3 attributes (L3)
            attrs = {"title_contains": title_hint, "state": state}
            if _RNG.random() > 0.4:
                attrs["labels"] = _pick_n(_ALL_LABELS, 1, 2)
        else:
            # 4+ attributes (L4/L5)
            attrs = {
                "title_contains": title_hint,
                "state": state,
                "labels": _pick_n(_ALL_LABELS, 1, 3),
                "assignee_username": _pick([
                    "byteblaze", "ericwbailey", "dev_alice", "qa_bob",
                ]),
            }
            if _RNG.random() > 0.5:
                attrs["milestone"] = _pick(["v1.0", "v2.0", "backlog", "sprint-12"])

        entities.append({
            "entity_id": _eid("gitlab", "issue", issue_counter),
            "site": "gitlab",
            "entity_type": "issue",
            "attributes": attrs,
            "relations": {"project_ref": proj_ref},
            "provenance": {
                "source": "webarena_extracted_synthesized",
                "source_task_ids": [],
            },
            "grounding_status": "symbolic_entity",
        })

    # ------------------------------------------------------------------
    # Phase 4: merge-request entities (bonus, from real data)
    # ------------------------------------------------------------------
    mr_counter = 0
    for repo in repos:
        if not repo.get("merge_requests"):
            continue
        proj_eid = repo_id_to_project_eid.get(repo["id"], _eid("gitlab", "project", 1))
        for mr in repo["merge_requests"]:
            mr_counter += 1
            attrs: dict[str, Any] = {}
            if mr.get("title_hint"):
                attrs["title_contains"] = mr["title_hint"]
            if mr.get("iid"):
                attrs["iid"] = mr["iid"]
            attrs["state"] = _pick(["merged", "open", "closed"])

            entities.append({
                "entity_id": _eid("gitlab", "mr", mr_counter),
                "site": "gitlab",
                "entity_type": "merge_request",
                "attributes": attrs,
                "relations": {"project_ref": proj_eid},
                "provenance": {
                    "source": "webarena_extracted",
                    "source_task_ids": [],
                },
                "grounding_status": "symbolic_entity",
            })

    return entities


# ---------------------------------------------------------------------------
# Shopping normalization
# ---------------------------------------------------------------------------

# Synthesized category buckets (derived from extracted categories)
_SHOPPING_CATEGORIES = [
    "fitness", "electronics", "clothing", "home & kitchen",
    "grocery", "beauty", "sports", "toys & games",
    "office", "outdoor", "video games", "cell phones",
]

_COLORS = ["black", "blue", "red", "white", "green", "purple", "gray", "pink"]
_SIZES = ["XS", "S", "M", "L", "XL", "XXL"]
_MATERIALS = ["cotton", "polyester", "nylon", "spandex", "fleece"]


def normalize_shopping(data: dict) -> list[dict]:
    """Normalize shopping raw data into product + product_variant entities.

    Generates:
      - shopping_product entities from products with task_count > 0
      - shopping_product_variant entities (synthesized)
    """
    entities: list[dict] = []
    products = data.get("products", [])

    # ------------------------------------------------------------------
    # Phase 1: product entities (>= 25)
    # ------------------------------------------------------------------
    product_counter = 0
    product_eid_list: list[tuple[str, str]] = []  # (eid, name)

    # Filter to products with names and task_count > 0
    eligible = [
        p for p in products
        if p.get("names") and p["names"][0] and p.get("task_count", 0) > 0
    ]

    for prod in eligible:
        product_counter += 1
        eid = _eid("shopping", "product", product_counter)
        name = prod["names"][0]
        product_eid_list.append((eid, name))

        # Vary attribute richness
        bucket = product_counter % 5
        attrs: dict[str, Any] = {"product_name": name}

        if bucket >= 1:
            cat = _pick(_SHOPPING_CATEGORIES)
            attrs["category"] = cat
        if bucket >= 3:
            if prod.get("sku"):
                attrs["sku"] = prod["sku"]
            attrs["has_reviews"] = _pick([True, False])
        if bucket == 4:
            attrs["price_range"] = _pick(["under_25", "25_50", "50_100", "100_plus"])

        entities.append({
            "entity_id": eid,
            "site": "shopping",
            "entity_type": "product",
            "attributes": attrs,
            "relations": {},
            "provenance": {
                "source": "webarena_extracted",
                "source_task_ids": [],
            },
            "grounding_status": "symbolic_entity",
        })

        # Cap at a reasonable number (we need >= 25)
        if product_counter >= 40:
            break

    # Also add products that only have url_slugs (no name), if needed to reach 25
    if product_counter < 25:
        slug_products = [
            p for p in products
            if not p.get("names") and p.get("url_slug") and p.get("task_count", 0) > 0
        ]
        for prod in slug_products:
            product_counter += 1
            eid = _eid("shopping", "product", product_counter)
            slug = prod["url_slug"]
            readable_name = slug.replace("-", " ").title()[:60]
            product_eid_list.append((eid, readable_name))
            entities.append({
                "entity_id": eid,
                "site": "shopping",
                "entity_type": "product",
                "attributes": {
                    "product_name": readable_name,
                    "url_slug": slug,
                },
                "relations": {},
                "provenance": {
                    "source": "webarena_extracted",
                    "source_task_ids": [],
                },
                "grounding_status": "symbolic_entity",
            })
            if product_counter >= 25:
                break

    # ------------------------------------------------------------------
    # Phase 2: product_variant entities (>= 15, synthesized)
    # ------------------------------------------------------------------
    variant_counter = 0
    for prod_eid, prod_name in product_eid_list:
        # Generate 1-2 variants per product (cycle through)
        n_variants = 1 if variant_counter % 3 != 0 else 2
        for _ in range(n_variants):
            variant_counter += 1
            color = _pick(_COLORS)
            size = _pick(_SIZES)
            in_stock = _pick([True, True, True, False])  # bias toward in-stock

            # Attribute richness buckets
            bucket = variant_counter % 4
            attrs: dict[str, Any] = {"product_name": prod_name}

            if bucket == 0:
                # 2 attrs
                attrs["color"] = color
            elif bucket == 1:
                # 3 attrs
                attrs["color"] = color
                attrs["size"] = size
            elif bucket == 2:
                # 4 attrs
                attrs["color"] = color
                attrs["size"] = size
                attrs["in_stock"] = in_stock
            else:
                # 5 attrs
                attrs["color"] = color
                attrs["size"] = size
                attrs["in_stock"] = in_stock
                attrs["material"] = _pick(_MATERIALS)

            entities.append({
                "entity_id": _eid("shopping", "variant", variant_counter),
                "site": "shopping",
                "entity_type": "product_variant",
                "attributes": attrs,
                "relations": {"product_ref": prod_eid},
                "provenance": {
                    "source": "webarena_extracted_synthesized",
                    "source_task_ids": [],
                },
                "grounding_status": "symbolic_entity",
            })

            if variant_counter >= 20:
                break
        if variant_counter >= 20:
            break

    return entities


# ---------------------------------------------------------------------------
# Reddit / Forum normalization
# ---------------------------------------------------------------------------

def normalize_reddit(data: dict) -> list[dict]:
    """Normalize reddit/forum raw data into community + post entities.

    Generates:
      - forum_community entities from forums with url_confirmed=true and task_count > 0
      - forum_post entities from forums that have posts
    """
    entities: list[dict] = []
    forums = data.get("forums", [])

    # ------------------------------------------------------------------
    # Phase 1: community entities (>= 15)
    # ------------------------------------------------------------------
    community_counter = 0
    slug_to_community_eid: dict[str, str] = {}

    # Eligible: url_confirmed=true and task_count > 0
    eligible_communities = [
        f for f in forums
        if f.get("url_confirmed") is True and f.get("task_count", 0) > 0
    ]

    # Sort by task_count desc for best coverage
    eligible_communities.sort(key=lambda f: f.get("task_count", 0), reverse=True)

    for forum in eligible_communities:
        community_counter += 1
        eid = _eid("forum", "community", community_counter)
        slug = forum["slug"]
        slug_to_community_eid[slug] = eid

        attrs: dict[str, Any] = {"community_name": slug}
        if forum.get("aliases"):
            attrs["aliases"] = forum["aliases"]
        # Add post_count for richer attributes on some
        if community_counter % 3 == 0 and forum.get("posts"):
            attrs["post_count"] = len(forum["posts"])

        entities.append({
            "entity_id": eid,
            "site": "forum",
            "entity_type": "community",
            "attributes": attrs,
            "relations": {},
            "provenance": {
                "source": "webarena_extracted",
                "source_task_ids": [],
            },
            "grounding_status": "symbolic_entity",
        })

        if community_counter >= 25:
            break

    # Also add forums without url_confirmed that have high task_count, if needed
    if community_counter < 15:
        extra_forums = [
            f for f in forums
            if f.get("url_confirmed") is not True and f.get("task_count", 0) > 0
        ]
        extra_forums.sort(key=lambda f: f.get("task_count", 0), reverse=True)
        for forum in extra_forums:
            community_counter += 1
            eid = _eid("forum", "community", community_counter)
            slug_to_community_eid[forum["slug"]] = eid
            entities.append({
                "entity_id": eid,
                "site": "forum",
                "entity_type": "community",
                "attributes": {
                    "community_name": forum["slug"],
                    "url_confirmed": False,
                },
                "relations": {},
                "provenance": {
                    "source": "webarena_extracted",
                    "source_task_ids": [],
                },
                "grounding_status": "symbolic_entity",
            })
            if community_counter >= 15:
                break

    # ------------------------------------------------------------------
    # Phase 2: post entities (>= 15)
    # ------------------------------------------------------------------
    post_counter = 0

    # Synthetic post title hints for enrichment
    _POST_TITLE_HINTS = [
        "public transit options", "best local restaurants",
        "weekend hiking trails", "affordable housing tips",
        "book recommendations for beginners", "DIY home improvement",
        "tech career advice", "stock market analysis",
        "movie review discussion", "music festival lineup",
        "science breakthrough news", "gaming setup showcase",
        "keyboard build log", "photography contest results",
        "historical facts thread", "fitness routine sharing",
        "cooking recipe exchange", "travel budget planning",
        "pet adoption stories", "climate change debate",
        "remote work productivity", "AI ethics discussion",
        "streaming service comparison", "local event announcement",
        "financial planning guide", "startup funding news",
        "open source project spotlight", "mental health resources",
        "education reform ideas", "sports highlights recap",
    ]

    title_idx = 0
    for forum in forums:
        if not forum.get("posts"):
            continue
        slug = forum["slug"]
        community_eid = slug_to_community_eid.get(slug)
        if not community_eid:
            # Forum not in community set; skip or add ad-hoc
            continue

        for post_data in forum["posts"]:
            post_counter += 1
            title_hint = _POST_TITLE_HINTS[title_idx % len(_POST_TITLE_HINTS)]
            title_idx += 1

            # Attribute richness buckets
            bucket = post_counter % 5
            attrs: dict[str, Any] = {"community": slug}

            if bucket == 0:
                # 1 attr (just community)
                pass
            elif bucket in (1, 2):
                # 2-3 attrs
                attrs["title_contains"] = title_hint
                if bucket == 2:
                    attrs["post_id"] = post_data.get("post_id", str(post_counter))
            else:
                # 4+ attrs
                attrs["title_contains"] = title_hint
                attrs["post_id"] = post_data.get("post_id", str(post_counter))
                attrs["has_comments"] = _pick([True, True, False])
                if _RNG.random() > 0.5:
                    attrs["sort_order"] = _pick(["hot", "new", "top", "most_commented"])

            entities.append({
                "entity_id": _eid("forum", "post", post_counter),
                "site": "forum",
                "entity_type": "post",
                "attributes": attrs,
                "relations": {"community_ref": community_eid},
                "provenance": {
                    "source": "webarena_extracted",
                    "source_task_ids": [],
                },
                "grounding_status": "symbolic_entity",
            })

            if post_counter >= 25:
                break
        if post_counter >= 25:
            break

    # Synthesize additional posts if we haven't reached 15
    while post_counter < 15:
        post_counter += 1
        title_hint = _POST_TITLE_HINTS[title_idx % len(_POST_TITLE_HINTS)]
        title_idx += 1
        # Pick a random community
        comm_eid = _pick(list(slug_to_community_eid.values()))
        comm_name = [
            k for k, v in slug_to_community_eid.items() if v == comm_eid
        ][0]

        attrs = {
            "community": comm_name,
            "title_contains": title_hint,
        }
        entities.append({
            "entity_id": _eid("forum", "post", post_counter),
            "site": "forum",
            "entity_type": "post",
            "attributes": attrs,
            "relations": {"community_ref": comm_eid},
            "provenance": {
                "source": "webarena_extracted_synthesized",
                "source_task_ids": [],
            },
            "grounding_status": "symbolic_entity",
        })

    return entities


# ---------------------------------------------------------------------------
# CMS fixture generation
# ---------------------------------------------------------------------------

_CMS_PAGES = [
    {"title": "return policy", "status": "published"},
    {"title": "shipping information", "status": "published"},
    {"title": "about us", "status": "published"},
    {"title": "privacy policy", "status": "published"},
    {"title": "terms and conditions", "status": "published"},
    {"title": "contact us", "status": "draft"},
    {"title": "holiday sale banner", "status": "draft"},
    {"title": "new arrivals promo", "status": "draft"},
    {"title": "customer testimonials", "status": "published"},
    {"title": "FAQ", "status": "published"},
]


def generate_cms_fixtures() -> list[dict]:
    """Generate 10 synthetic CMS page entities (no raw data source)."""
    entities: list[dict] = []
    for i, page in enumerate(_CMS_PAGES, start=1):
        # Attribute richness varies
        attrs: dict[str, Any] = {"page_title_contains": page["title"]}
        if i % 3 != 0:
            attrs["status"] = page["status"]
        if i % 4 == 0:
            attrs["url_key"] = page["title"].replace(" ", "-").lower()
        if i >= 7:
            attrs["content_type"] = _pick(["cms_block", "cms_page", "widget"])

        entities.append({
            "entity_id": _eid("cms", "page", i),
            "site": "cms_admin",
            "entity_type": "cms_page",
            "attributes": attrs,
            "relations": {},
            "provenance": {
                "source": "fixture_data",
                "source_task_ids": [],
            },
            "grounding_status": "symbolic_entity",
        })
    return entities


# ---------------------------------------------------------------------------
# Orchestration
# ---------------------------------------------------------------------------

def normalize_all(raw_data_dir: Path) -> list[dict]:
    """Read all raw entity files and return a unified normalized entity list.

    Parameters
    ----------
    raw_data_dir:
        Directory containing ``gitlab.json``, ``shopping.json``, and
        ``reddit.json``.

    Returns
    -------
    list[dict]
        Flat list of normalized entities (100+ items).
    """
    raw_data_dir = Path(raw_data_dir)

    # Load raw files
    with open(raw_data_dir / "gitlab.json", "r", encoding="utf-8") as f:
        gitlab_data = json.load(f)
    with open(raw_data_dir / "shopping.json", "r", encoding="utf-8") as f:
        shopping_data = json.load(f)
    with open(raw_data_dir / "reddit.json", "r", encoding="utf-8") as f:
        reddit_data = json.load(f)

    entities: list[dict] = []
    entities.extend(normalize_gitlab(gitlab_data))
    entities.extend(normalize_shopping(shopping_data))
    entities.extend(normalize_reddit(reddit_data))
    entities.extend(generate_cms_fixtures())

    return entities


def save_normalized(entities: list[dict], output_path: Path) -> None:
    """Write the normalized entity list to *output_path* as pretty JSON."""
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(entities, f, indent=2, ensure_ascii=False)


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------

def _print_summary(entities: list[dict]) -> None:
    """Print a quick breakdown of entity counts."""
    from collections import Counter
    counter = Counter((e["site"], e["entity_type"]) for e in entities)
    print(f"Total entities: {len(entities)}")
    for (site, etype), count in sorted(counter.items()):
        print(f"  {site}/{etype}: {count}")

    # Attribute-count distribution
    attr_buckets = Counter()
    for e in entities:
        n = len(e.get("attributes", {}))
        if n <= 1:
            attr_buckets["1 attr (L1/L2)"] += 1
        elif n <= 3:
            attr_buckets["2-3 attrs (L3)"] += 1
        else:
            attr_buckets["4+ attrs (L4/L5)"] += 1
    print("Attribute-count distribution:")
    for bucket, count in sorted(attr_buckets.items()):
        print(f"  {bucket}: {count}")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Normalize raw entities")
    parser.add_argument(
        "--raw-dir",
        type=Path,
        default=Path("data/entities"),
        help="Directory with gitlab.json, shopping.json, reddit.json",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("data/entities_normalized.json"),
        help="Output path for normalized JSON",
    )
    args = parser.parse_args()

    entities = normalize_all(args.raw_dir)
    _print_summary(entities)
    save_normalized(entities, args.output)
    print(f"\nWrote {len(entities)} entities to {args.output}")
