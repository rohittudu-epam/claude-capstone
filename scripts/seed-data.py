#!/usr/bin/env python3
"""Seed the database with sample notes, tags, and links for testing and demonstration.

Usage:
    python scripts/seed-data.py --email user@example.com

This creates a demo user (if it doesn't exist) and populates their account with:
- 15+ sample notes across various topics
- Tags for organization
- Accepted links between related notes
- Suggestions for potential links

Notes cover topics like: Python, JavaScript, databases, DevOps, web development,
machine learning, and personal knowledge management.
"""

import argparse
import sys
from pathlib import Path
from uuid import UUID

# Add backend to path
BACKEND_DIR = Path(__file__).parent.parent / "backend"
sys.path.insert(0, str(BACKEND_DIR))

from sqlalchemy.orm import Session

from shared.db import get_sessionmaker
from shared.models import AcceptedLink, Note, Tag, User

SAMPLE_NOTES = [
    {
        "title": "Python Type Hints Best Practices",
        "body": """# Python Type Hints Best Practices

Type hints improve code readability and catch bugs early.

## Key Principles
- Use `typing` module for complex types
- Prefer `list[str]` over `List[str]` in Python 3.9+
- Use `Optional[T]` for values that might be None
- Leverage `TypedDict` for structured dictionaries

## Example
```python
from typing import Optional

def greet(name: str, formal: bool = False) -> str:
    prefix = "Hello" if not formal else "Good day"
    return f"{prefix}, {name}!"
```

## Tools
- mypy: static type checker
- pyright: Microsoft's type checker
- pydantic: runtime validation with types

Type hints are documentation that the machine can verify.
""",
        "tags": ["python", "typing", "best-practices"],
    },
    {
        "title": "JavaScript Async Patterns",
        "body": """# JavaScript Async Patterns

Modern JavaScript provides multiple ways to handle asynchronous operations.

## Three Approaches

### 1. Callbacks (Legacy)
```javascript
fs.readFile('file.txt', (err, data) => {
  if (err) throw err;
  console.log(data);
});
```

### 2. Promises
```javascript
fetch('/api/data')
  .then(response => response.json())
  .then(data => console.log(data))
  .catch(error => console.error(error));
```

### 3. Async/Await (Preferred)
```javascript
async function getData() {
  try {
    const response = await fetch('/api/data');
    const data = await response.json();
    return data;
  } catch (error) {
    console.error(error);
  }
}
```

Async/await makes asynchronous code read like synchronous code.
""",
        "tags": ["javascript", "async", "best-practices"],
    },
    {
        "title": "PostgreSQL Indexing Strategies",
        "body": """# PostgreSQL Indexing Strategies

Indexes speed up queries but slow down writes. Choose wisely.

## Index Types

**B-tree (default)**: General purpose, works for equality and range queries
```sql
CREATE INDEX idx_users_email ON users(email);
```

**Hash**: Equality only, slightly faster than B-tree
```sql
CREATE INDEX idx_products_sku ON products USING HASH (sku);
```

**GIN**: Full-text search, JSONB, arrays
```sql
CREATE INDEX idx_notes_search ON notes USING GIN (search_vector);
```

**GiST**: Geographic data, range types
```sql
CREATE INDEX idx_locations_point ON locations USING GIST (point);
```

## Best Practices
- Index foreign keys
- Index columns in WHERE and JOIN clauses
- Avoid over-indexing (each index has overhead)
- Use `EXPLAIN ANALYZE` to verify query plans
- Consider partial indexes for filtered queries

Monitor index usage with `pg_stat_user_indexes`.
""",
        "tags": ["postgresql", "database", "performance"],
    },
    {
        "title": "Docker Multi-Stage Builds",
        "body": """# Docker Multi-Stage Builds

Multi-stage builds create smaller, more secure images.

## Problem
Traditional Dockerfiles include build tools in the final image, bloating size.

## Solution
Use multiple FROM statements. Copy only the artifacts you need.

## Example
```dockerfile
# Stage 1: Build
FROM node:18-alpine AS builder
WORKDIR /app
COPY package*.json ./
RUN npm ci --only=production
COPY . .
RUN npm run build

# Stage 2: Production
FROM node:18-alpine
WORKDIR /app
COPY --from=builder /app/dist ./dist
COPY --from=builder /app/node_modules ./node_modules
EXPOSE 3000
CMD ["node", "dist/main.js"]
```

## Benefits
- Smaller images (10x reduction is common)
- No build tools in production
- Cleaner layer caching
- Separation of concerns

The final image contains only runtime dependencies.
""",
        "tags": ["docker", "devops", "deployment"],
    },
    {
        "title": "REST API Design Principles",
        "body": """# REST API Design Principles

Good API design is about consistency and predictability.

## Resource Naming
- Use nouns, not verbs: `/users` not `/getUsers`
- Plural names: `/notes`, `/tags`
- Nested resources: `/users/{id}/notes`
- Keep URLs lowercase with hyphens: `/link-suggestions`

## HTTP Methods
- `GET`: Read, idempotent, no side effects
- `POST`: Create, not idempotent
- `PUT`: Replace entire resource
- `PATCH`: Partial update
- `DELETE`: Remove resource

## Status Codes
- 200 OK: Success with response body
- 201 Created: Resource created
- 204 No Content: Success, no body
- 400 Bad Request: Client error
- 401 Unauthorized: Authentication required
- 404 Not Found: Resource doesn't exist
- 500 Internal Server Error: Server error

## Response Format
```json
{
  "data": [...],
  "pagination": {
    "total": 100,
    "limit": 20,
    "offset": 0
  }
}
```

Consistency across endpoints reduces cognitive load.
""",
        "tags": ["api", "rest", "web-development"],
    },
    {
        "title": "Git Rebase vs Merge",
        "body": """# Git Rebase vs Merge

Two ways to integrate changes, each with trade-offs.

## Merge
Preserves history exactly as it happened.

```bash
git checkout main
git merge feature-branch
```

**Pros:**
- True history preservation
- Simple, safe
- No chance of rewriting shared history

**Cons:**
- Creates merge commits
- History can become cluttered

## Rebase
Rewrites history for a linear timeline.

```bash
git checkout feature-branch
git rebase main
```

**Pros:**
- Clean, linear history
- Easier to follow
- Bisect-friendly

**Cons:**
- Rewrites commits (never rebase shared branches)
- Loses context of when work was done

## Golden Rule
Never rebase commits that have been pushed to a shared branch.

Use merge for public branches, rebase for local cleanup.
""",
        "tags": ["git", "version-control", "best-practices"],
    },
    {
        "title": "CSS Grid vs Flexbox",
        "body": """# CSS Grid vs Flexbox

Both are powerful layout tools. Use the right one for the job.

## Flexbox: One-Dimensional Layouts
Best for components and smaller-scale layouts.

```css
.container {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 1rem;
}
```

**Use for:**
- Navigation bars
- Card layouts (single row/column)
- Centering content
- Distributing space between items

## Grid: Two-Dimensional Layouts
Best for page-level layouts.

```css
.layout {
  display: grid;
  grid-template-columns: 200px 1fr;
  grid-template-rows: auto 1fr auto;
  gap: 1rem;
}
```

**Use for:**
- Page layouts (header, sidebar, main, footer)
- Photo galleries
- Forms with aligned labels
- Any layout with rows AND columns

## Rule of Thumb
- Flexbox: content out (let content dictate size)
- Grid: layout in (define structure first)

They work great together! Use grid for the page, flexbox for components.
""",
        "tags": ["css", "web-development", "layout"],
    },
    {
        "title": "Redis Caching Strategies",
        "body": """# Redis Caching Strategies

Redis is an in-memory data store perfect for caching.

## Cache Patterns

### 1. Cache-Aside (Lazy Loading)
Application manages cache explicitly.

```python
def get_user(user_id):
    # Try cache first
    user = redis.get(f"user:{user_id}")
    if user:
        return json.loads(user)

    # Cache miss: load from database
    user = db.query(User).get(user_id)
    redis.setex(f"user:{user_id}", 3600, json.dumps(user))
    return user
```

### 2. Write-Through
Update cache on every write.

### 3. Write-Behind (Write-Back)
Update cache immediately, persist to DB asynchronously.

## Best Practices
- Set TTL (Time To Live) to prevent stale data
- Use namespaced keys: `user:123`, `post:456`
- Cache expensive queries, not everything
- Monitor hit rate: `INFO stats` shows hits/misses
- Consider cache stampede: use locking for hot keys

## When to Use Redis
- Session storage
- Real-time leaderboards
- Rate limiting
- Message queues (pub/sub)
- Temporary data with TTL

Don't use Redis as your primary database.
""",
        "tags": ["redis", "caching", "performance", "database"],
    },
    {
        "title": "Machine Learning Model Evaluation",
        "body": """# Machine Learning Model Evaluation

Accuracy isn't everything. Choose the right metric for your problem.

## Classification Metrics

**Accuracy**: (TP + TN) / Total
Good for balanced datasets, misleading for imbalanced.

**Precision**: TP / (TP + FP)
"Of items we predicted positive, how many were correct?"

**Recall (Sensitivity)**: TP / (TP + FN)
"Of actual positives, how many did we find?"

**F1 Score**: Harmonic mean of precision and recall
Balances both when you need a single metric.

## When to Use What

**High Recall**: Cancer detection (minimize false negatives)
**High Precision**: Spam filtering (minimize false positives)
**F1**: General-purpose when classes are imbalanced

## Regression Metrics
- MAE (Mean Absolute Error): Average absolute difference
- RMSE (Root Mean Square Error): Penalizes large errors more
- R² (R-Squared): How much variance does the model explain?

## Cross-Validation
Never evaluate on training data! Use k-fold cross-validation.

```python
from sklearn.model_selection import cross_val_score
scores = cross_val_score(model, X, y, cv=5)
print(f"Accuracy: {scores.mean():.2f} (+/- {scores.std():.2f})")
```

The metric should match your business goal.
""",
        "tags": ["machine-learning", "python", "data-science"],
    },
    {
        "title": "Zettelkasten Note-Taking Method",
        "body": """# Zettelkasten Note-Taking Method

A proven system for building a knowledge network.

## Core Principles

### 1. Atomic Notes
Each note contains one idea in your own words.

### 2. Link Heavily
Connect related ideas. The connections are as important as the notes.

### 3. Use Your Own Words
Forcing yourself to rephrase ensures understanding.

### 4. Add Context
Why is this note important? How does it relate to your work?

## Process

1. **Capture**: Write fleeting notes as ideas occur
2. **Process**: Convert to permanent notes (atomic, clear)
3. **Link**: Connect to existing notes
4. **Index**: Add to entry points (structure notes)

## Benefits
- Knowledge compounds over time
- Serendipitous discoveries through links
- Writing forces thinking
- Easy to find information later

## Digital Implementation
Tools like Obsidian, Roam, or LinkNote work well.

The goal isn't note storage—it's building a conversation with your past self.
""",
        "tags": ["knowledge-management", "productivity", "note-taking"],
    },
    {
        "title": "Kubernetes Pod Lifecycle",
        "body": """# Kubernetes Pod Lifecycle

Understanding pod states helps with debugging.

## Pod Phases

**Pending**: Scheduler hasn't placed the pod yet
- Check: node resources, affinity rules

**Running**: Pod bound to node, containers started
- At least one container still running

**Succeeded**: All containers terminated successfully
- Used for Jobs

**Failed**: At least one container terminated with error
- Check logs: `kubectl logs <pod>`

**Unknown**: Can't get pod state (node communication issue)

## Container States

**Waiting**: Not running yet (pulling image, init containers)

**Running**: Container executing

**Terminated**: Execution finished

## Lifecycle Hooks

**postStart**: Runs after container starts
```yaml
lifecycle:
  postStart:
    exec:
      command: ["/bin/sh", "-c", "echo Started > /tmp/started"]
```

**preStop**: Runs before container stops
Used for graceful shutdown.

## Restart Policies
- `Always`: Default, restarts on any exit
- `OnFailure`: Only on non-zero exit
- `Never`: Don't restart

Understanding the lifecycle prevents surprises in production.
""",
        "tags": ["kubernetes", "devops", "containers"],
    },
    {
        "title": "SQL Query Optimization Techniques",
        "body": """# SQL Query Optimization Techniques

Slow queries kill application performance.

## 1. Use EXPLAIN
Always start with query plan analysis.

```sql
EXPLAIN ANALYZE
SELECT * FROM orders
WHERE customer_id = 123
ORDER BY created_at DESC
LIMIT 10;
```

Look for:
- Sequential scans (usually bad)
- Index scans (good)
- High cost numbers

## 2. Index Foreign Keys
```sql
CREATE INDEX idx_orders_customer_id ON orders(customer_id);
```

## 3. Avoid SELECT *
Only fetch columns you need. Reduces I/O.

```sql
-- Bad
SELECT * FROM users WHERE active = true;

-- Good
SELECT id, email, name FROM users WHERE active = true;
```

## 4. Use LIMIT
Especially for pagination and debugging.

## 5. Batch Operations
```sql
-- Bad: 1000 separate INSERTs
-- Good: One INSERT with 1000 rows
INSERT INTO items (name, price) VALUES
  ('Item 1', 10.00),
  ('Item 2', 15.00),
  ...
```

## 6. JOINs vs Subqueries
JOINs are usually faster than correlated subqueries.

## 7. Monitor Query Performance
- Enable slow query log
- Track query execution time in production
- Set up alerts for degradation

The fastest query is the one you don't run.
""",
        "tags": ["sql", "database", "performance"],
    },
    {
        "title": "GraphQL vs REST",
        "body": """# GraphQL vs REST

Two approaches to API design, each with strengths.

## REST Strengths
- Simple, well-understood
- Easy to cache (HTTP caching)
- Tooling everywhere
- HTTP status codes for semantics

## GraphQL Strengths
- Fetch exactly what you need
- Single endpoint
- Type system and introspection
- Reduced over-fetching and under-fetching

## When to Use REST
- Simple CRUD operations
- Heavy caching requirements
- Public APIs (easier for consumers to learn)
- Small team or project

## When to Use GraphQL
- Complex data requirements
- Multiple clients (web, mobile, different needs)
- Rapidly evolving schema
- Microservices aggregation

## Example GraphQL Query
```graphql
query {
  user(id: "123") {
    name
    email
    posts(limit: 5) {
      title
      createdAt
    }
  }
}
```

Same in REST would require multiple round trips.

## Caveats
GraphQL adds complexity:
- Need to handle N+1 queries (use DataLoader)
- Harder to cache
- More setup overhead

Choose based on your actual needs, not hype.
""",
        "tags": ["graphql", "rest", "api", "web-development"],
    },
    {
        "title": "Microservices Communication Patterns",
        "body": """# Microservices Communication Patterns

How services talk matters as much as what they do.

## Synchronous (Request-Response)

### HTTP/REST
Pros: Simple, familiar, stateless
Cons: Coupling, cascading failures

### gRPC
Pros: Fast, type-safe, bidirectional streaming
Cons: Steeper learning curve

**When to use:** Read operations, immediate response needed

## Asynchronous (Event-Driven)

### Message Queue (RabbitMQ, SQS)
Work queue pattern: task distribution

### Publish-Subscribe (Kafka, Redis Pub/Sub)
Event streaming: multiple consumers

**When to use:** Write operations, eventual consistency acceptable

## Patterns

### API Gateway
Single entry point, routes to services

### Service Mesh
Handles cross-cutting concerns (retry, circuit breaking)

### Saga Pattern
Distributed transactions via choreography or orchestration

## Best Practices
- Design for failure (circuit breakers, timeouts)
- Use correlation IDs for tracing
- Version your APIs
- Monitor service health
- Prefer async where possible (better decoupling)

The goal is loose coupling, not just small services.
""",
        "tags": ["microservices", "architecture", "distributed-systems"],
    },
    {
        "title": "TypeScript Utility Types",
        "body": """# TypeScript Utility Types

Built-in types that manipulate other types.

## Partial<T>
Makes all properties optional.

```typescript
interface User {
  id: string;
  name: string;
  email: string;
}

// Update function doesn't require all fields
function updateUser(id: string, updates: Partial<User>) {
  // ...
}
```

## Pick<T, K>
Create type with subset of properties.

```typescript
type UserPreview = Pick<User, 'id' | 'name'>;
// { id: string; name: string; }
```

## Omit<T, K>
Create type excluding properties.

```typescript
type UserWithoutEmail = Omit<User, 'email'>;
// { id: string; name: string; }
```

## Record<K, T>
Object type with specified keys and value type.

```typescript
type PageInfo = Record<string, number>;
// { [key: string]: number }
```

## ReturnType<T>
Extract return type of function.

```typescript
function getUser() {
  return { id: '1', name: 'Alice' };
}

type User = ReturnType<typeof getUser>;
// { id: string; name: string; }
```

## Awaited<T>
Unwrap Promise type.

```typescript
type Response = Awaited<Promise<string>>;
// string
```

These save time and make code more maintainable.
""",
        "tags": ["typescript", "javascript", "type-system"],
    },
]

