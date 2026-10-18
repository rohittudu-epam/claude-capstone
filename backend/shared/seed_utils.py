"""Shared utilities for database seeding.

This module provides idempotent seeding functions that can be used both from
the CLI script and from the Docker compose seed service.
"""

from datetime import UTC, datetime, timedelta
from typing import Any, cast
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from shared.models import AcceptedLink, Note, Suggestion, Tag, User
from shared.security import hash_password

# Sample notes with realistic content across multiple topic clusters
SAMPLE_NOTES = [
    # Cluster 1: AI and Machine Learning (5 notes)
    {
        "title": "Understanding Artificial Intelligence",
        "body": """# Understanding Artificial Intelligence

AI is the simulation of human intelligence by machines, particularly computer systems.

## Types of AI

**Narrow AI (Weak AI)**: Designed for specific tasks
- Spam filters
- Recommendation systems
- Voice assistants like Siri and Alexa

**General AI (Strong AI)**: Human-level intelligence across all domains
- Still theoretical
- Would match human cognitive abilities

**Superintelligence**: Surpasses human intelligence
- Hypothetical future state

## Key Technologies

- **Machine Learning**: Systems learn from data
- **Deep Learning**: Neural networks with many layers
- **Natural Language Processing**: Understanding human language
- **Computer Vision**: Interpreting visual information

## Current Applications

- Healthcare diagnostics
- Autonomous vehicles
- Financial fraud detection
- Customer service chatbots
- Content recommendation

AI is not magic—it's math, statistics, and massive computation.
""",
        "tags": ["ai", "machine-learning", "automation"],
        "days_ago": 2,
    },
    {
        "title": "Machine Learning in Automation",
        "body": """# Machine Learning in Automation

ML enables systems to learn and improve from experience without explicit programming.

## Automation Use Cases

### Predictive Maintenance
Train models on sensor data to predict equipment failures before they happen.

```python
from sklearn.ensemble import RandomForestClassifier

# Train on historical failure data
model = RandomForestClassifier()
model.fit(sensor_data, failure_labels)

# Predict upcoming failures
predictions = model.predict(new_sensor_readings)
```

### Document Processing
Automate data extraction from invoices, receipts, forms.

### Quality Control
Computer vision detects manufacturing defects faster than human inspection.

### Customer Support
Chatbots handle routine queries, escalate complex issues to humans.

## Benefits

- **24/7 Operation**: No downtime
- **Consistency**: Same quality every time
- **Scalability**: Handle increasing volume
- **Cost Reduction**: Lower labor costs

## Challenges

- Requires quality training data
- Model drift over time
- Explainability (black box problem)
- Initial setup cost

Automation amplifies human capability rather than replacing it.
""",
        "tags": ["machine-learning", "automation", "python"],
        "days_ago": 5,
    },
    {
        "title": "Neural Networks Basics",
        "body": """# Neural Networks Basics

Neural networks are computing systems inspired by biological neural networks.

## Architecture

**Input Layer**: Receives raw data
**Hidden Layers**: Process information
**Output Layer**: Produces final result

Each connection has a **weight** that adjusts during training.

## How They Learn

1. **Forward Pass**: Data flows through network
2. **Loss Calculation**: Compare output to expected result
3. **Backpropagation**: Adjust weights to reduce error
4. **Repeat**: Thousands or millions of iterations

## Example: Simple Classification

```python
import tensorflow as tf

model = tf.keras.Sequential([
    tf.keras.layers.Dense(128, activation='relu', input_shape=(784,)),
    tf.keras.layers.Dropout(0.2),
    tf.keras.layers.Dense(10, activation='softmax')
])

model.compile(optimizer='adam',
              loss='sparse_categorical_crossentropy',
              metrics=['accuracy'])

model.fit(train_images, train_labels, epochs=5)
```

## Activation Functions

- **ReLU**: Most common, simple
- **Sigmoid**: Output between 0 and 1
- **Tanh**: Output between -1 and 1
- **Softmax**: Probability distribution for classification

## Deep Learning

Networks with many hidden layers ("deep" networks) can learn hierarchical features:
- Early layers detect edges
- Middle layers detect shapes
- Deep layers detect complex patterns

The "magic" is just calculus and linear algebra at scale.
""",
        "tags": ["ai", "machine-learning", "deep-learning"],
        "days_ago": 8,
    },
    {
        "title": "Prompt Engineering Tips",
        "body": """# Prompt Engineering Tips

Get better results from Large Language Models with effective prompts.

## Core Principles

### 1. Be Specific
Bad: "Write about dogs"
Good: "Write a 200-word blog intro about golden retriever training for first-time owners"

### 2. Provide Context
Include relevant background information the model needs.

### 3. Use Examples (Few-Shot Learning)
```
Extract names from these sentences:

Input: "John went to the store with Mary."
Output: ["John", "Mary"]

Input: "The conference was attended by Dr. Smith and Prof. Johnson."
Output: ["Dr. Smith", "Prof. Johnson"]

Input: "Alice and Bob collaborated on the project."
Output:
```

### 4. Break Down Complex Tasks
Chain multiple prompts rather than one mega-prompt.

### 5. Specify Format
"Respond in JSON format with keys: title, summary, tags"

## Advanced Techniques

**Chain of Thought**: Ask the model to show its reasoning
"Let's think step-by-step..."

**Role Prompting**: "You are an expert Python developer reviewing code..."

**Temperature Control**: Lower for factual, higher for creative

## Testing and Iteration

- Test on diverse inputs
- Refine based on failures
- Version your prompts
- Measure success metrics

Prompting is programming in natural language.
""",
        "tags": ["ai", "llm", "prompt-engineering"],
        "days_ago": 12,
    },
    {
        "title": "AI Ethics and Bias",
        "body": """# AI Ethics and Bias

AI systems reflect the data they're trained on—including societal biases.

## Types of Bias

**Data Bias**: Training data doesn't represent reality
- Historical hiring data favoring one gender
- Medical data primarily from one demographic

**Algorithmic Bias**: Model design amplifies certain patterns
- Feedback loops in recommendation systems

**Deployment Bias**: Context of use differs from training
- Facial recognition trained on limited ethnicities

## Real-World Examples

- Resume screening tools discriminating by name
- Predictive policing reinforcing over-policing
- Healthcare algorithms under-serving minorities
- Credit scoring based on biased historical data

## Mitigation Strategies

1. **Diverse Training Data**: Ensure representation
2. **Bias Testing**: Evaluate across demographics
3. **Explainability**: Understand model decisions
4. **Human Oversight**: Keep humans in the loop
5. **Regular Audits**: Monitor deployed systems

## Fairness Definitions

- **Demographic Parity**: Equal positive rate across groups
- **Equal Opportunity**: Equal true positive rate
- **Predictive Parity**: Equal precision across groups

These definitions can conflict—trade-offs are necessary.

> "All models are wrong, but some are useful. Some are also harmful."

Building ethical AI requires vigilance at every stage.
""",
        "tags": ["ai", "ethics", "bias"],
        "days_ago": 15,
    },
    # Cluster 2: Software Testing (5 notes)
    {
        "title": "AI-Powered Software Testing",
        "body": """# AI-Powered Software Testing

AI is transforming how we test software, from test generation to bug prediction.

## Use Cases

### Automated Test Generation
AI analyzes code and generates test cases automatically.

```python
# Tool example: Facebook's Sapienz for Android
# Generates UI tests through intelligent exploration
```

### Visual Testing
Computer vision detects UI regressions humans might miss.

### Intelligent Test Prioritization
ML predicts which tests are most likely to catch bugs given recent code changes.

### Flaky Test Detection
Identify tests with inconsistent results and suggest fixes.

### Bug Prediction
Models predict which code changes are most likely to introduce bugs.

## Benefits

- **Faster Test Creation**: Automated generation saves time
- **Better Coverage**: AI explores edge cases humans overlook
- **Reduced Maintenance**: Self-healing tests adapt to UI changes
- **Smart Resource Use**: Run high-risk tests first

## Limitations

- Requires significant training data
- May miss domain-specific logic errors
- Initial setup and tuning needed
- Black-box nature makes debugging harder

## Tools

- **Testim**: AI-powered test automation
- **Applitools**: Visual AI testing
- **Mabl**: Intelligent test automation
- **Test.ai**: Mobile test automation

AI complements human testers; it doesn't replace them.
""",
        "tags": ["software-testing", "ai", "automation", "qa"],
        "days_ago": 3,
    },
    {
        "title": "Selenium vs Playwright",
        "body": """# Selenium vs Playwright

Two popular browser automation frameworks with different strengths.

## Selenium

**Pros:**
- Mature ecosystem (since 2004)
- Supports more browsers (including older ones)
- Huge community
- Language support (Python, Java, C#, Ruby, JS)

**Cons:**
- Slower execution
- More flaky tests
- Verbose API
- Manual waits often needed

```python
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait

driver = webdriver.Chrome()
driver.get("https://example.com")
element = WebDriverWait(driver, 10).until(
    lambda d: d.find_element(By.ID, "myElement")
)
```

## Playwright

**Pros:**
- Modern, fast, reliable
- Auto-waits for elements
- Better debugging (trace viewer)
- Network interception built-in
- Cross-browser out of the box

**Cons:**
- Newer (since 2020)
- Smaller community
- Breaking changes more frequent

```python
from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    browser = p.chromium.launch()
    page = browser.new_page()
    page.goto("https://example.com")
    page.click("#myElement")  # Auto-waits!
```

## When to Use What

**Choose Selenium if:**
- You need to support old browsers
- Your team already knows it
- You're using languages Playwright doesn't support well

**Choose Playwright if:**
- Starting a new project
- Speed and reliability matter
- You want modern debugging tools
- You're testing modern web apps

Both are excellent—Playwright is generally better for new projects.
""",
        "tags": ["software-testing", "automation", "selenium", "playwright"],
        "days_ago": 7,
    },
    {
        "title": "Writing Reliable Test Cases",
        "body": """# Writing Reliable Test Cases

Flaky tests waste time and erode confidence. Write tests that pass consistently.

## Principles

### 1. Isolation
Each test should run independently, in any order.

```python
# Bad: Depends on previous test
def test_user_exists():
    assert get_user(1) is not None

def test_delete_user():
    delete_user(1)

# Good: Each test sets up its own data
def test_delete_user():
    user = create_test_user()
    delete_user(user.id)
    assert get_user(user.id) is None
```

### 2. Determinism
Same input = same output, every time.

**Avoid:**
- Random data (use fixed seeds)
- Current time (inject time as dependency)
- External services (use mocks/stubs)
- File system state (use temp directories)

### 3. Speed
Slow tests discourage running them.

- Unit tests: < 100ms each
- Integration tests: < 5 seconds
- E2E tests: < 30 seconds

### 4. Clarity
Test names should describe what they verify.

```python
# Bad
def test_user():
    ...

# Good
def test_user_creation_fails_with_duplicate_email():
    ...
```

## The AAA Pattern

**Arrange**: Set up test data
**Act**: Perform the action
**Assert**: Verify the outcome

```python
def test_shopping_cart_total():
    # Arrange
    cart = ShoppingCart()
    cart.add_item(Item("Book", price=10.00))
    cart.add_item(Item("Pen", price=2.50))

    # Act
    total = cart.calculate_total()

    # Assert
    assert total == 12.50
```

## Dealing with Flakiness

1. **Identify**: Tag flaky tests
2. **Investigate**: Add logging, reduce concurrency
3. **Fix**: Address root cause
4. **Quarantine**: Disable if can't fix quickly

A flaky test is worse than no test.
""",
        "tags": ["software-testing", "best-practices", "qa"],
        "days_ago": 10,
    },
    {
        "title": "API Testing with REST Assured",
        "body": """# API Testing with REST Assured

REST Assured is a Java DSL for testing REST APIs with readable syntax.

## Basic Example

```java
import static io.restassured.RestAssured.*;
import static org.hamcrest.Matchers.*;

@Test
public void testGetUser() {
    given()
        .baseUri("https://api.example.com")
        .header("Authorization", "Bearer token123")
    .when()
        .get("/users/1")
    .then()
        .statusCode(200)
        .body("name", equalTo("John Doe"))
        .body("email", equalTo("john@example.com"));
}
```

## Request Specifications

Reuse common config:

```java
RequestSpecification requestSpec = new RequestSpecBuilder()
    .setBaseUri("https://api.example.com")
    .addHeader("Authorization", "Bearer token123")
    .setContentType(ContentType.JSON)
    .build();

given()
    .spec(requestSpec)
.when()
    .get("/users")
.then()
    .statusCode(200);
```

## Testing POST Requests

```java
User user = new User("Alice", "alice@example.com");

given()
    .contentType(ContentType.JSON)
    .body(user)
.when()
    .post("/users")
.then()
    .statusCode(201)
    .body("id", notNullValue());
```

## Response Extraction

```java
String userId = given()
    .when()
        .post("/users", user)
    .then()
        .statusCode(201)
        .extract()
        .path("id");

// Use userId in subsequent tests
```

## Schema Validation

```java
given()
    .when()
        .get("/users")
    .then()
        .body(matchesJsonSchemaInClasspath("user-schema.json"));
```

## Best Practices

- Use `RequestSpecification` for common setup
- Extract response data for dependent tests
- Validate schema, not just values
- Test error cases (400, 401, 404, 500)
- Clean up test data (DELETE after CREATE)

REST Assured makes API testing feel natural in Java.
""",
        "tags": ["software-testing", "api", "java", "rest"],
        "days_ago": 14,
    },
    {
        "title": "Test Pyramid Strategy",
        "body": """# Test Pyramid Strategy

Balance your test suite for speed, coverage, and maintainability.

## The Pyramid

```
       /\\
      /E2E\\         10% - Slow, brittle, high value
     /------\\
    /Integration\\   20% - Medium speed, test interactions
   /------------\\
  /    Unit      \\  70% - Fast, stable, test logic
 /________________\\
```

## Unit Tests (Base)

**What**: Test individual functions/methods in isolation
**Speed**: Milliseconds
**Count**: Hundreds or thousands

```python
def test_calculate_discount():
    assert calculate_discount(100, 0.1) == 90
    assert calculate_discount(50, 0.2) == 40
```

**Focus**: Business logic, edge cases, error handling

## Integration Tests (Middle)

**What**: Test how components work together
**Speed**: Seconds
**Count**: Dozens to hundreds

```python
def test_order_creation_updates_inventory():
    order = create_order(product_id=1, quantity=5)
    inventory = get_inventory(product_id=1)
    assert inventory.available == original - 5
```

**Focus**: Database, external APIs, message queues

## E2E Tests (Top)

**What**: Test complete user workflows
**Speed**: Minutes
**Count**: A few dozen at most

```python
def test_complete_purchase_flow():
    login_user("test@example.com")
    add_to_cart(product="Book")
    checkout()
    assert order_confirmation_shown()
```

**Focus**: Critical business paths, cross-system flows

## Anti-Pattern: Ice Cream Cone

```
  /____________\\   Too many E2E tests
 /    E2E      \\   (slow, flaky, expensive)
/----------------\\
\\  Integration  /
 \\____________/
  \\   Unit   /     Too few unit tests
   \\______/        (poor coverage)
```

## Choosing Test Type

**Unit** if you can test the logic in isolation
**Integration** if you need real database/services
**E2E** for the 10 most critical user journeys

More fast tests, fewer slow tests.
""",
        "tags": ["software-testing", "testing-strategy", "best-practices"],
        "days_ago": 18,
    },
    # Cluster 3: Productivity & Learning (3 notes)
    {
        "title": "Spaced Repetition for Learning",
        "body": """# Spaced Repetition for Learning

Review information at increasing intervals to maximize retention.

## The Forgetting Curve

We forget about 50% of new information within a day, 90% within a month.

Spaced repetition fights this by reviewing just before you'd forget.

## Optimal Intervals

1. First review: 1 day after learning
2. Second review: 3 days later
3. Third review: 7 days later
4. Fourth review: 14 days later
5. Then: monthly, quarterly

## How It Works

Each successful recall strengthens the memory and extends the next interval.

Failed recalls reset the interval to a shorter period.

## Tools

**Anki**: The gold standard
- Customizable algorithms
- Mobile apps
- Shared decks

**SuperMemo**: The original
**Quizlet**: Simpler, more social

## Creating Good Cards

**Bad Card:**
Q: What is machine learning?
A: [Paragraph of text]

**Good Card:**
Q: What distinguishes supervised from unsupervised learning?
A: Supervised has labeled training data, unsupervised doesn't

**Better: Cloze Deletion**
Supervised learning uses {{c1::labeled}} training data to learn a mapping from inputs to outputs.

## Best Practices

- One concept per card
- Keep answers brief
- Add context (don't just memorize in a vacuum)
- Review daily (takes 10-20 minutes)
- Delete cards that don't matter anymore

## What to Use It For

- Language learning (vocabulary)
- Medical/law facts
- Programming APIs and syntax
- Historical dates and events

**Not good for:** Conceptual understanding (use active practice instead)

Spaced repetition is the closest thing to a "learning hack" that actually works.
""",
        "tags": ["learning", "productivity", "memory"],
        "days_ago": 6,
    },
    {
        "title": "Weekly Review Template",
        "body": """# Weekly Review Template

A structured weekly review keeps projects on track and surfaces insights.

## Schedule

Friday afternoon or Sunday evening. Block 30-60 minutes.

## Process

### 1. Collect & Process (10 min)

- Empty email inbox (archive, delete, add to task list)
- Empty browser tabs (bookmark or close)
- Empty download folder
- Review calendar for upcoming week

### 2. Review & Reflect (20 min)

**Last Week:**
- What got done?
- What didn't? Why?
- What went well?
- What could improve?

**This Week:**
- What are the 3 most important things to accomplish?
- Any meetings that need prep?
- Any blocked items to unblock?

### 3. Plan Next Week (15 min)

- Block calendar for deep work
- Schedule important tasks at peak energy times
- Identify top 3 priorities
- Move low-priority items to "someday" list

### 4. Update Systems (15 min)

- Review project statuses
- Update task lists
- File notes and documents
- Clean up workspace (physical and digital)

## Questions to Ask

- Am I working on the right things?
- What patterns am I seeing?
- What's draining energy?
- What's giving energy?
- What needs to change?

## Output

A list of **3 priorities** for the coming week and a **cleared mental space**.

## Why It Works

The review creates a pause to **work on** your work, not just **in** it.

> "If you don't decide what matters, everything does."

30 minutes weekly saves hours of misdirected effort.
""",
        "tags": ["productivity", "planning", "reflection"],
        "days_ago": 11,
    },
    {
        "title": "Zettelkasten Method",
        "body": """# Zettelkasten Method

A note-taking system for building knowledge networks over time.

## Core Idea

Create atomic notes and connect them. The value emerges from the connections.

## Three Note Types

### 1. Fleeting Notes
Quick captures. Temporary.
- Ideas during a meeting
- Shower thoughts
- Tweet you want to remember

Process these within 24-48 hours.

### 2. Literature Notes
Summarize what you read/watch.
- In your own words
- Include source
- Note why it matters to you

### 3. Permanent Notes
One idea, explained clearly, in your own words.

```
# Idea Title

[The idea explained in 1-3 paragraphs]

## Connections
- Links to related notes
- Why this connects to those

## Source
Where this came from (optional)
```

## Process

1. **Capture** fleeting notes throughout the day
2. **Process** fleeting → literature/permanent notes
3. **Connect** new notes to existing ones
4. **Review** connections regularly (spaced repetition)

## Linking Strategy

**Direct Links**: This note builds on / contradicts / provides example for that note

**Hub Notes**: Index notes that organize a topic

**Emergence**: Surprising insights arise from unexpected connections

## Digital Implementation

Tools: Obsidian, Roam Research, LogSeq, or (of course) LinkNote

## Anti-Patterns

- Collecting without processing
- Not using your own words
- Not adding links
- Treating it like a filing system

## Why It Works

- **Active learning**: Rephrasing forces understanding
- **Compounding**: Notes build on each other
- **Retrieval**: Ideas surface when you need them
- **Serendipity**: Cross-pollination of ideas

> "The slip-box is not a collection of notes. It's a thinking environment."

The goal isn't to store information—it's to have conversations with your past self.
""",
        "tags": ["knowledge-management", "note-taking", "productivity"],
        "days_ago": 20,
    },
    # Bridge notes (connect clusters)
    {
        "title": "Automated Testing ROI",
        "body": """# Automated Testing ROI

When does test automation pay for itself?

## Cost Factors

**Initial Investment:**
- Tool licenses
- Infrastructure setup
- Test authoring time
- Team training

**Ongoing:**
- Test maintenance (flaky tests, UI changes)
- CI/CD runtime costs
- Developer time investigating failures

## Benefit Factors

**Speed:**
- Regression suite runs in minutes, not hours
- Deploy multiple times per day

**Coverage:**
- Test combinations humans can't manually test
- Run tests on every commit

**Confidence:**
- Catch bugs before production
- Refactor without fear

**Scalability:**
- Same test suite handles 10x traffic growth
- No need to scale QA team linearly

## Break-Even Analysis

If manual testing takes 8 hours per release and you release weekly:
- Manual: 8 hours × 52 weeks = 416 hours/year

If automation takes 80 hours to set up and 2 hours/week to maintain:
- Automated: 80 + (2 × 52) = 184 hours/year

**Payback period: ~5 months**

## When Automation Doesn't Pay

- App changes constantly (maintenance > savings)
- Releasing infrequently (ROI takes years)
- Very simple app (manual is fast enough)
- No resources for maintenance

## Machine Learning + Testing

AI-powered tools reduce maintenance burden:
- Self-healing tests adapt to UI changes
- Intelligent test prioritization
- Automated test generation

This shifts the ROI curve significantly.

## Rule of Thumb

Automate tests for:
- Critical business flows
- Stable features
- Regression-prone areas
- APIs and business logic

Keep exploratory testing manual.
""",
        "tags": ["software-testing", "automation", "roi"],
        "days_ago": 16,
    },
    {
        "title": "Learning New Programming Languages",
        "body": """# Learning New Programming Languages

After your first few languages, learning new ones gets easier.

## The 80/20 Approach

Focus on concepts that appear in every language, master the syntax later.

### Core Concepts (Same Everywhere)

- Variables and types
- Control flow (if, loops, functions)
- Data structures (arrays, hashmaps)
- Error handling
- Modules/imports

### Language-Specific (Learn Later)

- Advanced type system features
- Metaprogramming
- Concurrency primitives
- Standard library quirks

## Four-Stage Learning Plan

### 1. Hello World (1 hour)
- Set up environment
- Run a simple program
- Understand basic syntax

### 2. Core Concepts (1 week)
- Variables, functions, loops
- Read/understand existing code
- Solve simple problems (fizzbuzz, palindromes)

### 3. Real Project (2-4 weeks)
Build something small but useful:
- CLI tool
- REST API
- Data analysis script

You'll learn most here.

### 4. Deep Dive (Ongoing)
- Read language docs
- Study standard library
- Learn idiomatic patterns
- Contribute to open-source project

## Resources

**Official docs first**: Most languages have great getting-started guides

**Practice:** LeetCode, Exercism, Project Euler

**Read code:** Find well-regarded open-source projects in that language

## Polyglot Benefits

Each language teaches different paradigms:
- **Python**: Readability, batteries included
- **JavaScript**: Async, event-driven
- **Go**: Simplicity, concurrency
- **Rust**: Memory safety, ownership
- **Haskell**: Functional purity, types

Learning a new language rewires how you think in ALL languages.

## Common Trap

Don't just learn syntax—learn the *philosophy* of the language.

Write Pythonic Python, not Java-in-Python-syntax.

## When to Learn a New Language

- Your problem fits its strengths (data science → Python, systems → Rust)
- Your team uses it
- You're curious and have time

Not every language needs mastery. Competency in 3-5 languages is plenty.
""",
        "tags": ["learning", "programming", "productivity"],
        "days_ago": 25,
    },
    # Isolated notes
    {
        "title": "Hello World",
        "body": """# Hello World

This is a simple test note.

Every programming journey starts with Hello World.

```python
print("Hello, World!")
```

It's a tradition that dates back decades.
""",
        "tags": ["programming", "tradition"],
        "days_ago": 30,
    },
    {
        "title": "Another Text",
        "body": """# Another Text

Just another note in the system.

Sometimes you need notes that don't connect to anything—they stand alone until the right connection appears.

That's okay. Not everything needs to be part of a cluster immediately.

> "All knowledge begins with a single note."
""",
        "tags": ["notes", "random"],
        "days_ago": 28,
    },
]

