# WebArena Task Structure Analysis

Analyzed `arena_repos/webarena/config_files/test.raw.json` with 812 original WebArena tasks, plus `evaluation_harness/evaluators.py`, `evaluation_harness/helper_functions.py`, `config/task_templates/*.yaml`, and `data/outputs/generated_tasks_100.json`.

Notes:
- Counts from explicit JSON fields are exact.
- Operation type, step count, query/filter markers, and information-transfer markers are heuristic classifications from task intent text.
- Current generated tasks are compared against the local 100-task sample, not an exhaustive generator run.

## Overall Stats

| Metric | Value |
|---|---:|
| Total WebArena tasks | 812 |
| Unique site labels | 6 |
| Unique site combinations | 12 |
| Single-site tasks | 764 (94.1%) |
| Two-site tasks | 48 (5.9%) |
| Unique `intent_template_id` values | 190 |
| Require login | 812 (100.0%) |
| Require reset | 0 (0.0%) |
| Start URLs with `\|AND\|` | 5 (0.6%) |
| Tasks with geolocation config | 0 (0.0%) |

## Site Distribution

Site combination counts:

| Sites | Tasks |
|---|---:|
| shopping | 187 |
| shopping_admin | 182 |
| gitlab | 180 |
| map | 109 |
| reddit | 106 |
| wikipedia + map | 16 |
| gitlab + reddit | 10 |
| reddit + gitlab | 8 |
| gitlab + wikipedia | 6 |
| shopping + reddit | 5 |
| map + shopping_admin | 2 |
| map + wikipedia | 1 |

Site membership counts, including multi-site tasks:

| Site | Membership Count |
|---|---:|
| gitlab | 204 |
| shopping | 192 |
| shopping_admin | 184 |
| reddit | 129 |
| map | 128 |
| wikipedia | 23 |

## Evaluator Structure

WebArena uses three evaluator families:
- `string_match`: checks the final `stop(answer=...)` answer against exact, must-include, or LLM fuzzy references.
- `url_match`: checks final browser URL base/path/query against one or more references.
- `program_html`: navigates or inspects page/API-derived state with JS locators or helper functions.

Eval type combinations:

| Eval Types | Tasks |
|---|---:|
| string_match | 325 |
| program_html | 282 |
| url_match + program_html | 129 |
| url_match | 66 |
| string_match + url_match | 10 |

Reference answer methods in string evals:

| Method | Uses |
|---|---:|
| must_include | 176 |
| fuzzy_match | 118 |
| exact_match | 45 |

`program_html` target locator patterns:

| Locator Pattern | Uses |
|---|---:|
| JS locator | 524 |
| Full page content | 105 |
| Helper function locator | 22 |

Programmatic helper functions used by evaluators:

| Helper | Uses | Purpose |
|---|---:|---|
| `reddit_get_post_url` | 65 | Normalize a comment/post URL to the post URL |
| `shopping_get_latest_order_url` | 10 | Retrieve latest order URL through shopping API |
| `gitlab_get_project_memeber_role` | 12 | Inspect GitLab member role from page DOM |
| `shopping_get_sku_latest_review_rating` | 5 | Retrieve latest review rating through shopping API |
| `shopping_get_sku_latest_review_author` | 5 | Retrieve latest review author through shopping API |

## Heuristic Task Taxonomy

Coarse operation types from intent text:

| Operation Type | Tasks |
|---|---:|
| Query / answer | 354 (43.6%) |
| Create / submit | 195 (24.0%) |
| Other / mixed | 175 (21.6%) |
| Modify / state-change | 61 (7.5%) |
| Delete / remove / negative action | 17 (2.1%) |
| Navigation | 10 (1.2%) |

Estimated step counts from intent complexity:

| Estimated Steps | Tasks |
|---|---:|
| 1-3 estimated steps | 467 (57.5%) |
| 4-6 estimated steps | 310 (38.2%) |
| 7+ estimated steps | 35 (4.3%) |

