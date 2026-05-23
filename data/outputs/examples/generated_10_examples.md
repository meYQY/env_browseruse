# Generated Browser-Use Task Examples

## Task 1: task_0001

**Task description:**
In GitLab, find the issue whose title is file upload 413. Add a comment containing "added reproduction steps".

**Target environment:** gitlab

**Ability dimension:** Memory

**Difficulty:** L1

**Target entity:** gitlab_issue_018

**Ground truth:**

- `issue_comments` where {'issue_ref': 'gitlab_issue_018', 'author_ref': 'current_user'} must satisfy {'exists': True, 'body_must_include': ['added reproduction steps']}

**Verifier:**

- Query `issue_comments` with filters {'issue_ref': 'gitlab_issue_018', 'author_ref': 'current_user'}, check {'exists': True, 'body_must_include': ['added reproduction steps']}

- Execution status: `not_executed`

**Validation status:**

- symbolic_grounded: True

- backend_grounded: False

- verifier_executed: False

- needs_backend_validation: True

---

## Task 2: task_0093

**Task description:**
In the shopping site, find the product variant whose product name is a cat t-shirt. Add it to the cart with quantity 1.

**Target environment:** shopping

**Ability dimension:** Long-horizon

**Difficulty:** L1

**Target entity:** shopping_variant_011

**Ground truth:**

- `cart_items` where {'user_ref': 'current_user', 'variant_ref': 'shopping_variant_011'} must satisfy {'exists': True, 'quantity': 1}

**Verifier:**

- Query `cart_items` with filters {'user_ref': 'current_user', 'variant_ref': 'shopping_variant_011'}, check {'exists': True, 'quantity': 1}

- Execution status: `not_executed`

**Validation status:**

- symbolic_grounded: True

- backend_grounded: False

- verifier_executed: False

- needs_backend_validation: True

---

## Task 3: task_0047

**Task description:**
In the forum, find the post whose title is science breakthrough news. Add a comment containing "I would check public transit options first".

**Target environment:** forum

**Ability dimension:** Memory

**Difficulty:** L2

**Target entity:** forum_post_011

**Ground truth:**

- `comments` where {'post_ref': 'forum_post_011', 'author_ref': 'current_user'} must satisfy {'exists': True, 'body_must_include': ['I would check public transit options first']}

**Verifier:**

- Query `comments` with filters {'post_ref': 'forum_post_011', 'author_ref': 'current_user'}, check {'exists': True, 'body_must_include': ['I would check public transit options first']}

- Execution status: `not_executed`

**Validation status:**

- symbolic_grounded: True

- backend_grounded: False

- verifier_executed: False

- needs_backend_validation: True

---

## Task 4: task_0120

**Task description:**
In the CMS admin, find the page whose page title is customer testimonials. Create a page with a title containing "loyalty rewards" and a body containing "international shipping restrictions apply".

**Target environment:** cms_admin

**Ability dimension:** Long-horizon

**Difficulty:** L2

**Target entity:** cms_page_009

**Ground truth:**

- `cms_pages` where {'page_ref': 'cms_page_009'} must satisfy {'exists': True, 'title_must_include': ['loyalty rewards'], 'body_must_include': ['international shipping restrictions apply'], 'creator_ref': 'current_user'}

**Verifier:**

- Query `cms_pages` with filters {'page_ref': 'cms_page_009'}, check {'exists': True, 'title_must_include': ['loyalty rewards'], 'body_must_include': ['international shipping restrictions apply'], 'creator_ref': 'current_user'}

- Execution status: `not_executed`

**Validation status:**

- symbolic_grounded: True

- backend_grounded: False

- verifier_executed: False

- needs_backend_validation: True

---

## Task 5: task_0011

**Task description:**
In GitLab, find the issue with IID 8 and whose state is open. Add the "frontend" label.

**Target environment:** gitlab

**Ability dimension:** Memory

**Difficulty:** L3

**Target entity:** gitlab_issue_007

**Ground truth:**

- `issue_labels` where {'issue_ref': 'gitlab_issue_007'} must satisfy {'labels_include': 'frontend'}

**Verifier:**

- Query `issue_labels` with filters {'issue_ref': 'gitlab_issue_007'}, check {'labels_include': 'frontend'}

- Execution status: `not_executed`

**Validation status:**

- symbolic_grounded: True

- backend_grounded: False

- verifier_executed: False

- needs_backend_validation: True

---

## Task 6: task_0078

**Task description:**
In GitLab, find the issue whose state is open and whose title is mobile layout broken; then find the issue with IID 316. For the issue titled mobile layout broken: Add a comment containing "performance regression noted". For the issue titled mobile layout broken: Add the "security" label. For the issue titled mobile layout broken: Close the issue. For the issue #316: Reopen the issue. For the issue #316: Assign the issue to qa_bob.