# Links to create between related notes (by title pairs)
SAMPLE_LINKS = [
    # Within Cluster 1 (AI/ML)
    ("Understanding Artificial Intelligence", "Machine Learning in Automation"),
    ("Machine Learning in Automation", "Neural Networks Basics"),
    ("Neural Networks Basics", "Prompt Engineering Tips"),
    # Within Cluster 2 (Testing)
    ("AI-Powered Software Testing", "Writing Reliable Test Cases"),
    ("Selenium vs Playwright", "Writing Reliable Test Cases"),
    ("API Testing with REST Assured", "Test Pyramid Strategy"),
    # Within Cluster 3 (Productivity/Learning)
    ("Weekly Review Template", "Zettelkasten Method"),
    ("Spaced Repetition for Learning", "Zettelkasten Method"),
    # Bridge connections
    ("AI-Powered Software Testing", "Machine Learning in Automation"),  # AI + Testing
    ("Automated Testing ROI", "Test Pyramid Strategy"),  # Testing + ROI
    ("Automated Testing ROI", "Machine Learning in Automation"),  # ROI + ML
    ("Learning New Programming Languages", "Spaced Repetition for Learning"),  # Learning bridge
]


def create_or_get_user(session: Session, email: str, password: str) -> User:
    """Create user if doesn't exist, otherwise return existing user."""
    user = session.scalars(select(User).where(User.email == email)).first()
    if user:
        print(f"✓ User {email} already exists (id: {user.id})")
        return user

    user = User(email=email, password_hash=hash_password(password))
    session.add(user)
    session.commit()
    session.refresh(user)
    print(f"✓ Created user: {email} (id: {user.id})")
    return user