# Links to create between related notes (by title pairs)
SAMPLE_LINKS = [
    ("Python Type Hints Best Practices", "JavaScript Async Patterns"),  # Both about language features
    ("PostgreSQL Indexing Strategies", "SQL Query Optimization Techniques"),  # Database performance
    ("PostgreSQL Indexing Strategies", "Redis Caching Strategies"),  # Database topics
    ("Docker Multi-Stage Builds", "Kubernetes Pod Lifecycle"),  # Container topics
    ("REST API Design Principles", "GraphQL vs REST"),  # API design
    ("Git Rebase vs Merge", "Docker Multi-Stage Builds"),  # DevOps workflows
    ("Machine Learning Model Evaluation", "Python Type Hints Best Practices"),  # Python topics
    ("Zettelkasten Note-Taking Method", "Microservices Communication Patterns"),  # Knowledge organization
    ("TypeScript Utility Types", "JavaScript Async Patterns"),  # TypeScript/JavaScript
    ("Kubernetes Pod Lifecycle", "Microservices Communication Patterns"),  # Distributed systems
]


def create_user(session: Session, email: str, password: str = "demo123456") -> User:
    """Create or get demo user."""
    from shared.auth import hash_password

    user = session.query(User).filter(User.email == email).first()
    if user:
        print(f"✓ User {email} already exists")
        return user

    user = User(email=email, password_hash=hash_password(password))
    session.add(user)
    session.commit()
    print(f"✓ Created user: {email}")
    return user