The estimate is based on operation type, multi-site use, compound action markers (`and`, `then`, `after`, `all`, `each`), ranking/recentness markers, and multi-evaluator configurations. It is best read as a relative complexity proxy, not a literal browser-action count.

Query/filter markers:

| Marker | Tasks |
|---|---:|
| Attribute/entity filter | 425 (52.3%) |
| Temporal/recent | 157 (19.3%) |
| Ranking/top-bottom | 154 (19.0%) |
| Route/distance/map | 147 (18.1%) |
| Aggregation/count | 87 (10.7%) |
| Comparison/threshold | 82 (10.1%) |
| Cross-reference | 81 (10.0%) |
| Negation/exclusion | 36 (4.4%) |

Marker density:

| Marker Count Per Task | Tasks |
|---|---:|
| 0 | 171 |
| 1 | 305 |
| 2 | 186 |
| 3 | 116 |
| 4 | 26 |
| 5 | 8 |

Information-transfer markers:

| Marker | Tasks |
|---|---:|
| None obvious | 622 (76.6%) |
| Literal text entry | 82 (10.1%) |
| Within-task transfer/copy | 60 (7.4%) |
| Multi-site transfer | 48 (5.9%) |

## WebArena Skeleton Patterns

Common high-volume skeletons by `intent_template_id`:

| Template ID | Tasks | Sites | Eval | Operation | Skeleton |
|---:|---:|---|---|---|---|
| 332 | 10 | gitlab | program_html | create/submit | Create a new scoped project and add account list as members |
| 279 | 7 | shopping_admin | string_match | query/answer | Ask for top-N best-selling product/brand/type over period |
| 366 | 7 | shopping_admin | string_match | query/answer | Get an attribute of an order with a status |
| 371 | 7 | wikipedia + map | program_html | navigation | Find a described Wikipedia entity page on the map |
| 222 | 6 | shopping | string_match | query/answer | List reviewers mentioning a description |
| 352 | 6 | gitlab | program_html | create/submit | Fork a repository |
| 247 | 6 | shopping_admin | program_html | other/mixed | Change this product price by amount |
| 87 | 6 | gitlab + wikipedia | program_html | create/submit | Create repo with topics in README |
| 328 | 6 | gitlab | url_match + program_html | create/submit | Open an issue in a repo |
| 335 | 6 | gitlab | url_match + program_html | create/submit | Submit merge request and assign reviewer |
| 25 | 6 | reddit | program_html | modify/state-change | Like all submissions by user in subreddit |
| 1510 | 6 | reddit | program_html | delete/remove/negative-action | Dislike all submissions by user in subreddit |
| 246 | 6 | shopping_admin | program_html | delete/remove/negative-action | Delete all reviews of a type |
| 742 | 6 | shopping_admin | program_html | other/mixed | Change price of configurable product by amount |
| 288 | 5 | shopping_admin | string_match | query/answer | Count reviews mentioning a term |
| 73 | 5 | map | string_match | query/answer | Compare walking and driving route time |
| 33 | 5 | reddit | string_match | query/answer | Count comments with downvotes > upvotes for a derived user |
| 77 | 5 | map | string_match | query/answer | Check one-hour car reachability |
| 197 | 5 | shopping | string_match | query/answer | Count fulfilled orders and spend over period |
| 68 | 5 | map | string_match | query/answer | Walking time between start and end |

Broader skeleton families visible in the benchmark:

| Family | Pattern | Representative Sites | Evaluator Shape |
|---|---|---|---|
| Answer extraction | Find/count/rank/compare facts and answer with text | shopping, shopping_admin, reddit, gitlab, map | mostly `string_match` |
| URL navigation target | End on a specific listing/detail/page URL | gitlab, reddit, misc/map | `url_match`, sometimes plus `program_html` |
| CRUD state mutation | Create issue/repo/project/post/review/order/cart item, edit price/order/page, delete reviews | gitlab, reddit, shopping, shopping_admin | mostly `program_html` |
| Bulk action | Like/dislike all matching submissions, delete all matching reviews | reddit, shopping_admin | `program_html` |
| Admin analytics | Top sellers, order status attributes, review counts, customer dissatisfaction reasons | shopping_admin | `string_match` |
| Cross-site transfer | Find information on one site and create/use it on another | gitlab + wikipedia, wikipedia + map, shopping + reddit | mostly `program_html` |
| Map/routing | Compute route time, reachability, nearest place, address lookup | map | mostly `string_match` |
| Derived target | Identify latest/top/matching entity, then act on it | reddit, shopping, shopping_admin, gitlab | mixed |