def seed_notes(session: Session, user: User) -> dict[str, UUID]:
    """
    Create sample notes and tags, idempotently.

    Returns dict of note_title -> note_id.
    """
    note_ids: dict[str, UUID] = {}
    created_count = 0
    skipped_count = 0
    now = datetime.now(UTC)

    for note_data in SAMPLE_NOTES:
        title = cast(str, note_data["title"])

        # Check if note already exists
        existing = session.scalars(select(Note).where(Note.owner_id == user.id, Note.title == title)).first()

        if existing:
            note_ids[title] = existing.id
            skipped_count += 1
            continue

        # Create note with realistic timestamps
        days_ago = cast(float, note_data.get("days_ago", 0))
        created_at = now - timedelta(days=days_ago)

        note = Note(
            owner_id=user.id,
            title=title,
            body=note_data["body"],
            created_at=created_at,
            updated_at=created_at,
        )
        session.add(note)
        session.flush()  # Get note ID
        note_ids[title] = note.id

        # Create/get tags
        for tag_name in cast(list[str], note_data["tags"]):
            tag = session.scalars(select(Tag).where(Tag.owner_id == user.id, Tag.name == tag_name)).first()
            if not tag:
                tag = Tag(owner_id=user.id, name=tag_name)
                session.add(tag)
                session.flush()

            if tag not in note.tags:
                note.tags.append(tag)

        created_count += 1

    session.commit()

    if created_count > 0:
        print(f"✓ Created {created_count} notes")
    if skipped_count > 0:
        print(f"  Skipped {skipped_count} existing notes")

    return note_ids