def create_sample_notes(session: Session, user: User) -> dict[str, UUID]:
    """Create sample notes and tags. Returns dict of note_title -> note_id."""
    note_ids = {}

    for note_data in SAMPLE_NOTES:
        # Create note
        note = Note(
            owner_id=user.id,
            title=note_data["title"],
            body=note_data["body"],
        )
        session.add(note)
        session.flush()  # Get note ID
        note_ids[note_data["title"]] = note.id

        # Create/get tags
        for tag_name in note_data["tags"]:
            tag = session.query(Tag).filter(Tag.owner_id == user.id, Tag.name == tag_name).first()
            if not tag:
                tag = Tag(owner_id=user.id, name=tag_name)
                session.add(tag)
                session.flush()

            note.tags.append(tag)

        print(f"✓ Created note: {note_data['title']} ({len(note_data['tags'])} tags)")

    session.commit()
    return note_ids


def create_sample_links(session: Session, user: User, note_ids: dict[str, UUID]) -> None:
    """Create accepted links between related notes."""
    created = 0

    for source_title, target_title in SAMPLE_LINKS:
        source_id = note_ids.get(source_title)
        target_id = note_ids.get(target_title)

        if not source_id or not target_id:
            continue

        # Ensure canonical order (source < target)
        if source_id > target_id:
            source_id, target_id = target_id, source_id

        # Check if link already exists
        existing = (
            session.query(AcceptedLink)
            .filter(AcceptedLink.source_note_id == source_id, AcceptedLink.target_note_id == target_id)
            .first()
        )

        if not existing:
            link = AcceptedLink(
                owner_id=user.id,
                source_note_id=source_id,
                target_note_id=target_id,
            )
            session.add(link)
            created += 1

    session.commit()
    print(f"✓ Created {created} links between notes")


def main():
    parser = argparse.ArgumentParser(description="Seed database with sample notes and links")
    parser.add_argument(
        "--email",
        default="demo@example.com",
        help="Email for demo user (default: demo@example.com)",
    )
    parser.add_argument(
        "--password",
        default="demo123456",
        help="Password for demo user (default: demo123456)",
    )
    args = parser.parse_args()

    print(f"\n📝 Seeding database with sample data for {args.email}\n")

    SessionLocal = get_sessionmaker()
    session = SessionLocal()

    try:
        # Create user
        user = create_user(session, args.email, args.password)

        # Create notes and tags
        note_ids = create_sample_notes(session, user)

        # Create links
        create_sample_links(session, user, note_ids)

        print(f"\n✅ Successfully seeded {len(note_ids)} notes with tags and links!")
        print(f"   Login at http://localhost:3000 with:")
        print(f"   Email: {args.email}")
        print(f"   Password: {args.password}")
        print()

    except Exception as e:
        session.rollback()
        print(f"\n❌ Error seeding database: {e}")
        raise
    finally:
        session.close()


if __name__ == "__main__":
    main()
