"""Extract entities from public WebArena / WebChoreArena task datasets.

Reconstructs the entity database from public task JSONs for GitLab,
Shopping, and Reddit. All entities get sequential integer IDs.

Usage:
    python src/extract_entities.py --output data/entities/
"""

from __future__ import annotations

import argparse
import json
import re
from collections import defaultdict
from pathlib import Path
from typing import Any


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def load_json(path: Path) -> list[dict]:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def save_json(obj: Any, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, indent=2)
        f.write("\n")


def _url_matches(pattern: str, text: str) -> list[str]:
    return [m.group(1) for m in re.finditer(pattern, text)]


# ---------------------------------------------------------------------------
# Reddit helpers
# ---------------------------------------------------------------------------

_FORUM_NAME_TO_SLUG: dict[str, str] = {
    "books forum": "books",
    "games forum": "games",
    "nyc forum": "nyc",
    "explain like im 5": "explainlikeimfive",
    "the deep learning": "deeplearning",
    "future technology": "Futurology",
    "machine learning": "MachineLearning",
    "news related forums": "news",
    "personal finances": "personalfinance",
}

_REDDIT_USER_PARAMS = {
    "Sariel007", "mossadnik", "nastratin", "chrisdh79", "thebelsnickle1991",
}


def _collect_all_url_forum_slugs(
    orig: list[dict], verified: list[dict], webchore: list[dict],
) -> set[str]:
    slugs: set[str] = set()
    for t in orig + verified + webchore:
        if "reddit" not in t.get("sites", []):
            continue
        ev = t.get("eval", {})
        if isinstance(ev, dict):
            for url_str in [ev.get("reference_url", "") or ""]:
                slugs.update(_url_matches(r"/f/(\w+)", url_str))
            for ph in ev.get("program_html", []):
                slugs.update(_url_matches(r"/f/(\w+)", ph.get("url", "")))
        if isinstance(ev, list):
            for e in ev:
                urls = e.get("expected", {}).get("url", [])
                if isinstance(urls, str):
                    urls = [urls]
                for url in urls:
                    if isinstance(url, str):
                        slugs.update(_url_matches(r"/f/(\w+)", url))
    return slugs


def _normalize_forum_name(
    raw: str, url_slugs: set[str], slug_lower_map: dict[str, str],
) -> str | None:
    if raw in _REDDIT_USER_PARAMS:
        return None
    clean = raw.replace("/f/", "").replace("f/", "").strip()
    if clean in url_slugs:
        return clean
    if clean.lower() in slug_lower_map:
        return slug_lower_map[clean.lower()]
    if raw in _FORUM_NAME_TO_SLUG:
        return _FORUM_NAME_TO_SLUG[raw]
    for k, v in _FORUM_NAME_TO_SLUG.items():
        if raw.lower() == k.lower():
            return v
    return clean


# ---------------------------------------------------------------------------
# GitLab
# ---------------------------------------------------------------------------

def _identify_creation_target_repos(
    orig: list[dict], verified: list[dict], webchore: list[dict],
) -> set[str]:
    """Simple patterns: only 'create a repo/repository/project' or 'fork'."""
    creation_repos: set[str] = set()
    for t in orig + verified + webchore:
        if "gitlab" not in t.get("sites", []):
            continue
        intent = t.get("intent", "").lower()
        inst = t.get("instantiation_dict", {})

        is_create = bool(
            re.search(r"\bcreate\s+a\s+(?:new\s+)?(?:repo(?:sitory)?|project)\b", intent)
            or re.search(r"\bfork\b", intent)
            or "in a new repository" in intent
        )
        if not is_create:
            continue

        for key in ("name", "project_name", "repo_name"):
            val = inst.get(key, "")
            if val and "/" not in val:
                creation_repos.add(f"byteblaze/{val}")

        repo2 = inst.get("repository2", "")
        if repo2 and "/" in repo2:
            creation_repos.add(repo2)

    return creation_repos