def seed_links(session: Session, user: User, note_ids: dict[str, UUID]) -> int:
    """Create accepted links between related notes. Returns count of new links."""
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
        existing = session.scalars(
            select(AcceptedLink).where(
                AcceptedLink.source_note_id == source_id,
                AcceptedLink.target_note_id == target_id,
            )
        ).first()

        if not existing:
            link = AcceptedLink(
                owner_id=user.id,
                source_note_id=source_id,
                target_note_id=target_id,
            )
            session.add(link)
            created += 1

    if created > 0:
        session.commit()
        print(f"✓ Created {created} accepted links")

    return created


def seed_rejected_suggestion(session: Session, user: User, note_ids: dict[str, UUID]) -> int:
    """Create one rejected suggestion for testing. Returns 1 if created, 0 if skipped."""
    # Reject suggestion between two unrelated notes
    source_title = "Hello World"
    target_title = "API Testing with REST Assured"

    source_id = note_ids.get(source_title)
    target_id = note_ids.get(target_title)

    if not source_id or not target_id:
        return 0

    # Ensure canonical order
    if source_id > target_id:
        source_id, target_id = target_id, source_id

    # Check if already exists
    existing = session.scalars(
        select(Suggestion).where(
            Suggestion.source_note_id == source_id,
            Suggestion.target_note_id == target_id,
            Suggestion.status == "rejected",
        )
    ).first()

    if existing:
        return 0

    # Create a rejected suggestion (requires similarity_score, explanation, and updated_at fields)
    now = datetime.now(UTC)

    rejection = Suggestion(
        owner_id=user.id,
        source_note_id=source_id,
        target_note_id=target_id,
        similarity_score=0.15,  # Below threshold, which is why it might be rejected
        explanation="Low semantic similarity between notes on different topics",
        status="rejected",
        source_updated_at=now,
        target_updated_at=now,
        rejected_at=now,
    )
    session.add(rejection)
    session.commit()
    print("✓ Created 1 rejected suggestion (for testing)")
    return 1