**Target environment:** gitlab

**Ability dimension:** Long-horizon

**Difficulty:** L3

**Target entity:** gitlab_issue_016

**Ground truth:**

- `issue_comments` where {'issue_ref': 'gitlab_issue_016', 'author_ref': 'current_user'} must satisfy {'exists': True, 'body_must_include': ['performance regression noted']}

- `issue_labels` where {'issue_ref': 'gitlab_issue_016'} must satisfy {'labels_include': 'security'}

- `issues` where {'issue_ref': 'gitlab_issue_016'} must satisfy {'state': 'closed'}

- `issues` where {'issue_ref': 'gitlab_issue_010'} must satisfy {'state': 'open'}

- `issues` where {'issue_ref': 'gitlab_issue_010'} must satisfy {'assignee_ref': 'qa_bob'}

**Verifier:**

- Query `issue_comments` with filters {'issue_ref': 'gitlab_issue_016', 'author_ref': 'current_user'}, check {'exists': True, 'body_must_include': ['performance regression noted']}

- Query `issue_labels` with filters {'issue_ref': 'gitlab_issue_016'}, check {'labels_include': 'security'}

- Query `issues` with filters {'issue_ref': 'gitlab_issue_016'}, check {'state': 'closed'}

- Query `issues` with filters {'issue_ref': 'gitlab_issue_010'}, check {'state': 'open'}

- Query `issues` with filters {'issue_ref': 'gitlab_issue_010'}, check {'assignee_ref': 'qa_bob'}

- Execution status: `not_executed`

**Validation status:**

- symbolic_grounded: True

- backend_grounded: False

- verifier_executed: False

- needs_backend_validation: True

---

## Task 7: task_0037

**Task description:**
In the shopping site, find the product whose category is electronics and whose product name is Circe's products. Write a 4-star review containing "comfortable".

**Target environment:** shopping

**Ability dimension:** Memory

**Difficulty:** L4

**Target entity:** shopping_product_037

**Ground truth:**

- `reviews` where {'product_ref': 'shopping_product_037', 'author_ref': 'current_user'} must satisfy {'exists': True, 'rating': 4, 'body_must_include': ['comfortable']}

**Verifier:**

- Query `reviews` with filters {'product_ref': 'shopping_product_037', 'author_ref': 'current_user'}, check {'exists': True, 'rating': 4, 'body_must_include': ['comfortable']}

- Execution status: `not_executed`

**Validation status:**

- symbolic_grounded: True

- backend_grounded: False

- verifier_executed: False

- needs_backend_validation: True

---

## Task 8: task_0083

**Task description:**
In GitLab, find the issue with IID 719; then find the issue whose state is open and whose labels is backend, ux, question. For the issue #719: Reopen the issue. For the issue #719: Assign the issue to qa_bob. For the issue with state open: Add a comment containing "requires security audit". For the issue with state open: Add the "documentation" label. For the issue with state open: Close the issue.

**Target environment:** gitlab

**Ability dimension:** Long-horizon

**Difficulty:** L4

**Target entity:** gitlab_issue_002

**Ground truth:**

- `issues` where {'issue_ref': 'gitlab_issue_002'} must satisfy {'state': 'open'}

- `issues` where {'issue_ref': 'gitlab_issue_002'} must satisfy {'assignee_ref': 'qa_bob'}

- `issue_comments` where {'issue_ref': 'gitlab_issue_034', 'author_ref': 'current_user'} must satisfy {'exists': True, 'body_must_include': ['requires security audit']}

- `issue_labels` where {'issue_ref': 'gitlab_issue_034'} must satisfy {'labels_include': 'documentation'}

- `issues` where {'issue_ref': 'gitlab_issue_034'} must satisfy {'state': 'closed'}

**Verifier:**

- Query `issues` with filters {'issue_ref': 'gitlab_issue_002'}, check {'state': 'open'}

- Query `issues` with filters {'issue_ref': 'gitlab_issue_002'}, check {'assignee_ref': 'qa_bob'}

- Query `issue_comments` with filters {'issue_ref': 'gitlab_issue_034', 'author_ref': 'current_user'}, check {'exists': True, 'body_must_include': ['requires security audit']}

- Query `issue_labels` with filters {'issue_ref': 'gitlab_issue_034'}, check {'labels_include': 'documentation'}

- Query `issues` with filters {'issue_ref': 'gitlab_issue_034'}, check {'state': 'closed'}

- Execution status: `not_executed`

**Validation status:**

- symbolic_grounded: True

- backend_grounded: False

- verifier_executed: False

- needs_backend_validation: True

---

## Task 9: task_0053