def extract_gitlab(
    orig: list[dict], verified: list[dict], webchore: list[dict],
) -> dict:
    orig_by_id = {t["task_id"]: t for t in orig}
    repos: dict[str, dict] = {}
    users: dict[str, dict] = {}
    branches: set[str] = set()
    labels: set[str] = set()
    groups: dict[str, dict] = {}
    ground_truth_facts: list[dict] = []
    creation_targets = _identify_creation_target_repos(orig, verified, webchore)

    def ensure_repo(path: str) -> dict:
        if path not in repos:
            repos[path] = {
                "path": path,
                "project_ids": [],
                "owner": path.split("/")[0] if "/" in path else None,
                "name": path.split("/")[1] if "/" in path else path,
                "issues": {},
                "merge_requests": {},
                "task_ids": set(),
            }
        return repos[path]

    def ensure_user(username: str) -> dict:
        if username not in users:
            users[username] = {
                "username": username,
                "display_names": set(),
                "task_ids": set(),
            }
        return users[username]

    u = ensure_user("byteblaze")
    u["display_names"].add("Byte Blaze")
    u["role"] = "primary_test_user"
    u["password"] = "hello1234"

    known_display_to_username = {
        "Abishek": "abisubramanya27",
        "Abishek S": "abisubramanya27",
        "Jakub Klinkovský": "lahwaacz",
        "Koushik": "koush",
        "Vinta": "vinta",
        "Benoît Blanchon": "bblanchon",
        "Eric Bailey": "ericwbailey",
        "Eric": "ericwbailey",
        "Steven Woodson": "stevenwoodson",
        "Nic Chan": "nickchan",
        "Nic": "nickchan",
        "Philip": "philip",
        "Kilian": "kilian",
        "Roshan Jossy": "roshanjossey",
        "Anthony": "anthony",
        "Muralekrishnan R": "muralekrishnan",
        "Akilesh Kannan": "akileshkannan",
        "Byte Blaze": "byteblaze",
        "First Contributions": "firstcontributions",
        "Convex Eggtart": "convexeggtart",
        "Meta": "meta",
        "TODO": "todo",
        "Do it myself": "doitmyself",
        "Awesome_DIY_ideas": "awesome_diy_ideas",
    }

    # --- Pass 1: All datasets - inst_dict extraction ---
    for t in orig + verified + webchore:
        if "gitlab" not in t.get("sites", []):
            continue
        tid = t["task_id"]
        inst = t.get("instantiation_dict", {})
        intent = t.get("intent", "")

        # Repos from inst_dict
        for key in ("repo", "project_name", "repo_name", "repository", "repository1", "repository2", "gitlab_repo", "project"):
            val = inst.get(key, "")
            if val and len(val) > 1:
                if "/" in val:
                    ensure_repo(val)["task_ids"].add(tid)
                elif key in ("repo", "repository", "repository1", "repository2", "gitlab_repo", "project"):
                    ensure_repo(f"byteblaze/{val}")["task_ids"].add(tid)

        # Users from inst_dict
        for key in ("user", "username", "member", "user1", "user2", "userName"):
            val = inst.get(key, "")
            if val and len(val) > 1:
                if val in known_display_to_username:
                    uname = known_display_to_username[val]
                    u = ensure_user(uname)
                    u["display_names"].add(val)
                    u["task_ids"].add(tid)
                else:
                    u = ensure_user(val)
                    u["task_ids"].add(tid)

        # Display names from inst_dict 'name' key and intent
        for key in ("name",):
            val = inst.get(key, "")
            if val and val in known_display_to_username:
                uname = known_display_to_username[val]
                u = ensure_user(uname)
                u["display_names"].add(val)
                u["task_ids"].add(tid)
        for display_name, username in known_display_to_username.items():
            if display_name in intent or display_name in str(inst):
                u = ensure_user(username)
                u["display_names"].add(display_name)
                u["task_ids"].add(tid)

        # Branches
        for key in ("source_branch", "target_branch", "branch", "branch_name"):
            val = inst.get(key, "")
            if val and val not in ("main", "master", "the default branch"):
                branches.add(val)

        # Labels
        for key in ("label", "label_name"):
            val = inst.get(key, "")
            if val:
                labels.add(val)

        # Account lists (groups of users)
        for key in ("account_list", "collaborator_account_list"):
            val = inst.get(key, "")
            if val:
                for name in re.split(r"[,;]\s*", str(val)):
                    name = name.strip()
                    if name and name in known_display_to_username:
                        uname = known_display_to_username[name]
                        u = ensure_user(uname)
                        u["display_names"].add(name)
                        u["task_ids"].add(tid)

    # --- Pass 2: Original WebArena - eval URLs ---
    for t in orig:
        if "gitlab" not in t.get("sites", []):
            continue
        tid = t["task_id"]
        inst = t.get("instantiation_dict", {})
        ev = t.get("eval", {})

        for ph in ev.get("program_html", []):
            url = ph.get("url", "")
            locator = ph.get("locator", "")

            m = re.match(r"__GITLAB__/([^/]+/[^/]+)/-/issues/(\d+)", url)
            if m:
                r = ensure_repo(m.group(1))
                iid = int(m.group(2))
                if iid not in r["issues"]:
                    r["issues"][iid] = {"iid": iid}
                r["issues"][iid].setdefault("task_ids", set()).add(tid)
                r["task_ids"].add(tid)
                kw = inst.get("issue", "") or inst.get("title", "")
                if kw:
                    r["issues"][iid]["title_hint"] = kw

            m = re.match(r"__GITLAB__/([^/]+/[^/]+)/-/merge_requests/(\d+)", url)
            if m:
                r = ensure_repo(m.group(1))
                iid = int(m.group(2))
                if iid not in r["merge_requests"]:
                    r["merge_requests"][iid] = {"iid": iid}
                r["merge_requests"][iid].setdefault("task_ids", set()).add(tid)
                r["task_ids"].add(tid)

            m_repo = re.match(r"__GITLAB__/([^/]+/[^/]+)", url)
            if m_repo:
                rp = m_repo.group(1)
                if "api/" not in rp and "dashboard" not in rp:
                    ensure_repo(rp)["task_ids"].add(tid)

            m2 = re.search(r"gitlab_get_project_memeber_role\(__page__,\s*'([^']+)'\)", locator)
            if m2:
                ensure_user(m2.group(1))["task_ids"].add(tid)

        ref_url = ev.get("reference_url", "") or ""
        for pattern, collection in [
            (r"__GITLAB__/([^/]+/[^/]+)/-/issues/(\d+)", "issues"),
            (r"__GITLAB__/([^/]+/[^/]+)/-/merge_requests/(\d+)", "merge_requests"),
        ]:
            m = re.match(pattern, ref_url)
            if m:
                r = ensure_repo(m.group(1))
                iid = int(m.group(2))
                if iid not in r[collection]:
                    r[collection][iid] = {"iid": iid}
                r[collection][iid].setdefault("task_ids", set()).add(tid)
                r["task_ids"].add(tid)

        m = re.match(r"__GITLAB__/([^/]+/[^/]+)", ref_url)
        if m:
            rp = m.group(1)
            if "api/" not in rp and "dashboard" not in rp:
                ensure_repo(rp)["task_ids"].add(tid)

    # --- Pass 3: Verified dataset ---
    for t in verified:
        if "gitlab" not in t.get("sites", []):
            continue
        tid = t["task_id"]
        inst = t.get("instantiation_dict", {})

        for e in t.get("eval", []):
            # Ground truth facts
            if e.get("expected", {}).get("task_type") == "retrieve":
                rd = e["expected"].get("retrieved_data")
                if rd is not None:
                    ground_truth_facts.append({
                        "task_id": tid,
                        "query": t["intent"],
                        "template": t.get("intent_template", ""),
                        "params": inst,
                        "answer": rd,
                    })

            if e.get("evaluator") != "NetworkEventEvaluator":
                continue
            exp = e["expected"]
            urls = exp.get("url", [])
            if isinstance(urls, str):
                urls = [urls]

            for url in urls:
                m = re.match(r"__GITLAB__/([^/]+/[^/]+)/", url)
                if m and "api/" not in m.group(1) and "dashboard" not in m.group(1):
                    ensure_repo(m.group(1))["task_ids"].add(tid)

                m2 = re.search(r"api/v4/projects/(\d+)", url)
                if m2:
                    pid = m2.group(1)
                    repo_name = inst.get("repo", "")
                    if repo_name and "/" in repo_name:
                        r = ensure_repo(repo_name)
                        if pid not in r["project_ids"]:
                            r["project_ids"].append(pid)

                m3 = re.search(r"projects/([^/]+%2F[^/]+)", url)
                if m3:
                    decoded = m3.group(1).replace("%2F", "/")
                    ensure_repo(decoded)["task_ids"].add(tid)

                m4 = re.match(r"__GITLAB__/([^/]+/[^/]+)/-/issues/(\d+)", url)
                if m4:
                    r = ensure_repo(m4.group(1))
                    iid = int(m4.group(2))
                    if iid not in r["issues"]:
                        r["issues"][iid] = {"iid": iid}
                    r["issues"][iid].setdefault("task_ids", set()).add(tid)

                m5 = re.search(r"users/([^/]+)/follow", url)
                if m5:
                    ensure_user(m5.group(1))["task_ids"].add(tid)

            qp = exp.get("query_params", {})
            target_ids = qp.get("target_id", [])
            target_types = qp.get("target_type", [])
            if "merge_request" in target_types and target_ids:
                for url in urls:
                    m = re.match(r"__GITLAB__/([^/]+/[^/]+)/notes", url)
                    if m:
                        r = ensure_repo(m.group(1))
                        internal_id = target_ids[0]
                        mr_iid = None
                        orig_t = orig_by_id.get(tid)
                        if orig_t:
                            for ph in orig_t.get("eval", {}).get("program_html", []):
                                m6 = re.search(r"merge_requests/(\d+)", ph.get("url", ""))
                                if m6:
                                    mr_iid = int(m6.group(1))
                        if mr_iid:
                            if mr_iid not in r["merge_requests"]:
                                r["merge_requests"][mr_iid] = {"iid": mr_iid}
                            r["merge_requests"][mr_iid]["internal_id"] = internal_id
                            r["merge_requests"][mr_iid]["title_hint"] = inst.get("mr", "")
                            r["merge_requests"][mr_iid].setdefault("task_ids", set()).add(tid)

    # --- Pass 4: WebChoreArena ---
    for t in webchore:
        if "gitlab" not in t.get("sites", []):
            continue
        tid = t["task_id"]
        inst = t.get("instantiation_dict", {})
        ev = t.get("eval", {})

        for ph in ev.get("program_html", []):
            url = ph.get("url", "")
            m = re.match(r"__GITLAB__/([^/]+/[^/]+)", url)
            if m:
                rp = m.group(1)
                if "api/" not in rp and "dashboard" not in rp:
                    ensure_repo(rp)["task_ids"].add(tid)

            m = re.match(r"__GITLAB__/([^/]+/[^/]+)/-/issues/(\d+)", url)
            if m:
                r = ensure_repo(m.group(1))
                iid = int(m.group(2))
                if iid not in r["issues"]:
                    r["issues"][iid] = {"iid": iid}
                r["issues"][iid].setdefault("task_ids", set()).add(tid)
                r["task_ids"].add(tid)

        ref_url = ev.get("reference_url", "") or ""
        m = re.match(r"__GITLAB__/([^/]+/[^/]+)", ref_url)
        if m:
            rp = m.group(1)
            if "api/" not in rp and "dashboard" not in rp:
                ensure_repo(rp)["task_ids"].add(tid)

        # WebChoreArena answers
        ans = inst.get("answer", "")
        if ans:
            ground_truth_facts.append({
                "task_id": tid,
                "source": "webchore",
                "query": t["intent"],
                "params": inst,
                "answer": ans,
            })

    # --- Build pid_to_repo ---
    pid_to_repo: dict[str, str] = {}
    for t in verified:
        if "gitlab" not in t.get("sites", []):
            continue
        inst = t.get("instantiation_dict", {})
        for e in t.get("eval", []):
            if e.get("evaluator") != "NetworkEventEvaluator":
                continue
            urls = e["expected"].get("url", [])
            if isinstance(urls, str):
                urls = [urls]
            for url in urls:
                m = re.search(r"api/v4/projects/(\d+)", url)
                if m:
                    pid = m.group(1)
                    repo = inst.get("repo", "")
                    if repo:
                        pid_to_repo.setdefault(pid, repo)

    # --- Serialize ---
    result_groups = []
    result_repos = []
    repo_id = 1
    for path in sorted(repos.keys()):
        if path.startswith("users/"):
            ensure_user(path.split("/")[1])
            continue
        if path.startswith("groups/"):
            result_groups.append({
                "path": path,
                "name": path.split("/")[1] if "/" in path else path,
                "task_count": len(repos[path]["task_ids"]),
            })
            continue
        r = repos[path]
        is_creation_target = path in creation_targets
        repo_obj = {
            "id": repo_id,
            "path": r["path"],
            "owner": r["owner"],
            "name": r["name"],
            "entity_type": "creation_target" if is_creation_target else "pre_existing",
            "project_ids": sorted(set(r["project_ids"])),
            "issues": [],
            "merge_requests": [],
            "task_count": len(r["task_ids"]),
        }
        issue_id = 1
        for iid in sorted(r["issues"].keys()):
            info = r["issues"][iid]
            issue_obj = {"iid": iid}
            if "title_hint" in info:
                issue_obj["title_hint"] = info["title_hint"]
            issue_obj["task_count"] = len(info.get("task_ids", set()))
            repo_obj["issues"].append(issue_obj)
        for iid in sorted(r["merge_requests"].keys()):
            info = r["merge_requests"][iid]
            mr_obj = {"iid": iid}
            if "internal_id" in info:
                mr_obj["internal_id"] = info["internal_id"]
            if "title_hint" in info:
                mr_obj["title_hint"] = info["title_hint"]
            mr_obj["task_count"] = len(info.get("task_ids", set()))
            repo_obj["merge_requests"].append(mr_obj)
        result_repos.append(repo_obj)
        repo_id += 1

    result_users = []
    user_id = 1
    for username in sorted(users.keys()):
        u = users[username]
        user_obj = {
            "id": user_id,
            "username": username,
            "display_names": sorted(u["display_names"]),
            "task_count": len(u["task_ids"]),
        }
        if "role" in u:
            user_obj["role"] = u["role"]
        if "password" in u:
            user_obj["password"] = u["password"]
        result_users.append(user_obj)
        user_id += 1

    pre_existing = sum(1 for r in result_repos if r["entity_type"] == "pre_existing")
    creation = sum(1 for r in result_repos if r["entity_type"] == "creation_target")

    return {
        "site": "gitlab",
        "backend": "GitLab CE (PostgreSQL)",
        "port": 8023,
        "accounts": {"username": "byteblaze", "password": "hello1234"},
        "pid_to_repo_hint": pid_to_repo,
        "repos": result_repos,
        "groups": result_groups,
        "users": result_users,
        "branches": sorted(branches),
        "labels": sorted(labels),
        "ground_truth_facts": ground_truth_facts,
        "stats": {
            "total_repos": len(result_repos),
            "pre_existing_repos": pre_existing,
            "creation_target_repos": creation,
            "total_groups": len(result_groups),
            "total_issues": sum(len(r["issues"]) for r in result_repos),
            "total_merge_requests": sum(len(r["merge_requests"]) for r in result_repos),
            "total_users": len(result_users),
            "total_branches": len(branches),
            "total_labels": len(labels),
            "total_ground_truth_facts": len(ground_truth_facts),
        },
    }