## Current Generated Template Coverage

Local template files define 14 templates:

| Environment | Templates | Allowed Actions |
|---|---:|---|
| gitlab | 4 | `comment`, `add_label`, `close_issue` |
| shopping | 5 | `add_to_cart`, `update_quantity`, `write_review` |
| forum | 3 | `create_post`, `comment_post` |
| cms_admin | 2 | `edit_page`, `publish_page` |

All current templates use `db_api_state_checker`.

Generated sample distribution:

| Dimension | Distribution |
|---|---|
| Environment | gitlab 48, shopping 29, forum 13, cms_admin 10 |
| Ability | Memory 60, Long-horizon 40 |
| Difficulty | L1 22, L2 20, L3 20, L4 20, L5 18 |
| Verifier | `db_api_checker_template` 100 |

Generated action coverage:

| Action | Uses |
|---|---:|
| comment | 29 |
| add_label | 23 |
| close_issue | 22 |
| write_review | 18 |
| add_to_cart | 17 |
| edit_page | 10 |
| comment_post | 9 |
| update_quantity | 8 |
| create_post | 7 |
| publish_page | 4 |

## Coverage Gaps

High-impact gaps versus WebArena:

| Gap | Evidence | Impact |
|---|---|---|
| Query/answer tasks are absent or under-modeled | WebArena has 325 `string_match` tasks and 354 heuristic query/answer tasks; generated tasks all use backend state checkers | Current set misses the largest WebArena family: information retrieval, aggregation, ranking, comparison, and free-text answers |
| URL-target tasks are absent | WebArena has 66 pure `url_match` and 139 tasks with URL matching | Current templates do not test navigation-to-result workflows |
| Page-content/DOM evaluators are absent | WebArena has 411 tasks with `program_html` in eval types and 524 JS locators | Current verifiers only inspect backend state, missing UI-visible state and final-page correctness |
| `shopping_admin` is missing | 184 WebArena site memberships | Large admin analytics and catalog/order management surface is uncovered |
| `map` and `wikipedia` are missing | 128 map and 23 wikipedia memberships; 48 multi-site tasks | Missing routing, geographic search, and cross-site information transfer |
| Reddit/forum coverage is action-narrow | WebArena reddit tasks include voting, bulk actions, comment/post discovery, latest/top derived targets; current forum has create/comment only | Current forum tasks do not cover social ranking, voting, deletion/negative actions, or derived targets |
| GitLab coverage is action-narrow | WebArena includes project/repo creation, forks, merge requests, membership roles, branch/commit queries, issue listings | Current GitLab is mainly issue comment/label/close |
| Shopping coverage lacks checkout/order history and admin inventory | WebArena includes order spend/counts, product configs, reviewers, SKU review APIs, price changes, deletes | Current shopping is cart/review only |
| Multi-site transfer is rare-to-absent | WebArena has 48 explicit multi-site tasks and 60 within-task transfer/copy markers | Current generated tasks target one environment at a time |
| Bulk and derived-target operations are missing | WebArena includes all matching items, latest/top/filtered targets, and count/threshold tasks | Current structures mostly bind a known entity directly or through simple locators |

## Recommended High-Priority Additions

1. Add answer-query templates and a `string_answer_checker`.
   - Skeletons: `answer_top_n`, `answer_count_matching`, `answer_attribute_of_order_or_entity`, `answer_route_time`, `answer_reviewers_matching_text`, `answer_commit_count`.
   - Required support: reference answer field with `exact_match`, `must_include`, and optional fuzzy matching.