**Task description:**
In the forum, find the community whose post count is 4 and whose community name is movies and whose aliases is /f/movies. Create a post with a title containing "neighborhood safety" and a body containing "family friendly". Add a comment containing "definitely worth checking out".

**Target environment:** forum

**Ability dimension:** Memory

**Difficulty:** L5

**Target entity:** forum_community_006

**Ground truth:**

- `posts` where {'community_ref': 'forum_community_006', 'author_ref': 'current_user'} must satisfy {'exists': True, 'title_must_include': ['neighborhood safety'], 'body_must_include': ['family friendly']}

- `comments` where {'community_ref': 'forum_community_006', 'author_ref': 'current_user'} must satisfy {'exists': True}

**Verifier:**

- Query `posts` with filters {'community_ref': 'forum_community_006', 'author_ref': 'current_user'}, check {'exists': True, 'title_must_include': ['neighborhood safety'], 'body_must_include': ['family friendly']}

- Query `comments` with filters {'community_ref': 'forum_community_006', 'author_ref': 'current_user'}, check {'exists': True}

- Execution status: `not_executed`

**Validation status:**

- symbolic_grounded: True

- backend_grounded: False

- verifier_executed: False

- needs_backend_validation: True

---

## Task 10: task_0088

**Task description:**
In GitLab, find the issue whose state is open and whose labels is devops, frontend; then find the issue with IID 566 and whose state is open; then find the issue whose state is closed and whose labels is enhancement, help needed, documentation. For the issue with state open: Add a comment containing "confirmed as duplicate". For the issue with state open: Assign the issue to ericwbailey. For the issue with state open: Close the issue. For the issue #566: Add a comment containing "triaged for backend team". For the issue #566: Assign the issue to byteblaze. For the issue #566: Close the issue. For the issue with state closed: Reopen the issue. For the issue with state closed: Add a comment containing "needs retry logic". For the issue with state closed: Add the "high-priority" label.

**Target environment:** gitlab

**Ability dimension:** Long-horizon

**Difficulty:** L5

**Target entity:** gitlab_issue_021

**Ground truth:**

- `issue_comments` where {'issue_ref': 'gitlab_issue_021', 'author_ref': 'current_user'} must satisfy {'exists': True, 'body_must_include': ['confirmed as duplicate']}

- `issues` where {'issue_ref': 'gitlab_issue_021'} must satisfy {'assignee_ref': 'ericwbailey'}

- `issues` where {'issue_ref': 'gitlab_issue_021'} must satisfy {'state': 'closed'}

- `issue_comments` where {'issue_ref': 'gitlab_issue_001', 'author_ref': 'current_user'} must satisfy {'exists': True, 'body_must_include': ['triaged for backend team']}

- `issues` where {'issue_ref': 'gitlab_issue_001'} must satisfy {'assignee_ref': 'byteblaze'}

- `issues` where {'issue_ref': 'gitlab_issue_001'} must satisfy {'state': 'closed'}

- `issues` where {'issue_ref': 'gitlab_issue_033'} must satisfy {'state': 'open'}

- `issue_comments` where {'issue_ref': 'gitlab_issue_033', 'author_ref': 'current_user'} must satisfy {'exists': True, 'body_must_include': ['needs retry logic']}

- `issue_labels` where {'issue_ref': 'gitlab_issue_033'} must satisfy {'labels_include': 'high-priority'}

**Verifier:**

- Query `issue_comments` with filters {'issue_ref': 'gitlab_issue_021', 'author_ref': 'current_user'}, check {'exists': True, 'body_must_include': ['confirmed as duplicate']}

- Query `issues` with filters {'issue_ref': 'gitlab_issue_021'}, check {'assignee_ref': 'ericwbailey'}

- Query `issues` with filters {'issue_ref': 'gitlab_issue_021'}, check {'state': 'closed'}

- Query `issue_comments` with filters {'issue_ref': 'gitlab_issue_001', 'author_ref': 'current_user'}, check {'exists': True, 'body_must_include': ['triaged for backend team']}

- Query `issues` with filters {'issue_ref': 'gitlab_issue_001'}, check {'assignee_ref': 'byteblaze'}

- Query `issues` with filters {'issue_ref': 'gitlab_issue_001'}, check {'state': 'closed'}

- Query `issues` with filters {'issue_ref': 'gitlab_issue_033'}, check {'state': 'open'}

- Query `issue_comments` with filters {'issue_ref': 'gitlab_issue_033', 'author_ref': 'current_user'}, check {'exists': True, 'body_must_include': ['needs retry logic']}

- Query `issue_labels` with filters {'issue_ref': 'gitlab_issue_033'}, check {'labels_include': 'high-priority'}

- Execution status: `not_executed`

**Validation status:**

- symbolic_grounded: True

- backend_grounded: False

- verifier_executed: False

- needs_backend_validation: True

---