# ---------------------------------------------------------------------------
# Shopping
# ---------------------------------------------------------------------------

def extract_shopping(
    orig: list[dict], verified: list[dict], webchore: list[dict],
) -> dict:
    products: dict[str, dict] = {}
    categories: set[str] = set()
    orders: dict[str, dict] = {}
    people: dict[str, dict] = {}
    ground_truth_facts: list[dict] = []

    def _find_product_by_name(name: str) -> str | None:
        lower = name.lower()
        for key, p in products.items():
            if any(n.lower() == lower for n in p["names"]):
                return key
        return None

    name_lower_to_canonical: dict[str, str] = {}

    # --- Products with SKUs from helper functions ---
    for t in orig:
        if "shopping" not in t.get("sites", []) and "shopping_admin" not in t.get("sites", []):
            continue
        ev = t.get("eval", {})
        inst = t.get("instantiation_dict", {})
        for ph in ev.get("program_html", []):
            loc = ph.get("locator", "")
            m = re.search(r"shopping_get_sku_latest_review_\w+\('([^']+)'\)", loc)
            if m:
                sku = m.group(1)
                product_name = inst.get("product", "")
                if sku not in products:
                    products[sku] = {"sku": sku, "names": set(), "task_ids": set()}
                if product_name:
                    products[sku]["names"].add(product_name)
                products[sku]["task_ids"].add(t["task_id"])

    # --- Product slugs from verified NetworkEvent URLs ---
    for t in verified:
        if "shopping" not in t["sites"]:
            continue
        for e in t.get("eval", []):
            if e.get("evaluator") != "NetworkEventEvaluator":
                continue
            urls = e["expected"].get("url", [])
            if isinstance(urls, str):
                urls = [urls]
            for url in urls:
                m = re.match(r"__SHOPPING__/([a-z0-9][a-z0-9-]*\.html)$", url)
                if m:
                    slug = m.group(1).replace(".html", "")
                    key = f"slug:{slug}"
                    if key not in products:
                        products[key] = {"url_slug": slug, "names": set(), "task_ids": set()}
                    products[key]["task_ids"].add(t["task_id"])

    # --- Product names from inst_dict ---
    for t in orig + verified + webchore:
        sites = t.get("sites", [])
        if "shopping" not in sites and "shopping_admin" not in sites:
            continue
        inst = t.get("instantiation_dict", {})
        for key in ("product", "product_name", "product_name1", "product_name2"):
            product = inst.get(key, "")
            if not product or len(product) <= 2:
                continue
            lower = product.lower()
            if lower not in name_lower_to_canonical:
                name_lower_to_canonical[lower] = product
            canonical = name_lower_to_canonical[lower]

            existing_key = _find_product_by_name(product)
            if existing_key:
                products[existing_key]["names"].add(canonical)
                products[existing_key]["task_ids"].add(t["task_id"])
            else:
                pkey = f"name:{lower}"
                if pkey not in products:
                    products[pkey] = {"names": set(), "task_ids": set()}
                products[pkey]["names"].add(canonical)
                products[pkey]["task_ids"].add(t["task_id"])

    # --- Categories from inst_dict ---
    for t in orig + verified + webchore:
        sites = t.get("sites", [])
        if "shopping" not in sites and "shopping_admin" not in sites:
            continue
        inst = t.get("instantiation_dict", {})
        for key in ("category", "product_category", "product_type"):
            val = inst.get(key, "")
            if val and len(val) > 1:
                categories.add(val)

    # --- Categories from verified URLs ---
    for t in verified:
        if "shopping" not in t["sites"]:
            continue
        for e in t.get("eval", []):
            if e.get("evaluator") != "NetworkEventEvaluator":
                continue
            urls = e["expected"].get("url", [])
            if isinstance(urls, str):
                urls = [urls]
            for url in urls:
                m2 = re.match(r"__SHOPPING__/([\w-]+(?:/[\w-]+)+\.html)$", url)
                if m2 and "/" in m2.group(1):
                    categories.add(m2.group(1))

    # --- Orders from inst_dict ---
    valid_order_re = re.compile(r"^\d+$")
    for t in orig + verified + webchore:
        sites = t.get("sites", [])
        if "shopping" not in sites and "shopping_admin" not in sites:
            continue
        inst = t.get("instantiation_dict", {})
        for key in ("order_number", "order", "order_id"):
            val = str(inst.get(key, "")).strip()
            if not val:
                continue
            # Some values are descriptors like "highest", "newest" - skip those
            if valid_order_re.match(val):
                if val not in orders:
                    orders[val] = {"order_number": val, "task_ids": set()}
                orders[val]["task_ids"].add(t["task_id"])

    # --- People (reviewers, customers) from inst_dict ---
    for t in orig + verified + webchore:
        sites = t.get("sites", [])
        if "shopping" not in sites and "shopping_admin" not in sites:
            continue
        inst = t.get("instantiation_dict", {})
        for key in ("reviewer_name", "customer_name", "name", "customer"):
            val = inst.get(key, "")
            if val and len(val) > 2 and not val.isdigit():
                lower = val.lower()
                if lower not in people:
                    people[lower] = {"name": val, "task_ids": set()}
                people[lower]["task_ids"].add(t["task_id"])

    # --- Ground truth: verified retrieve answers ---
    for t in verified:
        sites = t.get("sites", [])
        if "shopping" not in sites and "shopping_admin" not in sites:
            continue
        for e in t.get("eval", []):
            if e.get("expected", {}).get("task_type") != "retrieve":
                continue
            rd = e["expected"].get("retrieved_data")
            if rd is not None:
                ground_truth_facts.append({
                    "task_id": t["task_id"],
                    "site": sites[0],
                    "query": t["intent"],
                    "template": t.get("intent_template", ""),
                    "params": t.get("instantiation_dict", {}),
                    "answer": rd,
                })

    # --- Ground truth: WebChoreArena answers ---
    for t in webchore:
        sites = t.get("sites", [])
        if "shopping" not in sites and "shopping_admin" not in sites:
            continue
        inst = t.get("instantiation_dict", {})
        for key in ("answer", "ground_truth", "expected_answer"):
            val = inst.get(key, "")
            if val:
                ground_truth_facts.append({
                    "task_id": t["task_id"],
                    "source": "webchore",
                    "site": sites[0],
                    "query": t["intent"],
                    "params": inst,
                    "answer": val,
                })
                break  # one fact per task

    # --- Enrich products from ground truth ---
    for fact in ground_truth_facts:
        answer = fact["answer"]
        if not isinstance(answer, list):
            continue
        for item in answer:
            if not isinstance(item, dict):
                continue
            name = item.get("product_name") or item.get("name") or item.get("title")
            sku = item.get("sku")
            if sku and isinstance(sku, str):
                if sku not in products:
                    products[sku] = {"sku": sku, "names": set(), "task_ids": set()}
                if name:
                    products[sku]["names"].add(str(name))
            elif name and isinstance(name, str) and len(name) > 2:
                lower = name.lower()
                pkey = f"name:{lower}"
                if pkey not in products:
                    products[pkey] = {"names": set(), "task_ids": set(), "from_ground_truth": True}
                products[pkey]["names"].add(name)

    # --- Serialize ---
    result_products = []
    prod_id = 1
    for key in sorted(products.keys()):
        p = products[key]
        obj = {"id": prod_id}
        if "sku" in p:
            obj["sku"] = p["sku"]
        if "url_slug" in p:
            obj["url_slug"] = p["url_slug"]
        obj["names"] = sorted(p["names"])
        obj["task_count"] = len(p.get("task_ids", set()))
        if p.get("from_ground_truth"):
            obj["source"] = "ground_truth"
        result_products.append(obj)
        prod_id += 1

    result_categories = []
    cat_id = 1
    for cat in sorted(categories):
        result_categories.append({"id": cat_id, "name": cat})
        cat_id += 1

    result_orders = []
    order_id = 1
    for onum in sorted(orders.keys(), key=lambda x: int(x)):
        o = orders[onum]
        result_orders.append({
            "id": order_id,
            "order_number": o["order_number"],
            "task_count": len(o["task_ids"]),
        })
        order_id += 1

    result_people = []
    person_id = 1
    for lower_name in sorted(people.keys()):
        p = people[lower_name]
        result_people.append({
            "id": person_id,
            "name": p["name"],
            "task_count": len(p["task_ids"]),
        })
        person_id += 1

    return {
        "site": "shopping",
        "backend": "Magento 2 (MySQL)",
        "port": 7770,
        "admin_port": 7780,
        "accounts": {
            "customer": {"username": "emma.lopez@gmail.com", "password": "Password.123"},
            "admin": {"username": "admin", "password": "admin1234"},
        },
        "db_credentials": {"user": "magentouser", "password": "MyPassword", "database": "magentodb"},
        "products": result_products,
        "categories": result_categories,
        "orders": result_orders,
        "people": result_people,
        "ground_truth_facts": ground_truth_facts,
        "stats": {
            "total_products": len(result_products),
            "products_with_sku": sum(1 for p in result_products if "sku" in p),
            "products_from_ground_truth": sum(1 for p in result_products if p.get("source") == "ground_truth"),
            "total_categories": len(result_categories),
            "total_orders": len(result_orders),
            "total_people": len(result_people),
            "total_ground_truth_facts": len(ground_truth_facts),
        },
    }