2. Add URL navigation templates and a `url_match_checker`.
   - Skeletons: `navigate_to_filtered_issue_list`, `open_matching_post`, `open_product_or_order_detail`, `find_map_place_page`.
   - Required support: base/path/query matching and OR references.

3. Add page-content state checkers in addition to DB checkers.
   - Skeletons: `assert_visible_text`, `assert_dom_locator_text`, `assert_latest_entity_detail`, `assert_member_role`.
   - This closes the gap between backend state and WebArena's user-visible success checks.

4. Add `shopping_admin` templates.
   - Actions: `change_product_price`, `delete_reviews`, `inspect_order_attribute`, `answer_sales_analytics`, `answer_review_analytics`.
   - These should include ranking, temporal periods, order statuses, SKU/product config filters, and review text filters.

5. Add map/routing templates.
   - Actions/skeletons: `answer_route_duration`, `compare_route_modes`, `answer_reachability_within_time`, `answer_nearest_place`, `navigate_to_map_entity`.
   - These cover a large WebArena site family with mostly answer-based verification.

6. Expand GitLab beyond issue triage.
   - Actions: `create_project`, `fork_repo`, `create_issue`, `create_merge_request`, `assign_reviewer`, `add_project_member`, `create_readme`.
   - Query skeletons: commit counts by user/date, issue list filtering by labels, project member role lookup.

7. Expand forum/reddit with social operations.
   - Actions: `upvote`, `downvote`, `bulk_vote`, `find_latest_post`, `answer_comment_count`, `answer_vote_filtered_comments`.
   - Include derived target locators like latest post by user/subreddit and all submissions matching a predicate.

8. Add cross-site skeletons.
   - Skeletons: `lookup_info_then_create_repo_readme`, `wikipedia_entity_to_map_page`, `site_fact_to_forum_or_gitlab_text`, `shopping_item_to_reddit_post`.
   - Verifier should be able to check the destination state while task generation records the source dependency.

9. Add bulk and negative-operation templates.
   - Actions: `delete_all_matching`, `remove_from_cart`, `cancel_order`, `bulk_dislike`, `bulk_like`.
   - Include explicit safeguards in generated tasks so destructive scope is narrow and verifiable.

10. Add ranking/recent/threshold locator variants.
    - Structure variants: `latest_matching_entity`, `top_n_by_metric`, `threshold_filtered_entities`, `temporal_period_aggregate`, `negated_filter`.
    - These are more WebArena-like than direct entity lookup, and they exercise memory/information tracking without requiring extra writes.

## Practical Template Roadmap

Suggested order for largest coverage gain:

| Priority | Addition | Why First |
|---:|---|---|
| 1 | `string_answer_checker` + query templates | Covers the largest WebArena family and adds non-mutating tasks |
| 2 | `url_match_checker` + navigation/listing templates | Covers final-location tasks and filtered search workflows |
| 3 | `shopping_admin` analytics and mutation templates | Adds a missing high-count site and ranking/temporal filters |
| 4 | GitLab project/fork/MR/member templates | Leverages existing GitLab entity model while expanding action diversity |
| 5 | Map/routing answer templates | Adds a distinct domain with high marker density |
| 6 | Cross-site transfer templates | Adds WebArena-style compositionality after source/destination verifiers exist |

## Key Takeaways

- WebArena is not primarily a CRUD benchmark. It is almost half answer-query tasks, with strong use of ranking, filtering, aggregation, temporal constraints, and route/map reasoning.
- The local generator currently produces clean backend-grounded state-change tasks, but all 100 generated tasks use one verifier family. This creates a much narrower behavioral surface than WebArena's string, URL, DOM, and helper-function evaluators.
- The biggest missing sites are `shopping_admin`, `map`, and `wikipedia`; the biggest missing task families are answer extraction, URL navigation, admin analytics, cross-site transfer, bulk operations, and derived-target actions.
- High-priority skeletons should separate source/entity discovery from destination action and verifier shape. WebArena often asks agents to identify a target by latest/top/status/text filter, then answer or mutate that derived target.