def run_seed(
    email: str = "demo@linknote.local",
    password: str = "demo123456",
    session_maker: Any = None,
) -> dict[str, Any]:
    """
    Main seeding function. Idempotent - safe to run multiple times.

    Returns summary dict with counts.
    """
    from shared.db import get_sessionmaker

    if session_maker is None:
        session_maker = get_sessionmaker()

    session = session_maker()
    summary: dict[str, Any] = {"user_created": False, "notes_created": 0, "links_created": 0}

    try:
        print(f"\n📝 Seeding database for {email}...")

        # Create/get user
        user = create_or_get_user(session, email, password)
        summary["user_id"] = str(user.id)
        summary["user_email"] = user.email

        # Create notes
        note_ids = seed_notes(session, user)
        summary["notes_total"] = len(note_ids)

        # Create links
        links_created = seed_links(session, user, note_ids)
        summary["links_created"] = links_created

        # Create one rejected suggestion
        rejected = seed_rejected_suggestion(session, user, note_ids)
        summary["rejected_created"] = rejected

        print("\n✅ Seeding complete!")
        print(f"   Total notes: {len(note_ids)}")
        print(f"   New links: {links_created}")
        print("   Login credentials:")
        print(f"     Email: {email}")
        print(f"     Password: {password}")
        print()

        return summary

    except Exception as e:
        session.rollback()
        print(f"\n❌ Error seeding database: {e}")
        raise
    finally:
        session.close()