# ---------------------------------------------------------------------------
# Reddit
# ---------------------------------------------------------------------------

def extract_reddit(
    orig: list[dict], verified: list[dict], webchore: list[dict],
) -> dict:
    url_slugs = _collect_all_url_forum_slugs(orig, verified, webchore)
    slug_lower_map = {s.lower(): s for s in url_slugs}

    forums: dict[str, dict] = {}
    reddit_users: dict[str, dict] = {}
    ground_truth_facts: list[dict] = []

    def ensure_forum(slug: str) -> dict:
        if slug not in forums:
            forums[slug] = {
                "slug": slug,
                "url_confirmed": slug in url_slugs,
                "posts": {},
                "task_ids": set(),
                "raw_names": set(),
            }
        return forums[slug]

    def ensure_reddit_user(username: str) -> dict:
        if username not in reddit_users:
            reddit_users[username] = {"username": username, "task_ids": set()}
        return reddit_users[username]

    # --- All datasets: forums and users from inst_dict ---
    for t in orig + verified + webchore:
        if "reddit" not in t.get("sites", []):
            continue
        tid = t["task_id"]
        inst = t.get("instantiation_dict", {})

        # Forums
        for key in ("forum", "subreddit", "forum1", "forum2"):
            raw_forum = inst.get(key, "")
            if not raw_forum:
                continue
            if raw_forum in _REDDIT_USER_PARAMS:
                ensure_reddit_user(raw_forum)["task_ids"].add(tid)
                continue
            # Handle comma-separated values
            for part in raw_forum.split(","):
                part = part.strip()
                if not part:
                    continue
                slug = _normalize_forum_name(part, url_slugs, slug_lower_map)
                if slug is None:
                    continue
                f = ensure_forum(slug)
                f["task_ids"].add(tid)
                f["raw_names"].add(part)

        # Users
        for key in ("user", "username", "author"):
            val = inst.get(key, "")
            if not val or len(val) <= 1:
                continue
            # Handle comma-separated users like "Picture-unrelated, WhoIsJolyonWest"
            for part in re.split(r"[,;]\s*", val):
                part = part.strip()
                if part and len(part) > 1:
                    ensure_reddit_user(part)["task_ids"].add(tid)

    # Forums from URLs
    for slug in url_slugs:
        ensure_forum(slug)

    # --- Post IDs from URLs ---
    for t in orig + webchore:
        if "reddit" not in t.get("sites", []):
            continue
        ev = t.get("eval", {})
        ref_url = ev.get("reference_url", "") or ""
        for m in re.finditer(r"/f/(\w+)/(\d+)", ref_url):
            f = ensure_forum(m.group(1))
            pid = m.group(2)
            f["posts"][pid] = {"post_id": pid}
            f["task_ids"].add(t["task_id"])

        for ph in ev.get("program_html", []):
            for m in re.finditer(r"/f/(\w+)/(\d+)", ph.get("url", "")):
                f = ensure_forum(m.group(1))
                pid = m.group(2)
                f["posts"][pid] = {"post_id": pid}

        refs = ev.get("reference_answers") or {}
        for k, v in refs.items():
            if isinstance(v, list):
                for item in v:
                    if isinstance(item, str):
                        for m in re.finditer(r"/f/(\w+)/(\d+)", item):
                            f = ensure_forum(m.group(1))
                            f["posts"][m.group(2)] = {"post_id": m.group(2)}

    # Verified posts
    for t in verified:
        if "reddit" not in t["sites"]:
            continue
        for e in t.get("eval", []):
            if e.get("evaluator") != "NetworkEventEvaluator":
                continue
            urls = e["expected"].get("url", [])
            if isinstance(urls, str):
                urls = [urls]
            for url in urls:
                for m in re.finditer(r"/f/(\w+)/(\d+)", url):
                    f = ensure_forum(m.group(1))
                    f["posts"][m.group(2)] = {"post_id": m.group(2)}

    # --- Ground truth: verified retrieve ---
    for t in verified:
        if "reddit" not in t["sites"]:
            continue
        for e in t.get("eval", []):
            if e.get("expected", {}).get("task_type") != "retrieve":
                continue
            rd = e["expected"].get("retrieved_data")
            if rd is not None:
                ground_truth_facts.append({
                    "task_id": t["task_id"],
                    "query": t["intent"],
                    "template": t.get("intent_template", ""),
                    "params": t.get("instantiation_dict", {}),
                    "answer": rd,
                })

    # --- Ground truth: WebChoreArena answers ---
    for t in webchore:
        if "reddit" not in t.get("sites", []):
            continue
        inst = t.get("instantiation_dict", {})
        for key in ("answer", "ans"):
            val = inst.get(key, "")
            if val:
                ground_truth_facts.append({
                    "task_id": t["task_id"],
                    "source": "webchore",
                    "query": t["intent"],
                    "params": inst,
                    "answer": val,
                })
                break

    # --- Enrich users from ground truth ---
    for fact in ground_truth_facts:
        answer = fact["answer"]
        if isinstance(answer, list):
            for item in answer:
                if isinstance(item, dict):
                    for key in ("username", "author"):
                        username = item.get(key)
                        if username and isinstance(username, str):
                            ensure_reddit_user(username)
        if isinstance(answer, str):
            for m in re.finditer(r"/user/(\w+)", str(answer)):
                ensure_reddit_user(m.group(1))

    # Known account
    reddit_users.setdefault("MarvelsGrantMan136", {
        "username": "MarvelsGrantMan136",
        "task_ids": set(),
    })
    reddit_users["MarvelsGrantMan136"]["role"] = "primary_test_user"

    # --- Serialize ---
    result_forums = []
    forum_id = 1
    for slug in sorted(forums.keys(), key=str.lower):
        f = forums[slug]
        obj = {
            "id": forum_id,
            "slug": f["slug"],
            "url_confirmed": f["url_confirmed"],
            "posts": [{"post_id": pid} for pid in sorted(f["posts"].keys())],
            "task_count": len(f["task_ids"]),
        }
        raw = sorted(f["raw_names"] - {slug})
        if raw:
            obj["aliases"] = raw
        result_forums.append(obj)
        forum_id += 1

    result_users = []
    user_id = 1
    for username in sorted(reddit_users.keys()):
        u = reddit_users[username]
        user_obj = {
            "id": user_id,
            "username": username,
            "task_count": len(u.get("task_ids", set())),
        }
        if "role" in u:
            user_obj["role"] = u["role"]
        result_users.append(user_obj)
        user_id += 1

    return {
        "site": "reddit",
        "backend": "Postmill (PostgreSQL)",
        "port": 9999,
        "accounts": {"username": "MarvelsGrantMan136", "password": "test1234"},
        "forums": result_forums,
        "users": result_users,
        "ground_truth_facts": ground_truth_facts,
        "stats": {
            "total_forums": len(result_forums),
            "url_confirmed_forums": sum(1 for f in result_forums if f["url_confirmed"]),
            "total_posts_with_id": sum(len(f["posts"]) for f in result_forums),
            "total_users": len(result_users),
            "total_ground_truth_facts": len(ground_truth_facts),
        },
    }


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(description="Extract entities from WebArena datasets")
    parser.add_argument("--arena-repos", type=Path, default=Path("arena_repos"))
    parser.add_argument("--output", type=Path, default=Path("data/entities"))
    args = parser.parse_args()

    base = args.arena_repos
    orig = load_json(base / "webarena" / "config_files" / "test.raw.json")
    verified = load_json(base / "webarena-verified" / "assets" / "dataset" / "webarena-verified.json")
    webchore = load_json(base / "WebChoreArena" / "BrowserGym" / "config_files" / "test_webchore.raw.json")

    print(f"Loaded: {len(orig)} original, {len(verified)} verified, {len(webchore)} webchore tasks")

    gitlab = extract_gitlab(orig, verified, webchore)
    shopping = extract_shopping(orig, verified, webchore)
    reddit = extract_reddit(orig, verified, webchore)

    save_json(gitlab, args.output / "gitlab.json")
    save_json(shopping, args.output / "shopping.json")
    save_json(reddit, args.output / "reddit.json")

    # Clean up old map.json
    map_path = args.output / "map.json"
    if map_path.exists():
        map_path.unlink()
        print("Deleted map.json")

    print()
    print("=== Extraction Summary ===")
    for name, data in [("GitLab", gitlab), ("Shopping", shopping), ("Reddit", reddit)]:
        print(f"{name}: {data['stats']}")
    print()
    print(f"Output written to {args.output}/")


if __name__ == "__main__":
    main()
