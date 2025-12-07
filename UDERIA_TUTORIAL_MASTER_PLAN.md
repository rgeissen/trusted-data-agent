# Uderia Platform - Tutorial Master Plan
## Comprehensive Tutorial Structure & Narration Guide

**Platform:** Uderia (www.uderia.com)  
**Tutorial Platform:** Tight.studio  
**Target Duration per Section:** 2-5 minutes  
**Last Updated:** December 7, 2025

---

## 📋 Tutorial Philosophy

This tutorial series showcases Uderia's unique value proposition: **Cloud-Level Reasoning with Zero-Trust Privacy**. Each module aligns with one of Uderia's six core principles, ensuring comprehensive coverage of features, benefits, and differentiation.

**Key Messaging Themes:**
- From Days to Seconds (Actionable)
- From Guesswork to Clarity (Transparent)
- From $$$ to ¢¢¢ (Efficient)
- From Data Exposure to Data Sovereignty (Sovereignty)
- From Hidden Costs to Total Visibility (Financial Governance)
- From Isolated Expertise to Collective Intelligence (Collaborative)

---

## Module 1: Introduction & Quick Start
**Goal:** Hook viewers with immediate value demonstration and quick wins

**Demo Environment Setup:**
- **Database:** fitness_db (Teradata)
- **Schema:** 5 tables (Customers, Sales, SaleDetails, Products, ServiceTickets)
- **Business Context:** Fitness equipment retail and service tracking
- **MCP Tools:** base_tools, quality_tools for business user scenarios
- **Profiles:** Standard profile with Teradata MCP server configured

### 1.1 Welcome to Uderia - The Platform Promise
**Duration:** 2-3 minutes  
**Learning Objectives:**
- Understand Uderia's unique positioning in the AI landscape
- Recognize the six core principles
- See the fundamental "before vs after" transformation

**Key Topics to Cover:**
- [ ] The problem: Traditional AI tools force trade-offs (cloud intelligence vs data privacy)
- [ ] The Uderia solution: Best of both worlds
- [ ] Six core principles overview (visual diagram)
- [ ] Platform overview screenshot tour

**Narration Script:**
```
Welcome to Uderia—the platform that finally ends the impossible choice between 
cloud intelligence and data privacy.

For too long, organizations have been forced into a corner: either send your 
sensitive data to powerful cloud models and sacrifice sovereignty, or run local 
models and compromise on capability. It's been one or the other—never both.

Uderia shatters this false dichotomy.

Imagine having the reasoning power of Claude, GPT-4, or Gemini—while keeping your 
most sensitive data completely private on your own infrastructure. That's Uderia's 
hybrid intelligence architecture: cloud-level planning meets local execution.

But we go far beyond just hybrid deployment. Uderia is built on six revolutionary 
principles that transform how you work with enterprise data:

First—ACTIONABLE: Your conversational discovery IS your production-ready API. No 
handoffs. No rebuilding. From insight to automation in seconds, not weeks.

Second—TRANSPARENT: No more AI black boxes. Watch the agent plan, execute, and 
self-correct in real-time. Every decision, every tool call, fully visible.

Third—EFFICIENT: Our Fusion Optimizer uses strategic planning, RAG-powered 
self-learning, and proactive optimization to slash costs from dollars to cents.

Fourth—SOVEREIGNTY: Your data, your rules, your environment. Whether you choose 
cloud hyperscalers, AWS Bedrock, or fully private Ollama models—you're in control.

Fifth—FINANCIAL GOVERNANCE: Track every token, every penny, in real-time. Complete 
visibility into LLM spending with comprehensive analytics and cost optimization.

And sixth—COLLABORATIVE: Transform individual expertise into collective intelligence 
through our Intelligence Marketplace. Share patterns, subscribe to community wisdom, 
and amplify capabilities together.

This isn't just another data chat tool. Uderia is a complete AI orchestration platform 
that delivers enterprise results with optimized speed and minimal token cost.

Over the next few tutorials, you'll see exactly how Uderia transforms every aspect 
of data operations—from your first conversation to production deployment at scale.

Let's dive in.
```

**Screen Capture Plan:**
- [ ] Website hero section with tagline "Cloud-Level Reasoning. Zero-Trust Privacy."
- [ ] Six principles icons/cards appearing sequentially as mentioned
- [ ] Hybrid architecture diagram (cloud planner + local executor)
- [ ] Quick feature montage (API, Live Status Panel, Marketplace, Cost Dashboard)
- [ ] Live platform login screen teaser

**Supporting Materials:**
- README.md introduction
- Website value proposition sections
- Platform architecture diagram

---

### 1.2 First Login & Instant Intelligence
**Duration:** 2-3 minutes  
**Learning Objectives:**
- Successfully log in or register
- Understand the UI layout at first glance
- Identify key navigation elements

**Key Topics to Cover:**
- [ ] Registration/Login process
- [ ] Platform UI overview (navigation bar, main panels)
- [ ] Quick orientation: Conversations, Executions, Intelligence, Marketplace, Admin
- [ ] Profile indicator and status elements

**Narration Script:**
```
Let's get you started with Uderia. If you're following along on the live platform 
at tda.uderia.com, you'll see the login screen. New users can register in seconds—
just an email, username, and password. Enterprise deployments can integrate with 
your existing SSO systems.

Once you log in, you're immediately greeted by a clean, purposeful interface designed 
around one goal: getting you from question to insight as quickly as possible.

Let's orient ourselves.

Across the top, you have your main navigation bar. Five key sections:

'Conversations'—where you'll spend most of your time. This is your interactive 
workspace for natural language queries and real-time agent collaboration.

'Executions'—your mission control for monitoring tasks, tracking long-running queries, 
and reviewing execution history across all your automation workflows.

'Intelligence'—this is where the magic of continuous improvement lives. Here you'll 
manage your RAG collections, review champion cases, and track efficiency gains as 
the platform learns from your successes.

'Marketplace'—the community hub. Discover and share execution patterns, subscribe 
to expert knowledge collections, and contribute to the collective intelligence ecosystem.

And 'Administration'—your governance center. User management, cost analytics, access 
tokens, and system configuration all live here.

In the top right, you'll see your profile indicator showing your active LLM profile—
this controls which language model and MCP servers you're currently using. We'll 
dive deep into profiles later, but know that you can switch between different 
configurations with a single click.

The main workspace is divided into three intelligent panels:

On the left, your 'Resource Panel'—this dynamically shows available MCP tools, 
prompt templates, and data sources. This is your agent's capability catalog.

In the center, your 'Conversation Panel'—where queries, results, and visualizations 
appear. This is your primary interaction space.

And on the right, the game-changing 'Live Status Panel'—this is Uderia's transparency 
engine. Here you'll see the agent's strategic plan unfold in real-time, watch tactical 
decisions happen, and inspect raw data at every step. No black boxes. No guesswork.

Everything you need is within reach. Clean, organized, and built for speed.

Now let's put it to work.
```

**Screen Capture Plan:**
- [ ] Login screen with registration option highlighted
- [ ] Successful login transition to dashboard
- [ ] Navigation bar with each section highlighted as mentioned
- [ ] Profile indicator zoom-in (top right corner)
- [ ] Three-panel layout with annotations: Resource (left), Conversation (center), Live Status (right)
- [ ] Quick hover over each panel to show dynamic content
- [ ] Smooth transition to next section (query input ready)

**Supporting Materials:**
- User Guide documentation
- UI screenshots

---

### 1.3 Your First Conversation - From Question to Insight
**Duration:** 3-4 minutes  
**Learning Objectives:**
- Execute a simple query successfully
- Understand query → insight → action flow
- See immediate value in action

**Key Topics to Cover:**
- [ ] Typing a natural language query
- [ ] Watching the Live Status Panel (strategic plan appears)
- [ ] Tool execution visualization
- [ ] Receiving structured results
- [ ] Understanding the response format

**Narration Script:**
```
Alright—let's ask your first question. And I mean really ask it, the way you'd 
ask a colleague. No SQL required. No technical syntax. Just natural language.

We're working with a fitness equipment retail database. Let's try: "What are the 
top 5 fitness products by revenue this month?"

Watch what happens the moment you hit enter.

The Live Status Panel instantly comes alive. You see the agent's strategic plan 
appear—it's not just blindly executing. It's thinking through the problem:

"Phase 1: Identify relevant tables - Sales, SaleDetails, Products.
Phase 2: Calculate revenue by product from current month.
Phase 3: Sort and return top 5 with details."

This is the transparency that sets Uderia apart. You're not staring at a loading 
spinner wondering what's happening. You're watching a strategic blueprint unfold 
in real-time.

Now watch the Tactical Execution section. The agent decides which tool to invoke—
it's calling the base_tools SQL query function. You see the exact tool name, 
the SQL being generated joining SaleDetails with Products, filtering by current 
month, and the parameters being passed. Zero guesswork.

Here's the actual SQL it generated:

SELECT p.ProductName, p.Brand, SUM(sd.Quantity * sd.UnitPrice) as Revenue
FROM fitness_db.Products p
JOIN fitness_db.SaleDetails sd ON p.ProductID = sd.ProductID
JOIN fitness_db.Sales s ON sd.SaleID = s.SaleID
WHERE EXTRACT(MONTH FROM s.SaleDate) = EXTRACT(MONTH FROM CURRENT_DATE)
GROUP BY p.ProductName, p.Brand
ORDER BY Revenue DESC
LIMIT 5;

Within seconds, raw data flows back. You can actually click into the Live Status 
Panel and inspect the exact JSON response the tool returned. Complete visibility.

And here's where it gets beautiful—the agent doesn't just dump data on you. It 
intelligently renders the results: a clean, formatted table appears in your 
Conversation Panel:

Treadmill Pro 3000 (FitTech) - $45,230
Elliptical Elite (CardioMax) - $38,900
Weight Bench Deluxe (IronGrip) - $32,150
...and so on.

But you're not done. Let's ask a follow-up: "Show me the customer demographics 
for people who bought that top treadmill."

Notice something powerful—the agent already has context from your first question. 
It knows we're talking about the Treadmill Pro 3000. It knows the Products and 
Sales tables structure. This is contextual memory at work.

A new strategic plan appears: 
"Phase 1: Identify customers who purchased ProductID for Treadmill Pro 3000.
Phase 2: Retrieve demographic data from Customers table.
Phase 3: Aggregate by city, state, and visualize distribution."

It's joining Sales, SaleDetails, Customers—all without you specifying a single 
table name. The agent remembers. The agent reasons.

From question to insight in seconds. From insight to follow-up without missing a beat.

This is conversational data analysis—no Python notebooks, no SQL editors, no 
context switching. Just you, your questions, and an intelligent agent that shows 
its work every step of the way.

And here's the kicker—every query you just ran? It's automatically available via 
REST API. Your conversational discovery is already operationalized. But we'll 
explore that revolutionary paradigm in the next module.

For now, welcome to Uderia. You've just experienced intelligence that's actionable, 
transparent, and built for speed.

Let's keep going.
```

**Screen Capture Plan:**
- [ ] Query typed into input: "What are the top 5 products by revenue this quarter?"
- [ ] Live Status Panel: Strategic plan appears with phases
- [ ] Live Status Panel: Tactical section shows tool selection and SQL generation
- [ ] Live Status Panel: Raw data response visible (expandable JSON)
- [ ] Conversation Panel: Results render as formatted table with actual data
- [ ] Follow-up query typed: "Why did Product X decline compared to last quarter?"
- [ ] New strategic plan appears showing comparative analysis
- [ ] Results with trend analysis and potential chart visualization
- [ ] Quick flash of REST API documentation showing same query structure
- [ ] End with satisfied user looking at insights

**Supporting Materials:**
- fitness_db schema documentation (5 tables: Customers, Sales, SaleDetails, Products, ServiceTickets)
- MCP base_tools configuration (Teradata connector)
- Sample queries: revenue analysis, customer demographics, product trends
- Expected output samples with realistic fitness retail data
- MCP quality_tools for data validation demonstrations

---

## Module 2: ACTIONABLE - From Discovery to Production
**Goal:** Demonstrate seamless operationalization from conversation to automation

### 2.1 The Two-in-One Philosophy: Conversation → API
**Duration:** 3-4 minutes  
**Learning Objectives:**
- Understand the unique "discovery is production" paradigm
- See how a conversational query becomes an API call
- Grasp the value of eliminating handoffs

**Key Topics to Cover:**
- [ ] Traditional workflow: Analyst → Data Engineer → API Developer (days/weeks)
- [ ] Uderia workflow: One conversation → Immediate API (seconds)
- [ ] REST API endpoint overview
- [ ] Session management concept
- [ ] Bearer token authentication basics

**Narration Script:**
```
Let's talk about something revolutionary—something that separates Uderia from every 
other data tool you've ever used.

In traditional workflows, discovery and automation are two completely separate worlds.

Your business analyst asks a question: "What are our top revenue products?" 

A data analyst writes SQL in a notebook. 

A data engineer takes that SQL and rebuilds it in a pipeline.

An API developer wraps it in an endpoint. 

And DevOps deploys it to production.

Days or weeks. Multiple handoffs. Context lost at every step. This is the friction 
that kills innovation.

Uderia collapses this entire chain into a single conversation.

Watch this. We just asked: "What are the top 5 fitness products by revenue this month?"

The agent executed it using the `base_readQuery` MCP tool. We got our answer in seconds. 
That was conversational discovery.

But here's where it gets powerful—that exact same query is already available via REST API. 
No rebuilding. No translation. No handoffs.

Let me show you. Here's the Postman collection. We're hitting the `/v1/query/submit` 
endpoint with the exact same natural language question: "What are the top 5 fitness 
products by revenue this month?"

Same question. Same strategic plan. Same tool execution. Same results.

Or use cURL:

curl -X POST https://tda.uderia.com/api/v1/query/submit \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "What are the top 5 fitness products by revenue this month?",
    "session_id": "your-session-id"
  }'

Your conversational discovery IS your production automation. This is the two-in-one 
paradigm. Discovery equals operationalization.

No data engineer required to translate your notebook into a pipeline.

No API developer required to wrap your query in an endpoint.

No deployment cycle to move from dev to prod.

One conversation. One API. Zero friction.

This is what actionable intelligence looks like. From insight to automation in seconds, 
not weeks.

Let's dive deeper into how this actually works.
```

**Screen Capture Plan:**
- [ ] Traditional workflow diagram: Analyst → Engineer → API Dev → DevOps (days/weeks)
- [ ] Uderia workflow: One conversation → Immediate API (seconds)
- [ ] Live query execution showing `base_readQuery` tool call
- [ ] Switch to Postman: same query via `/v1/query/submit` endpoint
- [ ] Show cURL command with actual request/response
- [ ] Side-by-side comparison: UI results vs API results (identical)
- [ ] REST API documentation page

**Supporting Materials:**
- REST API documentation (query endpoints)
- Postman collection with pre-configured requests
- cURL command examples
- Workflow comparison diagram
- MCP tools reference (base_readQuery)

---

### 2.2 Profile System: Modular Infrastructure
**Duration:** 3-4 minutes  
**Learning Objectives:**
- Understand profile architecture (LLM Provider + MCP Servers)
- Learn profile switching mechanisms
- Recognize use cases for different profiles

**Key Topics to Cover:**
- [ ] What is a profile? (LLM + MCP Server combination)
- [ ] Profile tags (@PROD, @COST, @LOCAL)
- [ ] Default profile vs temporary overrides
- [ ] Creating and editing profiles
- [ ] Classification modes (Light vs Full)

**Narration Script:**
```
Now let's talk about profiles—Uderia's modular infrastructure system that gives you 
precise control over how your agent operates.

Think of a profile as a complete configuration package. It bundles two critical pieces:

1. Your LLM Provider—which language model you're using (Claude, GPT-4, Gemini, Ollama, etc.)
2. Your MCP Servers—which tools and data sources are available

For example, our "Production" profile might use Claude Sonnet with our Teradata MCP server. 
This gives us access to tools like `base_readQuery`, `base_tableList`, and `base_tableDDL` 
for database operations.

But maybe you want a "Cost-Optimized" profile using Gemini Flash for simple queries—same 
MCP tools, cheaper model.

Or a "Local Privacy" profile running entirely on Ollama—no cloud model, complete data 
sovereignty, same agent capabilities.

Profiles make this effortless.

Here's the power: every profile gets a tag. Look at the top right—we're currently on 
"@PROD" which uses Claude and our Teradata server.

Now let's say you want to run one expensive, complex query on the best model available. 
You don't need to reconfigure everything. Just type:

"@OPUS What are the most complex customer purchasing patterns across all product categories?"

Notice what just happened—the @OPUS tag temporarily overrode your default profile for 
this single query. It switched to Claude Opus, executed the query, and returned to 
your default profile.

One query. One tag. Temporary override.

Or let's create a new profile from scratch. Click Setup → Profiles → New Profile.

Give it a name: "AWS_Bedrock_Prod"
Tag: "@AWSBED"  
LLM Provider: AWS Bedrock → select your inference profile
MCP Server: Teradata MCP (this gives us all our base_* and dba_* tools)

Classification mode—this controls how tools and prompts are categorized:
- Light mode: Simple "All Tools" / "All Prompts" buckets—fast, no LLM needed
- Full mode: AI-powered categorization ("Database Operations", "Data Quality", etc.)

Let's use Light mode for speed. Save it.

Now that profile is available. Switch to it from the dropdown... and watch the agent 
reload with AWS Bedrock models and your Teradata MCP tools.

Same conversational interface. Same tools. Different infrastructure.

Profiles separate your usage patterns from your infrastructure. You can have:
- A profile for exploratory analysis (cheap model, fast iteration)
- A profile for production reports (reliable model, proven tools)  
- A profile for compliance (local Ollama, zero cloud exposure)
- A profile for cost comparison (test same query across multiple providers)

Flexibility without complexity. Infrastructure as configuration, not code.

This is modular intelligence at work.
```

**Screen Capture Plan:**
- [ ] Profile dropdown showing multiple profiles with tags (@PROD, @COST, @LOCAL, @OPUS)
- [ ] Profile configuration panel breakdown (LLM + MCP Server components)
- [ ] Active profile indicator showing "@PROD" with Claude + Teradata
- [ ] Query with @OPUS tag override demonstration
- [ ] Creating new profile: "AWS_Bedrock_Prod" with @AWSBED tag
- [ ] Classification mode selection (Light vs Full)
- [ ] Profile switching in action (watch capabilities reload)
- [ ] Capabilities Panel showing MCP tools (base_readQuery, base_tableList, etc.)

**Supporting Materials:**
- Profile configuration documentation
- MCP server setup guide
- Tag syntax reference
- Classification mode comparison
- Example profile configurations (cost, performance, privacy)

**Supporting Materials:**
- Profile configuration documentation
- Example profile configurations
- Use case scenarios

---

### 2.3 REST API Power: Operationalize Everything
**Duration:** 4-5 minutes  
**Learning Objectives:**
- Master REST API capabilities
- Understand async task pattern
- Learn endpoint categories

**Key Topics to Cover:**
- [ ] API endpoint categories (session, query, task, config, RAG, analytics)
- [ ] Async submit + poll pattern
- [ ] Session management (create, reuse, delete)
- [ ] Long-lived access tokens
- [ ] Profile override via API

**Narration Script:**
```
Now let's explore the full power of Uderia's REST API—the production backbone that 
turns every conversation into a programmable workflow.

The API is organized into six logical endpoint categories:

1. **Session Management** - Create, list, delete conversation sessions
2. **Query Execution** - Submit queries, poll status, retrieve results  
3. **Task Management** - Cancel tasks, check status, handle long-running operations
4. **Configuration** - Switch profiles, manage providers, control MCP servers
5. **RAG Operations** - Create collections, upload documents, manage knowledge
6. **Analytics** - Cost tracking, token usage, efficiency metrics

Let's walk through a complete workflow.

First, authentication. Every API call requires a Bearer token. You can use:
- Short-lived JWT tokens (24 hours, issued at login)
- Long-lived access tokens (90 days or permanent, managed in Admin panel)

Let's use a long-lived token for automation. In the Admin panel, generate one... 
there it is. Copy it once—you'll never see it again. Store it securely.

Now let's build a workflow.

**Step 1: Create a session**

POST /api/v1/sessions/create
{
  "session_name": "Revenue Analysis Automation",
  "profile_override": "@PROD"
}

Returns: `{"session_id": "abc-123-def-456"}`

This creates an isolated conversation context. All queries in this session share memory.

**Step 2: Submit a query (async pattern)**

POST /api/v1/query/submit
{
  "query": "What are the top 5 fitness products by revenue this month?",
  "session_id": "abc-123-def-456"
}

Returns: `{"task_id": "task_789"}`

Notice—we don't get results immediately. This is the async submit + poll pattern. 
The agent starts working in the background.

**Step 3: Poll for status**

GET /api/v1/query/status/task_789

Returns:
{
  "status": "running",
  "progress": "Executing phase 1: Database query"
}

Keep polling... now it's complete:

{
  "status": "completed",
  "result_ready": true
}

**Step 4: Retrieve results**

GET /api/v1/query/result/task_789

Returns the full structured response—the same data you'd see in the UI, but as JSON:

{
  "query": "What are the top 5 fitness products...",
  "answer": "...",
  "tool_calls": [{"tool": "base_readQuery", "args": {...}, "result": [...]}],
  "tokens": {"input": 1250, "output": 320},
  "cost": 0.0042
}

You get everything—the answer, the tool executions (like `base_readQuery`), token 
counts, and costs. Complete transparency via API.

**Step 5: Follow-up query (context preserved)**

POST /api/v1/query/submit
{
  "query": "Show me customer demographics for that top product",
  "session_id": "abc-123-def-456"
}

The agent remembers the previous query. Context is maintained across API calls, just 
like in the UI.

**Profile Override**

Want to run a single query on a different profile?

POST /api/v1/query/submit
{
  "query": "Complex analytical question here",
  "session_id": "abc-123-def-456",
  "profile_override": "@OPUS"
}

This query runs on Claude Opus. Next query returns to session's default profile.

**Task Cancellation**

If a query is taking too long:

POST /api/v1/tasks/cancel/task_789

Gracefully stops execution and frees resources.

This API architecture enables:
- Batch processing with Apache Airflow
- Chatbot integrations with Flowise
- Custom dashboards pulling live insights
- CI/CD pipelines running validation queries
- Scheduled reports running overnight

Your conversational intelligence, fully programmable. This is production-grade AI 
orchestration.
```

**Screen Capture Plan:**
- [ ] API documentation landing page with six categories
- [ ] Admin panel: Generate long-lived access token
- [ ] Postman collection: Session creation request/response
- [ ] Postman: Query submission (async) → task_id returned
- [ ] Postman: Status polling (running → completed)
- [ ] Postman: Result retrieval with full JSON response
- [ ] Show tool_calls array with `base_readQuery` execution details
- [ ] Follow-up query demonstrating context preservation
- [ ] Profile override example (@OPUS)
- [ ] Task cancellation request

**Supporting Materials:**
- Complete REST API documentation
- Postman collection (pre-configured)
- Authentication guide (JWT vs access tokens)
- Async pattern best practices
- Error handling reference
- Rate limiting documentation

**Supporting Materials:**
- REST API complete guide
- Postman collection
- Python/JavaScript SDK examples

---

### 2.4 Airflow Integration: Production Automation
**Duration:** 3-4 minutes  
**Learning Objectives:**
- Understand batch automation use case
- Learn DAG structure for Uderia integration
- See production-ready patterns

**Key Topics to Cover:**
- [ ] Apache Airflow integration overview
- [ ] Example DAG walkthrough
- [ ] Session reuse pattern
- [ ] Profile override for specialized workloads
- [ ] Async polling pattern for long-running queries

**Narration Script:**
```
Let's take everything we've learned about the REST API and put it into production with 
Apache Airflow—the industry-standard workflow orchestrator.

Uderia ships with production-ready DAG examples that you can deploy immediately. Let's 
walk through one.

Here's the Airflow UI showing our "TDA Execute Questions" DAG. This workflow runs a 
batch of analytical queries every morning at 6 AM.

Let me show you the code structure.

This is `tda_00_execute_questions.py`—our example DAG. It's built with Uderia best 
practices:

**1. Session Reuse Pattern**

First, we create a single session for all queries:

```python
def create_tda_session(**context):
    response = requests.post(
        f"{TDA_BASE_URL}/api/v1/sessions/create",
        headers={"Authorization": f"Bearer {TDA_ACCESS_TOKEN}"},
        json={"session_name": f"Airflow Batch {context['ds']}"}
    )
    session_id = response.json()["session_id"]
    context['ti'].xcom_push(key='tda_session_id', value=session_id)
```

We store the session_id in XCom so all downstream tasks can share context. This means 
query 2 can reference results from query 1—just like conversational follow-ups.

**2. Async Submit + Poll Pattern**

For each query, we submit it and poll until complete:

```python
def submit_query(query_text, session_id):
    response = requests.post(
        f"{TDA_BASE_URL}/api/v1/query/submit",
        headers={"Authorization": f"Bearer {TDA_ACCESS_TOKEN}"},
        json={
            "query": query_text,
            "session_id": session_id,
            "profile_override": "@PROD"  # Optional profile override
        }
    )
    task_id = response.json()["task_id"]
    
    # Poll until complete
    while True:
        status = requests.get(
            f"{TDA_BASE_URL}/api/v1/query/status/{task_id}"
        ).json()
        
        if status["status"] == "completed":
            break
        elif status["status"] == "failed":
            raise Exception(f"Query failed: {status['error']}")
        
        time.sleep(5)  # Poll every 5 seconds
    
    # Retrieve results
    result = requests.get(
        f"{TDA_BASE_URL}/api/v1/query/result/{task_id}"
    ).json()
    
    return result
```

This handles long-running queries gracefully—no timeouts, no blocking.

**3. Profile Override for Specialized Workloads**

Notice the `profile_override` parameter. Maybe your morning batch runs on a cost-optimized 
profile (@COST with Gemini Flash), but your quarterly executive reports need maximum 
accuracy (@OPUS with Claude Opus).

Same infrastructure. Different profiles per task.

**4. Error Handling and Retries**

```python
task = PythonOperator(
    task_id='query_revenue_analysis',
    python_callable=submit_query,
    op_kwargs={
        'query_text': 'What are monthly revenue trends by product category?',
        'session_id': '{{ ti.xcom_pull(key="tda_session_id") }}'
    },
    retries=3,
    retry_delay=timedelta(minutes=2)
)
```

Airflow automatically retries failed tasks. If the MCP server hiccups or the LLM times 
out, Airflow handles it.

**5. Scheduling and Triggering**

```python
dag = DAG(
    'tda_execute_questions',
    default_args=default_args,
    description='Execute batch Uderia queries',
    schedule_interval='0 6 * * *',  # Every day at 6 AM
    catchup=False
)
```

Cron-based scheduling. Or trigger manually. Or trigger via API. Or trigger on upstream 
data arrival. Full Airflow flexibility.

**6. Results Storage**

```python
def store_results(result, **context):
    # Write to S3, load into data warehouse, send to Slack—whatever you need
    s3.put_object(
        Bucket='analytics-reports',
        Key=f"daily_revenue_{context['ds']}.json",
        Body=json.dumps(result)
    )
```

Uderia gives you the insights. Airflow orchestrates storage, distribution, and 
downstream actions.

Let's trigger this DAG manually and watch it run.

Task 1: Create session... green check. Session ID stored in XCom.

Task 2: Submit first query "Top revenue products"... executing... Agent is using 
`base_readQuery` to query our fitness_db... complete. Results stored.

Task 3: Submit follow-up "Customer demographics for top products"... notice it's using 
the same session ID, so it has context from Task 2... complete.

Task 4: Store all results to S3... done.

Four tasks. One conversational workflow. Full production orchestration.

This is what it means to operationalize intelligence. From notebook explorations to 
scheduled batch processing—same agent, same queries, production-grade reliability.

Airflow + Uderia. Conversational AI meets enterprise workflows.
```

**Screen Capture Plan:**
- [ ] Airflow UI: DAG graph view showing task dependencies
- [ ] Code editor: `tda_00_execute_questions.py` walkthrough
- [ ] Session creation task code
- [ ] Async submit + poll code pattern
- [ ] Profile override configuration
- [ ] Error handling and retry configuration
- [ ] Schedule interval setting (cron)
- [ ] Manual DAG trigger
- [ ] Live task execution: green checks appearing
- [ ] Task logs showing API calls and responses
- [ ] XCom variables showing session_id propagation
- [ ] Results storage task completing

**Supporting Materials:**
- docs/Airflow complete documentation
- Example DAG files (tda_00_execute_questions.py)
- Airflow setup guide
- Best practices document
- Error handling patterns
- Production deployment checklist

**Supporting Materials:**
- docs/Airflow documentation
- Example DAG files
- Production deployment guide

---

## Module 3: TRANSPARENT - Eliminate the Black Box
**Goal:** Build trust through complete visibility into agent reasoning

### 3.1 Live Status Panel: Watch the Agent Think
**Duration:** 3-4 minutes  
**Learning Objectives:**
- Understand real-time agent reasoning visibility
- Learn to read strategic plans
- Recognize tactical decisions and tool selections

**Key Topics to Cover:**
- [ ] Live Status Panel components (Strategic Plan, Tactical Execution, Raw Data)
- [ ] Streaming updates via Server-Sent Events
- [ ] Phase-by-phase plan breakdown
- [ ] Tool selection rationale display
- [ ] Self-correction events

**Narration Script:**
```
Welcome to the feature that changes everything about AI trust—the Live Status Panel.

Most AI tools are black boxes. You ask a question, you wait, you get an answer. But 
what happened in between? You have no idea. Was the answer based on accurate data? Did 
it misunderstand your question? Did it hallucinate? You're left guessing.

Uderia eliminates the guesswork through radical transparency.

Let's ask a complex question: "Compare the service ticket resolution times across 
different product categories and identify products with quality issues."

The moment we hit enter, watch the right panel.

**STRATEGIC PLAN APPEARS:**

Phase 1: Identify relevant tables (ServiceTickets, Products)
Phase 2: Calculate average resolution times by ProductType
Phase 3: Identify products with high ticket counts and slow resolution
Phase 4: Generate comparative analysis report

This isn't just a loading spinner—this is a strategic blueprint. The agent is showing 
you its reasoning process before it even starts executing. You can validate the approach 
before wasting tokens on a wrong direction.

Now watch the Tactical Execution section.

**PHASE 1 EXECUTION:**

Tool selected: `base_tableList`
Arguments: {"database": "fitness_db"}
Rationale: "Need to verify ServiceTickets and Products tables exist"

You see the exact tool being called, the exact arguments being passed, and why the 
agent chose this tool. Zero ambiguity.

Results appear in the Raw Data section—you can click to expand and see the actual JSON 
response from the MCP tool:

```json
{
  "tables": ["Customers", "Products", "Sales", "SaleDetails", "ServiceTickets"],
  "database": "fitness_db"
}
```

Complete visibility into what data the agent is working with.

**PHASE 2 EXECUTION:**

Tool selected: `base_readQuery`
Arguments: {
  "sql": "SELECT p.ProductType, AVG(CAST(st.ResolutionDate - st.TicketDate AS INT)) 
         as AvgResolutionDays FROM fitness_db.ServiceTickets st JOIN fitness_db.Products p 
         ON st.ProductID = p.ProductID WHERE st.ResolutionDate IS NOT NULL 
         GROUP BY p.ProductType ORDER BY AvgResolutionDays DESC"
}
Rationale: "Calculate average resolution time by product type"

Look at that—we can see the exact SQL being generated. If there's an issue with the 
query logic, you can spot it immediately. No blind trust required.

Raw results stream in... click to inspect:

```json
[
  {"ProductType": "Cardio", "AvgResolutionDays": 8.3},
  {"ProductType": "Strength", "AvgResolutionDays": 5.1},
  {"ProductType": "Accessories", "AvgResolutionDays": 2.7}
]
```

Now comes the beautiful part.

**PHASE 3 EXECUTION:**

Tool selected: `TDA_LLMTask`
Arguments: {
  "task": "Analyze which product categories show quality issues based on ticket 
          volume and resolution time",
  "data": "[resolution time data + ticket counts]"
}
Rationale: "Need LLM reasoning to identify quality patterns beyond just metrics"

The agent is delegating analytical reasoning to a specialized LLM task. You see this 
decision being made explicitly—not hidden behind the curtain.

And here's where transparency becomes trust-building.

**SELF-CORRECTION EVENT:**

Let's say the agent tries to query a table that doesn't exist. Watch what happens.

Tool call: `base_readQuery` with SQL referencing "ProductReturns" table
Error returned: "Table fitness_db.ProductReturns does not exist"

**RECOVERY STRATEGY:**

The Live Status Panel shows:

"Error detected. Initiating recovery: Replanning without ProductReturns table. 
Using ServiceTickets as proxy for quality issues."

New tactical plan: Query ServiceTickets grouped by ProductID to identify high-complaint 
products.

Tool call: `base_readQuery` with corrected SQL
Result: Success

You just watched the agent fail, recognize the failure, replan its approach, and 
succeed—all transparently. This is what builds trust.

In a traditional AI tool, you'd just get a generic error message or worse, a 
hallucinated answer. Here, you see the agent think, execute, detect problems, and 
self-correct.

This is the Live Status Panel. Not just transparency—radical visibility into every 
decision, every tool call, every piece of data, and every recovery.

No black boxes. No guesswork. Complete trust through complete transparency.
```

**Screen Capture Plan:**
- [ ] Complex query input: "Compare service ticket resolution times..."
- [ ] Strategic Plan appears with 4 phases listed
- [ ] Tactical section: Phase 1 executing with `base_tableList` tool
- [ ] Raw Data section: Click to expand JSON response
- [ ] Tactical section: Phase 2 executing with `base_readQuery` showing full SQL
- [ ] Raw Data: Query results JSON display
- [ ] Tactical section: Phase 3 with `TDA_LLMTask` delegation
- [ ] Error scenario: Wrong table name → Error message appears
- [ ] Recovery strategy displayed in Live Status
- [ ] Corrected query execution succeeds
- [ ] Final results rendering in Conversation Panel

**Supporting Materials:**
- Live Status Panel documentation
- Complex query examples
- Self-correction scenarios
- Error handling guide
- Tool execution logs

**Supporting Materials:**
- Live Status Panel documentation
- Example complex queries
- Self-correction examples

---

### 3.2 Capabilities Discovery: Know What's Possible
**Duration:** 2-3 minutes  
**Learning Objectives:**
- Explore available MCP tools
- Understand prompt library organization
- Learn resource enumeration

**Key Topics to Cover:**
- [ ] Capabilities Panel overview
- [ ] MCP Tools tab (automatic discovery)
- [ ] Prompts tab (categorized library)
- [ ] Resources tab (data source visibility)
- [ ] Dynamic updates on configuration changes

**Narration Script:**
```
Before you can trust an agent, you need to know what it can actually do. The Capabilities 
Panel gives you instant visibility into every tool, prompt, and resource your agent has 
access to.

Look at the left panel—three tabs: Tools, Prompts, and Resources.

**TOOLS TAB:**

Click on Tools. This is your complete catalog of MCP tools available in the current profile.

Notice they're organized by category. Let's expand "Database Operations":

- `base_databaseList` - List all databases in the system
- `base_tableList` - List all tables in a database
- `base_tableDDL` - Retrieve table DDL structure
- `base_readQuery` - Execute SELECT queries and return results

Each tool shows:
1. The exact name the agent will use
2. A clear description of what it does
3. Required vs optional arguments (hover to see details)

Expand "Data Quality":

- `qlty_dataProfile` - Profile data quality metrics for a table
- `qlty_findAnomalies` - Detect statistical anomalies in data
- `qlty_validateConstraints` - Check foreign key and constraint violations

And "System Administration":

- `dba_databaseVersion` - Get Teradata system version
- `dba_systemHealth` - Check system resource utilization
- `dba_userActivity` - Monitor active user sessions

This isn't just documentation—it's a real-time inventory of what your agent can do 
right now with the current profile.

**PROMPTS TAB:**

Now click Prompts. These are pre-built, complex workflows that the agent can invoke.

Under "Business Intelligence":

- `base_databaseBusinessDesc` - Generate comprehensive business context for a database
  - Arguments: database_name (required), detail_level (optional)
  - Returns: Business purpose, key entities, common use cases

- `base_tableBusinessDesc` - Explain business meaning of a table
  - Arguments: database_name, table_name (both required)
  - Returns: Table purpose, key columns, business rules

Under "Data Quality":

- `qlty_databaseQuality` - Comprehensive database quality assessment
  - Arguments: database_name (required), include_profiling (optional)
  - Returns: Quality scores, issue summary, recommendations

Under "Administration":

- `dba_databaseHealthAssessment` - Full system health report
  - Arguments: include_recommendations (optional)
  - Returns: Resource usage, performance metrics, alerts

- `dba_userActivityAnalysis` - User behavior and query patterns
  - Arguments: time_range (optional, default: 24h)
  - Returns: Active users, query volumes, resource consumers

These prompts are like specialized team members. Instead of writing complex multi-step 
queries yourself, you invoke a prompt that knows how to gather the right data and 
generate the right analysis.

**RESOURCES TAB:**

Click Resources. This shows data sources and knowledge repositories available to the agent.

You might see:
- Database connections (fitness_db on Teradata)
- API endpoints (if configured)
- Knowledge collections (uploaded documents)
- External tools (if integrated)

**DYNAMIC CAPABILITY UPDATES:**

Now here's the powerful part. Let's say you want to add a new capability.

Go to Setup → MCP Servers → Add New Server.

Maybe you're adding a PostgreSQL database for cross-database analysis. Configure it:

Name: "Analytics PostgreSQL"
Host: analytics-db.company.com
Port: 5432
Path: /mcp

Save it. Add it to your current profile.

Now watch the Capabilities Panel. Click refresh (or it auto-updates).

New tools appear under "Database Operations":
- `postgres_queryExecute`
- `postgres_schemaIntrospect`
- `postgres_tableSample`

The agent immediately knows about these new capabilities. No restart required. No 
reconfiguration. Dynamic discovery.

You can now ask: "Compare revenue trends in our Teradata production database with 
the analytical models in PostgreSQL."

The agent sees both `base_readQuery` (Teradata) and `postgres_queryExecute` (PostgreSQL) 
and knows it can orchestrate cross-database analysis.

**CAPABILITY FILTERING:**

Let's say you want to temporarily disable a tool. Maybe `base_tableDDL` is expensive 
on your system and you want to prevent the agent from using it for routine queries.

Go to Setup → Capabilities Management → Tools.
Find `base_tableDDL` → Toggle "Enabled" to OFF.

Now watch the Capabilities Panel. That tool turns gray and shows "Disabled."

Ask a question that would normally trigger it: "Show me the structure of the Products table."

The agent will use alternative approaches (maybe `qlty_dataProfile` or just query 
INFORMATION_SCHEMA) because it knows `base_tableDDL` is unavailable.

Re-enable it, and it's back in action.

This is dynamic capability management. You control what the agent can do, in real-time, 
without writing code.

The Capabilities Panel isn't just a list—it's your window into the agent's potential. 
Every tool, every prompt, every resource, clearly visible and dynamically managed.

Know your agent. Trust your agent. Control your agent.
```

**Screen Capture Plan:**
- [ ] Capabilities Panel (left side) with three tabs
- [ ] Tools tab: Expand "Database Operations" category showing base_* tools
- [ ] Tool hover showing arguments and descriptions
- [ ] Expand "Data Quality" category showing qlty_* tools
- [ ] Expand "System Administration" showing dba_* tools
- [ ] Switch to Prompts tab
- [ ] Expand "Business Intelligence" showing base_databaseBusinessDesc, base_tableBusinessDesc
- [ ] Prompt detail view showing arguments (required vs optional)
- [ ] Expand "Data Quality" showing qlty_databaseQuality
- [ ] Expand "Administration" showing dba_* prompts
- [ ] Switch to Resources tab showing database connections
- [ ] Setup → MCP Servers → Add New Server (PostgreSQL example)
- [ ] Capabilities Panel refresh showing new postgres_* tools
- [ ] Capability filtering: Disable base_tableDDL
- [ ] Tool turns gray in Capabilities Panel
- [ ] Query execution using alternative tool
- [ ] Re-enable tool demonstration

**Supporting Materials:**
- MCP Tools complete reference
- Prompt library documentation
- Dynamic capability management guide
- MCP server configuration examples
- Tool filtering best practices

**Supporting Materials:**
- MCP Tools documentation
- Prompt library reference
- Capability discovery guide

---

### 3.3 Context Management: Control Agent Memory
**Duration:** 3-4 minutes  
**Learning Objectives:**
- Master turn activation/deactivation
- Understand context purge vs selective memory
- Learn query replay functionality

**Key Topics to Cover:**
- [ ] Turn-level context control (checkboxes)
- [ ] Full Context vs Turn Summaries modes
- [ ] Context purge for memory reset
- [ ] Query replay for alternative approaches
- [ ] Context indicator real-time status

**Narration Script:**
```
One of the most powerful yet underappreciated features of conversational AI is context 
management—controlling what the agent remembers and when.

Uderia gives you surgical precision over agent memory. Let's explore.

**TURN HISTORY PANEL:**

Look at the Session History panel below the conversation. Every query-response pair 
is a "turn." Each turn has a checkbox on the left.

Here's our conversation so far:

Turn 1: ✓ "What are the top 5 products by revenue?"
Turn 2: ✓ "Show customer demographics for those products"
Turn 3: ✓ "Which states have the highest sales?"
Turn 4: ✓ "What's the average ticket resolution time?"

All checkboxes are checked—meaning all turns are active in the agent's context.

**SELECTIVE MEMORY:**

Let's say we want to ask: "What are the top products?" again, but we don't want the 
agent confused by our previous product question in Turn 1.

Uncheck Turn 1. Watch the context indicator in the top right—it updates: "3 turns active."

Now ask: "What are the top selling products this week?"

The agent treats this as a fresh question. It doesn't reference Turn 1's results because 
that turn is deactivated. But it still remembers Turns 2-4 if needed.

**WHY THIS MATTERS:**

Imagine you're exploring data and you take a wrong turn. You asked about "Product X" 
but meant "Product Y." Traditional AI would carry that mistake through the entire 
conversation.

With Uderia, uncheck that wrong turn, and it's like it never happened. The conversation 
continues cleanly.

**CONTEXT MODES:**

Now look at the top bar—there's a toggle: "Full Context" vs "Turn Summaries."

**Full Context Mode (default):**
Every active turn's complete text is sent to the LLM. High token usage, maximum accuracy.

**Turn Summaries Mode:**
Only summaries of previous turns are sent. Lower token cost, slightly less detailed context.

Let's switch to Turn Summaries mode and ask: "What patterns do you see across our 
conversation?"

The agent receives:
- Turn 1 summary: "User asked for top products by revenue"
- Turn 2 summary: "User requested customer demographics"
- Turn 3 summary: "User inquired about geographic sales distribution"
- Turn 4 summary: "User asked about service ticket resolution times"

It can still reason about the conversation flow, but uses 70% fewer tokens.

For long exploratory sessions where you're asking dozens of questions, Turn Summaries 
mode saves significant costs while maintaining conversation continuity.

**CONTEXT PURGE:**

Sometimes you need a completely fresh start without creating a new session (which loses 
your tool results and history).

Click "Purge Context."

A confirmation appears: "This will deactivate all turns. Continue?"

Confirm.

Every checkbox in Turn History unchecks. The context indicator shows: "0 turns active."

Now the agent has no conversational memory—every query is treated as brand new. But 
your session history is still there for you to review, and you can reactivate turns 
selectively.

**QUERY REPLAY:**

Here's a powerful workflow. Let's say Turn 2 gave us interesting results, but we want 
to explore a different angle.

Click the three-dot menu next to Turn 2 → "Replay Query."

The original question appears in the input box: "Show customer demographics for those 
products."

But now we can modify it: "Show customer demographics AND purchasing patterns for 
those products."

Hit enter. The agent executes a new query with the same context as Turn 2 (Turn 1 is 
still active), but with your enhanced question. This becomes Turn 5.

You just explored an alternative path without losing your original results.

**CONTEXT INDICATOR:**

The top right shows real-time context status:

"4/5 turns active (2,340 tokens)"

This tells you:
- 4 out of 5 turns are providing context
- Current context size is 2,340 tokens
- You can see exactly how much context you're sending to the LLM

**ADVANCED USE CASE:**

Let's say you're doing a complex analysis with 20 turns. Turns 1-5 were data exploration. 
Turns 6-15 were deep analysis. Turns 16-20 are your final synthesis.

You want to create a clean summary without the exploratory noise.

Deactivate Turns 1-5. Keep Turns 6-20 active.

Ask: "Summarize our key findings."

The agent generates a summary based only on the deep analysis and final synthesis, 
without the messy exploration phase cluttering the context.

This is surgical control over agent memory. Context as a tool, not a limitation.

No other platform gives you this level of precision. Uderia treats context management 
as a first-class feature because in real-world workflows, controlling what the agent 
remembers is just as important as what it can do.

Memory precision. Cost control. Exploratory freedom. All in your hands.
```

**Screen Capture Plan:**
- [ ] Session History panel showing 4 turns with checkboxes (all checked)
- [ ] Context indicator showing "4 turns active"
- [ ] Uncheck Turn 1 → Context indicator updates to "3 turns active"
- [ ] New query asked with Turn 1 deactivated
- [ ] Context mode toggle: Switch from "Full Context" to "Turn Summaries"
- [ ] Token count comparison (Full Context: 4,200 tokens vs Turn Summaries: 1,300 tokens)
- [ ] Context Purge button → Confirmation dialog
- [ ] All checkboxes unchecked after purge
- [ ] Context indicator showing "0 turns active"
- [ ] Turn 2 three-dot menu → "Replay Query"
- [ ] Modified query in input box
- [ ] New Turn 5 executes with enhanced question
- [ ] Complex scenario: 20 turns displayed, selectively activate Turns 6-20
- [ ] Summary query generates clean results

**Supporting Materials:**
- Context management best practices
- Token optimization guide
- Turn Summaries vs Full Context comparison
- Advanced exploration workflows
- Cost optimization through context control

**Supporting Materials:**
- Context management guide
- Advanced context strategies
- Use case examples

---

### 3.4 System Customization: Shape Agent Behavior
**Duration:** 3-4 minutes  
**Learning Objectives:**
- Edit system prompts for custom behavior
- Test baseline LLM without tools
- Manage capability enable/disable

**Key Topics to Cover:**
- [ ] System Prompt Editor access
- [ ] Per-model instruction customization
- [ ] Save and reset capabilities
- [ ] Direct Model Chat for baseline testing
- [ ] Dynamic capability management (tools/prompts)

**Narration Script:**
```
Transparency isn't just about seeing what the agent does—it's about controlling how 
it behaves. Uderia gives you deep customization capabilities that most platforms hide 
behind proprietary walls.

**SYSTEM PROMPT EDITOR:**

Go to Setup → Advanced → System Prompts.

You're looking at the actual system instructions that guide the agent's behavior. 
These are the foundational prompts that shape how the agent reasons, plans, and executes.

You'll see prompts organized by provider:

- MASTER_SYSTEM_PROMPT (Universal - all providers)
- GOOGLE_MASTER_SYSTEM_PROMPT (Gemini-specific optimizations)
- OLLAMA_MASTER_SYSTEM_PROMPT (Local model adaptations)

Click "Edit" on MASTER_SYSTEM_PROMPT.

Here's what you see:

```
You are an enterprise data intelligence agent with access to tools and knowledge 
repositories. Your role is to:

1. Understand user queries and decompose them into strategic phases
2. Select the most appropriate tools for each phase
3. Execute with precision and self-correct when errors occur
4. Provide structured, actionable insights

When planning:
- Break complex requests into clear phases
- Identify required tools before execution
- Consider data dependencies between phases
- Anticipate potential errors

[... more instructions ...]
```

This is the brain of your agent. And you can edit it.

Let's say you want the agent to be more verbose about its reasoning. Add this:

```
When selecting tools, always explain:
- Why this tool is the best choice
- What alternatives you considered
- What you expect the tool to return
```

Save it. Now ask a question: "What are the top revenue products?"

Watch the Live Status Panel tactical section. Instead of just:

"Tool selected: base_readQuery"

You now see:

"Tool selected: base_readQuery  
Rationale: This tool provides direct SQL execution, which is optimal for aggregating 
revenue data. Alternatives considered: base_tableList (insufficient - only shows structure), 
qlty_dataProfile (unnecessary - not a data quality question). Expected return: Table 
with ProductName and Revenue columns, sorted descending."

You just customized the agent's communication style by editing its system prompt.

**PROVIDER-SPECIFIC PROMPTS:**

Google's Gemini models work differently than Claude or GPT-4. Their system prompt has 
optimizations like:

```
When using function calling, always structure arguments as clear JSON.
Gemini excels at parallel tool execution—identify opportunities to call multiple 
tools simultaneously.
```

These provider-specific tunings ensure optimal performance on each model's strengths.

**SAVE AND RESET:**

Made changes you want to keep? Click "Save to Overrides."

This stores your custom prompt in the `prompt_overrides/` directory. Even if you update 
Uderia, your customizations persist.

Want to revert to defaults? Click "Reset to Default."

**DIRECT MODEL CHAT:**

Now let's test the raw LLM without any tools or agent logic.

Go to Setup → Advanced → Direct Model Chat.

This is a baseline test environment. You're talking directly to the LLM—no MCP tools, 
no strategic planning, no agent orchestration. Just pure model reasoning.

Ask: "What are the top revenue products?"

The model responds:

"I don't have access to your database or real-time data. To answer this, I would need 
you to provide the data or run a query against your system."

This is the baseline. Now switch back to the agent (with tools enabled).

Ask the same question: "What are the top revenue products?"

The agent responds with actual data from your fitness_db using `base_readQuery`.

This comparison shows you exactly what the agent orchestration layer is adding—tool 
access, context management, and execution planning.

**DYNAMIC CAPABILITY MANAGEMENT:**

Now let's control which tools the agent can use.

Go to Setup → Capabilities → Tools.

You see the full list:
- ✓ base_databaseList (Enabled)
- ✓ base_tableList (Enabled)
- ✓ base_tableDDL (Enabled)
- ✓ base_readQuery (Enabled)

Let's run an experiment. Disable `base_readQuery`.

Click the toggle next to it → Confirm "Disable base_readQuery?"

Now it shows:
- ✗ base_readQuery (Disabled)

Ask: "What are the top 5 products by revenue?"

Watch the Live Status Panel. The agent plans:

"Phase 1: Need to query revenue data... ERROR: base_readQuery is unavailable.
Replanning: Attempting alternative approach using base_tableList to identify structure, 
then TDA_LLMTask to generate insights from schema..."

The query fails or produces a workaround because the optimal tool is disabled.

Re-enable `base_readQuery`. Toggle it back on.

Ask the same question again. Now it succeeds instantly with the proper tool.

This capability management lets you:
- Test agent behavior without specific tools
- Restrict expensive tools for cost control
- Disable problematic tools during debugging
- Phase in new tools gradually

All without restarting the platform or editing code.

**PROMPT MANAGEMENT:**

The same applies to prompts. Go to Setup → Capabilities → Prompts.

Disable `base_databaseBusinessDesc`.

Now if you ask: "Give me a business overview of the fitness_db database," the agent 
can't use that pre-built prompt. It will fall back to manual investigation with tools 
like `base_tableList` and `base_tableDDL`.

Re-enable it, and the efficient pre-built workflow becomes available again.

**WHY THIS MATTERS:**

Most AI platforms treat their prompts and tool configurations as proprietary secrets. 
You get what they give you.

Uderia gives you the keys. Edit the system prompt. Test the raw model. Enable or 
disable capabilities dynamically. Shape the agent to your exact needs.

This isn't just transparency—it's control. Your agent. Your rules. Your customization.

Trust through visibility. Power through customization.
```

**Screen Capture Plan:**
- [ ] Setup → Advanced → System Prompts menu
- [ ] System Prompt Editor showing MASTER_SYSTEM_PROMPT
- [ ] Edit mode: Adding custom reasoning verbosity instructions
- [ ] Save changes
- [ ] Query execution showing enhanced tactical reasoning output
- [ ] Provider-specific prompts: GOOGLE_MASTER_SYSTEM_PROMPT example
- [ ] "Save to Overrides" and "Reset to Default" buttons
- [ ] Setup → Advanced → Direct Model Chat
- [ ] Direct chat query (no tools) → Generic LLM response
- [ ] Switch back to agent mode → Same query with actual data results
- [ ] Setup → Capabilities → Tools management
- [ ] Toggle base_readQuery to Disabled
- [ ] Query execution failing/workaround due to disabled tool
- [ ] Live Status Panel showing "base_readQuery unavailable" message
- [ ] Re-enable base_readQuery
- [ ] Query succeeds with proper tool
- [ ] Setup → Capabilities → Prompts management
- [ ] Disable base_databaseBusinessDesc prompt
- [ ] Query using fallback approach
- [ ] Re-enable prompt

**Supporting Materials:**
- System prompt customization guide
- Provider-specific optimization examples
- Direct Model Chat use cases
- Capability management best practices
- Tool filtering strategies
- Prompt override documentation

**Supporting Materials:**
- System prompt examples
- Customization best practices
- Developer mode guide

---

### 3.5 Execution Monitoring: Track Every Task
**Duration:** 2-3 minutes  
**Learning Objectives:**
- Monitor cross-source workload tracking
- Review execution logs and tool history
- Learn task control operations

**Key Topics to Cover:**
- [ ] Executions View dashboard
- [ ] Real-time task list (running, completed, failed)
- [ ] Detailed execution logs
- [ ] Tool invocation history with arguments
- [ ] Task control (cancel, retry)

**Narration Script:**
```
Transparency doesn't stop at the current conversation. Uderia gives you a complete 
view of all agent activity across your entire platform—past, present, and running. 
Welcome to the Executions View.

Click on "Executions" in the main navigation.

**THE EXECUTIONS DASHBOARD:**

You're looking at mission control for all agent tasks—whether they came from the UI, 
REST API, Airflow DAGs, or Flowise workflows.

The dashboard shows three sections:

**1. ACTIVE TASKS (Real-Time Monitoring):**

At the top, you see currently running tasks:

┌─────────────────────────────────────────────────────────────┐
│ Task ID: task_7f3a2b   Status: RUNNING   Progress: 65%      │
│ Query: "Analyze quarterly revenue trends by product category"│
│ Session: Revenue Analysis Q4   Started: 2 minutes ago       │
│ Current Phase: Executing data aggregation (Phase 2 of 3)    │
│ Tools Used: base_tableList, base_readQuery                  │
│ [View Live Status] [Cancel Task]                            │
└─────────────────────────────────────────────────────────────┘

Click "View Live Status"—it opens that task's Live Status Panel in a modal. You can 
watch it execute in real-time even though it was submitted via API, not the UI.

You see:
- Strategic plan: Phase 1 ✓ Complete, Phase 2 → Running, Phase 3 Pending
- Current tool call: `base_readQuery` executing complex aggregation SQL
- Token count: 3,200 input, 1,800 output (so far)
- Estimated cost: $0.023

**2. COMPLETED TASKS (Historical Execution Log):**

Below active tasks, you see the completed execution history:

┌─────────────────────────────────────────────────────────────┐
│ ✓ Task ID: task_6a8d1c   Status: COMPLETED   Duration: 12s  │
│ Query: "What are the top 5 products by revenue?"            │
│ Session: Morning Batch Analysis   Finished: 5 minutes ago   │
│ Tools Used: base_readQuery, TDA_FinalReport                 │
│ Tokens: 1,250 in / 340 out   Cost: $0.008                   │
│ [View Execution Log] [Replay Query]                         │
└─────────────────────────────────────────────────────────────┘

Click "View Execution Log." A detailed drill-down appears:

**EXECUTION LOG DETAIL:**

```
Task: task_6a8d1c
Query: "What are the top 5 products by revenue?"
Session: Morning Batch Analysis (abc-123-def)
Profile: @PROD (Claude Sonnet 3.5 + Teradata MCP)
Started: 2025-12-07 09:15:23 UTC
Completed: 2025-12-07 09:15:35 UTC
Duration: 12.4 seconds

--- STRATEGIC PLAN ---
Phase 1: Execute revenue aggregation query
Phase 2: Generate final report with formatting

--- EXECUTION TRACE ---

[09:15:23] Planning Phase
  - LLM Call: Strategic Planner (Claude Sonnet 3.5)
  - Tokens: 1,100 input / 85 output
  - Cost: $0.0035
  - Result: 2-phase plan generated

[09:15:25] Phase 1 Execution
  - Tool: base_readQuery
  - Arguments: {
      "sql": "SELECT p.ProductName, p.Brand, SUM(sd.Quantity * sd.UnitPrice) 
              as Revenue FROM fitness_db.Products p JOIN fitness_db.SaleDetails sd 
              ON p.ProductID = sd.ProductID JOIN fitness_db.Sales s ON sd.SaleID = s.SaleID 
              WHERE EXTRACT(MONTH FROM s.SaleDate) = EXTRACT(MONTH FROM CURRENT_DATE) 
              GROUP BY p.ProductName, p.Brand ORDER BY Revenue DESC LIMIT 5"
    }
  - Execution Time: 3.2s
  - Result: 5 rows returned
  - Data Preview: [{"ProductName": "Treadmill Pro 3000", "Revenue": 45230}, ...]

[09:15:29] Phase 2 Execution
  - Tool: TDA_FinalReport
  - Arguments: {
      "data": [query results],
      "format": "table_with_summary"
    }
  - LLM Call: Report Formatter (Claude Sonnet 3.5)
  - Tokens: 150 input / 255 output
  - Cost: $0.0045
  - Result: Formatted HTML response generated

[09:15:35] Task Completed Successfully

TOTAL TOKENS: 1,250 input / 340 output
TOTAL COST: $0.008
```

This is forensic-level detail. You can see:
- Exact timing of every step
- Every tool invocation with full arguments
- Every LLM call with token counts
- SQL queries that were executed
- Data that was returned
- Complete cost breakdown

If something went wrong, you know exactly where and why.

**3. FAILED TASKS (Error Investigation):**

Let's look at a failed task:

┌─────────────────────────────────────────────────────────────┐
│ ✗ Task ID: task_2c5e9f   Status: FAILED   Duration: 8s      │
│ Query: "Compare sales across all regions"                   │
│ Session: Regional Analysis   Failed: 1 hour ago             │
│ Error: Table 'fitness_db.Regions' does not exist            │
│ [View Error Log] [Retry with Corrections]                   │
└─────────────────────────────────────────────────────────────┘

Click "View Error Log":

```
[10:42:15] Phase 1 Execution
  - Tool: base_readQuery
  - Arguments: {"sql": "SELECT * FROM fitness_db.Regions ..."}
  - ERROR: SQL execution failed
  - Error Message: "Table 'fitness_db.Regions' does not exist"
  - Recovery Attempted: Yes
  - Recovery Strategy: Replanning to use Customers.State column instead
  - Recovery Status: FAILED - insufficient data for complete regional breakdown

[10:42:23] Task Failed
  - Reason: Unable to complete query with available tables
  - Suggestion: Create Regions table or modify query to use City/State from Customers
```

You can see the agent tried to self-correct, but the recovery failed. Now you know 
exactly what to fix.

Click "Retry with Corrections"—it opens the query editor with the original question, 
and you can modify it: "Compare sales across all states using customer location data."

**TASK CANCELLATION:**

Let's say you have a runaway query that's taking too long.

In the Active Tasks section, find the task → Click "Cancel Task."

Confirmation: "Are you sure? This will stop execution and free resources."

Confirm.

The task status changes to "CANCELLED" and moves to the completed section:

┌─────────────────────────────────────────────────────────────┐
│ ⊗ Task ID: task_9b3f1a   Status: CANCELLED   Duration: 45s  │
│ Query: "Full database quality scan on all tables"           │
│ Session: System Audit   Cancelled: Just now                 │
│ Reason: Manual cancellation by user                         │
│ Progress at Cancellation: 30% (Phase 1 of 4 completed)      │
└─────────────────────────────────────────────────────────────┘

Graceful shutdown. Resources freed. Partial results saved if applicable.

**CROSS-SOURCE VISIBILITY:**

Here's what makes this powerful. Tasks from ALL sources appear here:

- UI-initiated queries (your interactive conversations)
- REST API calls (from Postman, cURL, custom apps)
- Airflow DAGs (scheduled batch jobs)
- Flowise workflows (chatbot interactions)

Everything in one place. One unified execution log.

You can filter by:
- Session ID
- Profile used
- Status (running, completed, failed, cancelled)
- Date range
- User (in multi-user environments)

**OPERATIONAL INTELLIGENCE:**

This isn't just debugging—it's operational intelligence.

- Which queries are most expensive? (Sort by cost)
- Which sessions have the most failures? (Filter by failed status)
- What's the average execution time for revenue queries? (Filter by query pattern)
- Which MCP tools are used most frequently? (Aggregate tool usage)

The Executions View turns your agent activity into actionable operational data.

Every task. Every tool. Every token. Every error. Complete transparency across your 
entire AI operations.

This is production-grade execution monitoring. Trust through visibility. Control through insight.
```

**Screen Capture Plan:**
- [ ] Executions View navigation (main menu)
- [ ] Dashboard with three sections: Active, Completed, Failed
- [ ] Active task card showing progress bar and current phase
- [ ] Click "View Live Status" → Modal with real-time execution
- [ ] Strategic plan showing Phase 1 ✓, Phase 2 Running, Phase 3 Pending
- [ ] Tool execution details (base_readQuery in progress)
- [ ] Token count and cost tracking (live updates)
- [ ] Completed tasks list with multiple entries
- [ ] Click "View Execution Log" on completed task
- [ ] Detailed execution trace with timestamps
- [ ] Tool invocations with full arguments (SQL queries visible)
- [ ] Token and cost breakdown per phase
- [ ] Failed task card with error message
- [ ] Click "View Error Log" → Detailed failure analysis
- [ ] Recovery attempt details
- [ ] "Retry with Corrections" button
- [ ] Active task cancellation: Click "Cancel Task" → Confirmation
- [ ] Task status changes to CANCELLED
- [ ] Filter options: Session, Profile, Status, Date range
- [ ] Cross-source task list: UI, API, Airflow labels
- [ ] Sort by cost (most expensive queries at top)

**Supporting Materials:**
- Execution monitoring guide
- Task lifecycle documentation
- Error investigation workflows
- Operational analytics examples
- Cross-source tracking reference
- Performance optimization guide

**Supporting Materials:**
- Execution monitoring guide
- Task lifecycle documentation
- Error debugging examples

---

## Module 4: EFFICIENT - The Fusion Optimizer
**Goal:** Showcase the revolutionary optimization engine and self-learning capabilities

### 4.1 Strategic & Tactical Planning Architecture
**Duration:** 4-5 minutes  
**Learning Objectives:**
- Understand multi-layered planning process
- See strategic meta-plans in action
- Grasp recursive delegation concept

**Key Topics to Cover:**
- [ ] Strategic Planner (high-level meta-plan)
- [ ] Tactical Execution (best next action)
- [ ] Recursive delegation for complex problems
- [ ] Phase-by-phase breakdown visualization
- [ ] Plan vs execution distinction

**Narration Script:**
```
Welcome to the heart of Uderia—the Fusion Optimizer. This is what transforms a simple 
LLM wrapper into an enterprise-grade AI orchestration engine.

Most AI tools execute queries reactively: user asks, model responds, repeat. No planning. 
No optimization. No intelligence in the execution itself.

Uderia's Fusion Optimizer uses a revolutionary multi-layered architecture that plans 
strategically, executes tactically, and optimizes continuously.

Let's see it in action with a complex request:

"Analyze our fitness equipment business: identify product categories with declining 
sales, investigate customer service patterns for those products, and recommend 
actionable improvements."

Watch the Live Status Panel.

**STRATEGIC PLANNING LAYER:**

The agent doesn't just start executing. First, it generates a meta-plan—a high-level 
strategic blueprint:

```
STRATEGIC META-PLAN:

Phase 1: Identify product categories with declining sales
  - Requires: Sales and SaleDetails tables
  - Expected output: List of product categories with negative growth trends
  - Dependencies: None (can execute immediately)

Phase 2: Analyze service ticket patterns for declining products
  - Requires: ServiceTickets table + results from Phase 1
  - Expected output: Ticket volume, resolution times, issue types
  - Dependencies: Phase 1 results

Phase 3: Correlate sales decline with service issues
  - Requires: Results from Phase 1 and Phase 2
  - Expected output: Correlation analysis, root cause insights
  - Dependencies: Phases 1 and 2 complete

Phase 4: Generate actionable recommendations
  - Requires: All previous analysis
  - Expected output: Prioritized improvement strategies
  - Dependencies: All prior phases
```

This is strategic thinking. The agent has mapped out the entire workflow before 
executing a single tool.

**TACTICAL EXECUTION LAYER:**

Now watch Phase 1 execute.

The strategic planner delegates to the tactical executor: "Complete Phase 1."

The tactical layer asks: "What is the single best next action to advance Phase 1?"

Tactical Decision:
```
Goal: Identify product categories with declining sales
Best action: Execute SQL query comparing current quarter vs previous quarter sales by ProductType
Selected tool: base_readQuery
Arguments: {
  "sql": "SELECT p.ProductType, 
                 SUM(CASE WHEN EXTRACT(QUARTER FROM s.SaleDate) = EXTRACT(QUARTER FROM CURRENT_DATE) 
                     THEN sd.Quantity * sd.UnitPrice ELSE 0 END) as CurrentQ,
                 SUM(CASE WHEN EXTRACT(QUARTER FROM s.SaleDate) = EXTRACT(QUARTER FROM CURRENT_DATE)-1 
                     THEN sd.Quantity * sd.UnitPrice ELSE 0 END) as PrevQ,
                 ((CurrentQ - PrevQ) / PrevQ * 100) as GrowthPct
          FROM fitness_db.Products p 
          JOIN fitness_db.SaleDetails sd ON p.ProductID = sd.ProductID
          JOIN fitness_db.Sales s ON sd.SaleID = s.SaleID
          WHERE s.SaleDate >= DATE '2024-07-01'
          GROUP BY p.ProductType
          ORDER BY GrowthPct ASC"
}
Rationale: Single query captures both current and previous quarter data, calculates 
growth percentage, identifies declining categories efficiently.
```

This is tactical precision—choosing the optimal tool and approach for this specific step.

Results return:
```json
[
  {"ProductType": "Cardio", "CurrentQ": 125000, "PrevQ": 180000, "GrowthPct": -30.5},
  {"ProductType": "Accessories", "CurrentQ": 45000, "PrevQ": 52000, "GrowthPct": -13.5},
  {"ProductType": "Strength", "CurrentQ": 200000, "PrevQ": 190000, "GrowthPct": 5.3}
]
```

Phase 1 complete. Cardio equipment is declining 30%, Accessories 13%.

**RECURSIVE DELEGATION:**

Now Phase 2 begins: "Analyze service ticket patterns for declining products."

But this phase is complex—it requires multiple steps:
1. Get service tickets for Cardio and Accessories products
2. Calculate average resolution times
3. Categorize issue types
4. Identify patterns

Watch what happens. The strategic planner doesn't try to handle this monolithically. 
It delegates Phase 2 to a NEW subordinate planner instance.

A recursive sub-plan appears:
```
SUB-PLAN for Phase 2:
  2.1: Retrieve product IDs for Cardio and Accessories categories
  2.2: Query ServiceTickets for those product IDs
  2.3: Calculate resolution time statistics
  2.4: Extract and categorize issue descriptions
```

This sub-planner operates independently, executes its sub-phases, and returns consolidated 
results to the parent planner.

The parent doesn't micromanage. It delegated a complex sub-task to a specialized instance, 
which broke it down further and solved it.

**This is recursive intelligence.**

Sub-Plan 2.1 executes:
```
Tool: base_readQuery
SQL: SELECT ProductID FROM fitness_db.Products WHERE ProductType IN ('Cardio', 'Accessories')
Result: 47 product IDs identified
```

Sub-Plan 2.2 executes:
```
Tool: base_readQuery  
SQL: SELECT ProductID, COUNT(*) as TicketCount, 
            AVG(CAST(ResolutionDate - TicketDate AS INT)) as AvgResolutionDays,
            IssueDescription
     FROM fitness_db.ServiceTickets
     WHERE ProductID IN (list of 47 IDs)
     GROUP BY ProductID
Result: Service patterns retrieved
```

Sub-Plan 2.3 executes:
```
Tool: TDA_LLMTask
Task: "Analyze resolution time distribution and identify outliers"
Result: Cardio products average 8.3 days to resolve vs 2.7 for Accessories
```

Sub-Plan 2.4 executes:
```
Tool: TDA_LLMTask
Task: "Categorize issue descriptions into common themes"
Result: Top issues for Cardio: Motor failures (45%), Belt wear (30%), Electronic issues (25%)
```

Sub-plan complete. Results return to parent Phase 2. Phase 2 marks complete.

**HIERARCHICAL PROBLEM SOLVING:**

Phase 3 begins: "Correlate sales decline with service issues."

This phase uses results from BOTH Phase 1 and Phase 2. The strategic planner has those 
results in context.

Tactical execution:
```
Tool: TDA_LLMTask
Task: "Analyze correlation between 30% Cardio sales decline and 8.3-day average 
       service resolution time with 45% motor failure rate. Determine causation likelihood."
Result: Strong correlation. Customer reviews and repeat purchase rates show service 
        experience directly impacts sales. Motor failures driving negative sentiment.
```

Phase 3 complete.

Phase 4 begins: "Generate actionable recommendations."

```
Tool: TDA_FinalReport
Arguments: All prior phase results
Task: Synthesize insights into prioritized recommendations
Result: 
  1. URGENT: Address motor quality issues in Cardio line (root cause)
  2. HIGH: Reduce service resolution time target to <5 days (customer experience)
  3. MEDIUM: Implement proactive outreach for products >6 months old (prevention)
```

Final answer delivered to the user.

**WHAT JUST HAPPENED:**

A complex, ambiguous question was decomposed into:
- A 4-phase strategic meta-plan
- Tactical tool selections for each phase
- A recursive sub-plan for complex Phase 2
- Data gathering, analysis, correlation, and synthesis
- Actionable recommendations

All orchestrated autonomously. All visible in real-time. All optimized for efficiency.

This isn't a chatbot. This is an enterprise AI orchestration engine.

The Fusion Optimizer: Strategic planning meets tactical execution. Recursive delegation 
meets hierarchical problem-solving.

This is why Uderia can handle enterprise complexity while other tools fail at anything 
beyond simple Q&A.

Intelligence in the architecture. Not just in the model.
```

**Screen Capture Plan:**
- [ ] Complex multi-part query input
- [ ] Strategic Meta-Plan appears with 4 phases and dependencies mapped
- [ ] Phase 1 tactical execution: base_readQuery with sales comparison SQL
- [ ] Phase 1 results: Declining product categories identified
- [ ] Phase 2 begins: "Analyze service patterns" 
- [ ] RECURSIVE delegation indicator appears
- [ ] Sub-plan appears: 2.1, 2.2, 2.3, 2.4 sub-phases
- [ ] Sub-plan execution: Multiple base_readQuery and TDA_LLMTask calls
- [ ] Sub-plan results consolidated and returned to parent
- [ ] Phase 2 complete checkmark
- [ ] Phase 3 execution: Correlation analysis using Phase 1 + Phase 2 data
- [ ] Phase 4 execution: TDA_FinalReport with synthesized recommendations
- [ ] Final formatted report in Conversation Panel
- [ ] Execution summary: 4 phases, 8 tool calls, 1 recursive delegation

**Supporting Materials:**
- Fusion Optimizer architecture diagram
- Strategic vs Tactical planning comparison
- Recursive delegation examples
- Complex query patterns
- Phase dependency visualization

**Supporting Materials:**
- Fusion Optimizer architecture diagram
- Complex query examples
- Planning algorithm documentation

---

### 4.2 RAG Self-Learning System: Continuous Improvement
**Duration:** 4-5 minutes  
**Learning Objectives:**
- Understand automatic case capture
- Learn efficiency analysis and champion selection
- See few-shot learning injection in action

**Key Topics to Cover:**
- [ ] Automatic case archiving after successful sessions
- [ ] Efficiency scoring (token reduction, fast paths)
- [ ] Champion strategy selection
- [ ] Few-shot learning injection at planning time
- [ ] Asynchronous processing (zero latency)

**Narration Script:**
```
The Fusion Optimizer is powerful. But here's what makes it revolutionary—it learns 
from every success. Welcome to Uderia's self-improving RAG system.

Most AI agents execute each query in isolation. They don't remember what worked. They 
don't learn from past successes. They reinvent the wheel every single time.

Uderia's RAG (Retrieval-Augmented Generation) system turns every successful interaction 
into organizational knowledge. The agent gets smarter with every query you run.

Let's see how.

**AUTOMATIC CASE CAPTURE:**

Go to Intelligence → RAG Collections.

You're looking at the "Planner Repository"—a knowledge base of successful execution 
patterns. Every completed session that succeeded is automatically analyzed and archived here.

Let's look at a captured case. Click on "Revenue Analysis - Top Products by Category."

```
CASE DETAILS:

Original Query: "What are the top 5 products by revenue in each category?"

Strategic Plan:
  Phase 1: Execute revenue aggregation with category grouping
  Phase 2: Format results with clear category breakdown

Tool Execution Trace:
  1. base_readQuery
     SQL: SELECT p.ProductType, p.ProductName, p.Brand, 
                 SUM(sd.Quantity * sd.UnitPrice) as Revenue,
                 RANK() OVER (PARTITION BY p.ProductType ORDER BY Revenue DESC) as Rank
          FROM fitness_db.Products p
          JOIN fitness_db.SaleDetails sd ON p.ProductID = sd.ProductID
          JOIN fitness_db.Sales s ON sd.SaleID = s.SaleID
          WHERE Rank <= 5
          GROUP BY p.ProductType, p.ProductName, p.Brand
     Execution Time: 1.8s
     Result: 15 rows (5 per category)
  
  2. TDA_FinalReport
     Format: Grouped table by category
     Result: Clean formatted output

Token Usage:
  Strategic Planning: 1,200 input / 95 output
  Tactical Execution: 850 input / 120 output
  Total: 2,050 input / 215 output (2,265 total)

Cost: $0.0112

Efficiency Score: 94/100
  - Optimal tool selection: ✓
  - Minimal token usage: ✓
  - Single-pass execution: ✓
  - No errors or retries: ✓

Champion Case: YES (lowest token count for this query pattern)
```

This entire successful workflow is now stored as a reusable pattern.

**EFFICIENCY ANALYSIS:**

Notice the "Efficiency Score: 94/100." The RAG system analyzes every case for optimization 
opportunities:

- **Token Efficiency:** Did it use minimal tokens to achieve the goal?
- **Execution Efficiency:** Single-pass or multiple retries?
- **Tool Selection:** Optimal tool choices or redundant calls?
- **Strategic Planning:** Direct path or unnecessary intermediate phases?

Cases are ranked. The most efficient solution for each query pattern becomes a "Champion Case."

Look at the list—you'll see champion badges (🏆) next to the best examples.

**CHAMPION STRATEGY SELECTION:**

Let's say we have three cases for "top revenue queries":

1. Revenue by Product (Champion 🏆) - 2,265 tokens, 1.8s, score 94
2. Revenue by Category - 3,100 tokens, 3.2s, score 78  
3. Revenue with Customer Analysis - 5,800 tokens, 7.5s, score 65

Case 1 is the champion—most efficient for straightforward revenue queries.

When a new similar query comes in, the RAG system will inject Case 1 as a few-shot 
example to guide the strategic planner.

**FEW-SHOT LEARNING INJECTION:**

Now let's see this in action. Ask a similar question:

"Show me the top revenue products by brand this month."

Watch the Live Status Panel during strategic planning.

You'll see a new section: "RAG-RETRIEVED CONTEXT"

```
Similar Past Cases Retrieved:

1. Revenue Analysis - Top Products by Category (similarity: 0.89)
   - Strategy: Single aggregation query with grouping
   - Tools: base_readQuery → TDA_FinalReport
   - Tokens: 2,265 | Cost: $0.0112 | Duration: 1.8s
   - Key pattern: Use RANK() window function for top-N per group

2. Monthly Revenue Trends (similarity: 0.76)
   - Strategy: Time-based filtering with SUM aggregation
   - Tools: base_readQuery → TDA_FinalReport
   - Tokens: 1,980 | Cost: $0.0095 | Duration: 1.5s
   - Key pattern: EXTRACT(MONTH FROM SaleDate) for current month filter
```

The strategic planner now has these champion examples as guidance. It learns:
- Use RANK() for top-N per group (from Case 1)
- Use EXTRACT(MONTH) for monthly filtering (from Case 2)
- Combine both patterns for this query

Strategic plan generated:
```
Phase 1: Execute revenue query by brand for current month using optimized SQL pattern
  Tool: base_readQuery
  SQL: SELECT p.Brand, p.ProductName,
              SUM(sd.Quantity * sd.UnitPrice) as Revenue,
              RANK() OVER (PARTITION BY p.Brand ORDER BY Revenue DESC) as Rank
       FROM fitness_db.Products p
       JOIN fitness_db.SaleDetails sd ON p.ProductID = sd.ProductID  
       JOIN fitness_db.Sales s ON sd.SaleID = s.SaleID
       WHERE EXTRACT(MONTH FROM s.SaleDate) = EXTRACT(MONTH FROM CURRENT_DATE)
         AND Rank <= 5
       GROUP BY p.Brand, p.ProductName

Phase 2: Format results
  Tool: TDA_FinalReport
```

Look at that—the agent learned the RANK() pattern from past success. It didn't waste 
time exploring alternative approaches. It went straight to the proven champion strategy.

Execution completes.

Token usage: 2,180 total (85 fewer than the first time we solved this pattern)
Cost: $0.0106 (saved $0.0006)
Duration: 1.6s (0.2s faster)

**CONTINUOUS IMPROVEMENT:**

This new execution is now analyzed:
- Did it succeed? Yes.
- Was it more efficient than existing cases? Yes (fewer tokens, faster).
- Should it become the new champion? Yes.

The RAG system automatically promotes this case to champion status. Next time someone 
asks a similar query, they'll benefit from this even more optimized approach.

The agent is learning. Getting faster. Getting cheaper. Automatically.

**ASYNCHRONOUS PROCESSING:**

You might wonder: "Doesn't all this RAG retrieval and analysis slow down responses?"

No. Watch the timeline:

```
[00:00.000] User submits query
[00:00.050] RAG retrieval starts (parallel thread)
[00:00.100] Strategic planner invoked
[00:00.350] RAG context injected (retrieval complete)
[00:00.400] Strategic plan finalized with RAG guidance  
[00:00.450] Tactical execution begins
[00:02.100] Results returned to user
[00:02.150] Async: Case archiving begins (background thread)
[00:03.500] Async: Efficiency analysis complete (background)
[00:03.600] Async: Case stored in RAG repository (background)
```

RAG retrieval happens during planning (under 300ms).

Case archiving happens AFTER the user gets their answer—no blocking latency.

Zero user-facing performance impact.

**PER-USER COST SAVINGS ATTRIBUTION:**

Go to Intelligence → Efficiency Metrics.

You'll see a dashboard:

```
YOUR RAG EFFICIENCY GAINS:

Total Queries: 247
RAG-Guided Queries: 183 (74%)

Token Savings:
  Without RAG (projected): 892,000 tokens
  With RAG (actual): 645,000 tokens  
  Savings: 247,000 tokens (28% reduction)

Cost Savings:
  Projected cost: $52.30
  Actual cost: $37.60
  Savings: $14.70 (28% reduction)

Time Savings:
  Average execution time without RAG: 4.2s
  Average execution time with RAG: 2.8s
  Per-query savings: 1.4s (33% faster)
```

The RAG system isn't just making the agent smarter—it's making it dramatically more 
cost-effective. And these savings compound as your repository grows.

**KNOWLEDGE TRANSFER:**

Here's the organizational benefit. When you ask a complex revenue analysis question, 
the agent learns the optimal approach. 

When your colleague asks a similar question next week, they automatically benefit from 
your success. No training. No documentation. The agent just knows.

This is collective intelligence at work. Every user's successful queries improve the 
agent for everyone.

From individual success to organizational knowledge. From one-time execution to reusable 
patterns. From static AI to self-improving intelligence.

This is the RAG-powered Fusion Optimizer. The agent that gets smarter every time you use it.
```

**Screen Capture Plan:**
- [ ] Intelligence → RAG Collections navigation
- [ ] Planner Repository view with list of cases
- [ ] Case detail: "Revenue Analysis - Top Products by Category"
- [ ] Strategic plan display
- [ ] Tool execution trace with SQL queries
- [ ] Token usage breakdown (planning + execution)
- [ ] Efficiency Score: 94/100 with breakdown
- [ ] Champion badge (🏆) indicator
- [ ] List view showing three cases with champion ranking
- [ ] New query: "Top revenue products by brand this month"
- [ ] Live Status Panel: "RAG-RETRIEVED CONTEXT" section appears
- [ ] Similar cases displayed with similarity scores
- [ ] Strategic plan using learned patterns (RANK + EXTRACT)
- [ ] Execution completes with improved metrics
- [ ] New case promoted to champion status
- [ ] Timeline visualization: RAG retrieval parallel to planning
- [ ] Intelligence → Efficiency Metrics dashboard
- [ ] Token savings: 247,000 saved (28% reduction)
- [ ] Cost savings: $14.70 saved
- [ ] Time savings: 1.4s per query faster

**Supporting Materials:**
- RAG system architecture documentation
- Efficiency scoring methodology
- Champion case selection algorithm
- Few-shot learning examples
- Asynchronous processing flow diagram
- Cost savings calculator

**Supporting Materials:**
- RAG system documentation
- Case capture examples
- Efficiency metrics guide

---

### 4.3 Proactive Optimization: Fast Paths & Hydration
**Duration:** 3-4 minutes  
**Learning Objectives:**
- Learn plan hydration mechanism
- Understand tactical fast path
- See specialized orchestrators in action

**Key Topics to Cover:**
- [ ] Plan hydration (reusing previous turn data)
- [ ] Tactical fast path (skip LLM for simple operations)
- [ ] Specialized orchestrators (date range, comparative analysis)
- [ ] Context distillation for large datasets
- [ ] Optimization impact on speed and cost

**Narration Script:**
```
The Fusion Optimizer doesn't just plan and learn—it actively hunts for optimization 
opportunities before and during execution. This is proactive optimization.

Let's explore the techniques that make Uderia fast and cost-effective.

**TECHNIQUE 1: PLAN HYDRATION**

Ask this query: "What are the top 5 products by revenue this month?"

The agent executes:
- Strategic Plan: Single phase query
- Tool: base_readQuery  
- Result: 5 products with revenue data
- Tokens: 1,800 total
- Duration: 2.1s

Results displayed. Now immediately ask a follow-up:

"What about the top 10?"

Watch the Live Status Panel carefully.

Instead of starting from scratch, you see:

```
🔧 OPTIMIZATION: PLAN HYDRATION DETECTED

New query: "What about the top 10?"
Context analysis: User is asking for expanded version of previous query

Previous query results available:
  - Query: Top 5 products by revenue
  - Tool: base_readQuery
  - Results: 5 products cached
  - Timestamp: 3 seconds ago (fresh)

Optimization strategy: HYDRATE new plan with cached data
  ✓ Skip Phase 1 planning (reuse existing strategy)
  ✓ Skip redundant tool call (modify TOP 5 to TOP 10)
  ✓ Execute single optimized query

Estimated savings: ~900 tokens, ~$0.005, ~1.2s
```

The agent recognizes this is an iterative refinement. Instead of replanning from scratch, 
it hydrates the new request with data from the previous turn.

Strategic plan:
```
Phase 1: Execute expanded query (TOP 10 instead of TOP 5)
  Tool: base_readQuery
  SQL: [Similar query with LIMIT 10]
```

Execution completes:
- Tokens: 950 total (850 fewer than full replanning)
- Duration: 0.9s (1.2s faster)
- Cost: $0.0045 ($0.005 saved)

This is plan hydration. When the agent detects iterative refinement, it reuses context 
intelligently instead of starting over.

Common triggers:
- "What about X instead?" (parameter change)
- "Show me more" (pagination/expansion)
- "Add Y to that analysis" (incremental addition)
- "Break that down by Z" (granularity increase)

**TECHNIQUE 2: TACTICAL FAST PATH**

Now ask: "What's the current date?"

Watch the Live Status Panel.

No strategic planning happens. No LLM call. You see:

```
⚡ OPTIMIZATION: TACTICAL FAST PATH

Query: "What's the current date?"
Complexity analysis: TRIVIAL (single deterministic tool call)

Optimization strategy: BYPASS strategic planning
  ✗ Skip strategic planner LLM call
  ✓ Direct tool invocation
  Tool: TDA_CurrentDate
  Arguments: {}

Estimated savings: ~1,500 tokens, ~$0.008, ~0.8s
```

The agent instantly recognized this is a trivial query—single tool, no arguments needed, 
no planning required.

Direct execution:
```
Tool: TDA_CurrentDate
Result: "2025-12-07"
```

Answer delivered in 0.2 seconds. No strategic plan. No tactical LLM call. Pure efficiency.

Fast path triggers:
- Single deterministic tool (dates, versions, simple lookups)
- All arguments inferrable from query
- No dependencies or multi-step logic

This eliminates ~1,500 tokens per fast-path query. For conversational interfaces with 
lots of quick questions, this adds up to massive savings.

**TECHNIQUE 3: SPECIALIZED ORCHESTRATORS**

Ask: "Show me daily sales for the past week."

The agent detects a pattern:

```
🎯 OPTIMIZATION: DATE RANGE ORCHESTRATOR

Query: "daily sales for the past week"
Pattern detected: Time-series iteration over date range

Standard approach:
  - Plan each day as separate phase (7 phases)
  - Execute 7 individual queries
  - Tokens: ~12,000 | Duration: ~15s

Optimized approach:
  - Specialized Date Range Orchestrator
  - Single multi-day aggregation query
  - Post-processing for daily breakdown
  - Tokens: ~2,800 | Duration: ~3.5s

Applying optimization...
```

The orchestrator generates:
```sql
SELECT CAST(SaleDate AS DATE) as Day,
       SUM(TotalAmount) as DailySales
FROM fitness_db.Sales
WHERE SaleDate >= CURRENT_DATE - 7
GROUP BY CAST(SaleDate AS DATE)
ORDER BY Day
```

One query. Seven days. Clean results.

Tokens: 2,800 (9,200 saved vs naive approach)
Duration: 3.2s (11.8s saved)

Other specialized orchestrators:

**Comparative Analysis Orchestrator:**
Query: "Compare Claude vs GPT-4 on this question: [complex query]"

Detects: Multi-model comparison pattern
Optimization: Executes query on both models in parallel, aggregates results
Savings: ~40% faster than sequential execution

**Multi-Table Join Orchestrator:**  
Query: "Join customers, sales, and products for full order analysis"

Detects: Complex multi-table join pattern
Optimization: Single optimized JOIN query instead of multiple tool calls
Savings: ~60% token reduction

**TECHNIQUE 4: CONTEXT DISTILLATION**

Ask: "List all products in the database."

The query returns 500 products. That's a lot of data.

Now ask a follow-up: "Which of those are Cardio equipment?"

Normally, the agent would send all 500 product records back to the LLM for analysis. 
That's ~50,000 tokens of context.

Watch the optimization:

```
💧 OPTIMIZATION: CONTEXT DISTILLATION

Previous tool result: 500 products (48,000 tokens raw)
New query requires: Subset filtering by ProductType='Cardio'

Strategy: DISTILL large dataset before LLM processing
  - Apply deterministic filter: ProductType='Cardio'
  - Reduced dataset: 87 products
  - Context tokens: 48,000 → 4,200 (91% reduction)

Passing distilled context to LLM for response generation...
```

The agent performed a deterministic pre-filter, dramatically reducing context size 
before involving the LLM.

Tokens used: 5,800 total (42,200 saved)
Cost: $0.028 ($2.10 saved on this single query)

Context distillation applies when:
- Large tool results (>10,000 tokens)
- Follow-up query requires subset or aggregation
- Deterministic filtering possible without LLM reasoning

**TECHNIQUE 5: MULTI-TOOL PARALLEL EXECUTION**

Ask: "Give me the database version, table list, and current system date."

The agent detects three independent requests:

```
⚡ OPTIMIZATION: PARALLEL TOOL EXECUTION

Query decomposition:
  1. Database version → dba_databaseVersion (independent)
  2. Table list → base_tableList (independent)
  3. Current date → TDA_CurrentDate (independent)

No dependencies detected. Executing in parallel...

Parallel execution:
  [Thread 1] dba_databaseVersion → 0.8s
  [Thread 2] base_tableList → 1.2s
  [Thread 3] TDA_CurrentDate → 0.1s
  
  Total duration: 1.2s (longest thread)
  
Sequential execution would take: 2.1s
Time saved: 0.9s (43% faster)
```

When multiple tools have no data dependencies, the Fusion Optimizer executes them 
concurrently.

**OPTIMIZATION IMPACT SUMMARY:**

Let's look at cumulative impact. Go to Intelligence → Optimization Metrics.

```
OPTIMIZATION PERFORMANCE (Last 30 Days):

Plan Hydration:
  - Applied: 89 times
  - Tokens saved: 78,000 (avg 876 per instance)
  - Time saved: 95 seconds total
  - Cost saved: $4.20

Tactical Fast Path:
  - Applied: 134 times  
  - Tokens saved: 195,000 (avg 1,456 per instance)
  - Time saved: 108 seconds total
  - Cost saved: $10.40

Specialized Orchestrators:
  - Applied: 23 times
  - Tokens saved: 142,000 (avg 6,174 per instance)
  - Time saved: 267 seconds total
  - Cost saved: $7.60

Context Distillation:
  - Applied: 12 times
  - Tokens saved: 380,000 (avg 31,667 per instance)
  - Time saved: 45 seconds total
  - Cost saved: $18.90

Parallel Execution:
  - Applied: 34 times
  - Time saved: 41 seconds total

TOTAL OPTIMIZATION IMPACT:
  Tokens saved: 795,000 (32% of total usage)
  Cost saved: $41.10 (34% of total spend)
  Time saved: 556 seconds (8.6 minutes)
```

These optimizations run automatically, transparently, continuously. You don't configure 
them. You don't enable them. They're built into the Fusion Optimizer's core intelligence.

From dollars to cents. From slow to fast. From wasteful to efficient.

This is proactive optimization. The agent that works smarter, not just harder.
```

**Screen Capture Plan:**
- [ ] Query: "Top 5 products by revenue"
- [ ] Results displayed with token/cost metrics
- [ ] Follow-up: "What about the top 10?"
- [ ] Live Status Panel: "🔧 PLAN HYDRATION DETECTED" message
- [ ] Optimization strategy explanation displayed
- [ ] Hydrated execution with reduced tokens (950 vs 1,800)
- [ ] Query: "What's the current date?"
- [ ] Live Status Panel: "⚡ TACTICAL FAST PATH" message
- [ ] Direct tool execution (no strategic planning)
- [ ] Result in 0.2s with token comparison
- [ ] Query: "Show daily sales for the past week"
- [ ] Live Status Panel: "🎯 DATE RANGE ORCHESTRATOR" detected
- [ ] Optimization comparison: 12,000 tokens naive vs 2,800 optimized
- [ ] Single aggregated SQL query executed
- [ ] Query: "List all products" → 500 results
- [ ] Follow-up: "Which are Cardio equipment?"
- [ ] Live Status Panel: "💧 CONTEXT DISTILLATION" message
- [ ] Context reduction: 48,000 → 4,200 tokens (91% reduction)
- [ ] Query: "Give me version, tables, and date"
- [ ] Live Status Panel: "⚡ PARALLEL TOOL EXECUTION" message
- [ ] Three threads executing simultaneously
- [ ] Duration comparison: 1.2s parallel vs 2.1s sequential
- [ ] Intelligence → Optimization Metrics dashboard
- [ ] 30-day summary with savings breakdown
- [ ] Total impact: 795,000 tokens saved, $41.10 saved

**Supporting Materials:**
- Optimization techniques documentation
- Plan hydration pattern recognition guide
- Fast path eligibility criteria
- Orchestrator catalog
- Context distillation algorithms
- Parallel execution dependency analyzer
- Performance benchmarks

**Supporting Materials:**
- Optimization techniques documentation
- Performance benchmarks
- Orchestrator examples

---

### 4.4 Cost Tracking: See Every Token, Every Cent
**Duration:** 3-4 minutes  
**Learning Objectives:**
- Monitor per-turn token usage
- Understand cost-to-token mapping
- Learn cost optimization strategies

**Key Topics to Cover:**
- [ ] Per-turn token breakdown (input/output)
- [ ] Provider-specific pricing
- [ ] Historical token trends
- [ ] Optimization insights
- [ ] RAG efficiency savings attribution

**Narration Script:**
```
All these optimizations are powerful. But how do you know they're actually saving money? 
Uderia's answer: Complete cost transparency at every level.

Let's explore the cost tracking that turns token usage from a mystery into actionable data.

**TURN-LEVEL COST VISIBILITY:**

Look at any conversation turn in the Session History panel.

Below each query-response pair, you'll see:

```
💬 Turn 3: "What are the top revenue products?"

📊 TOKEN BREAKDOWN:
  Input tokens:  1,850
  Output tokens:   340
  Total tokens:  2,190

💰 COST BREAKDOWN:
  Model: Claude Sonnet 3.5
  Input cost:  $0.0055 (1,850 × $0.003 per 1K)
  Output cost: $0.0051 (340 × $0.015 per 1K)
  Total cost:  $0.0106
  
⚡ EFFICIENCY:
  RAG-guided: YES (champion case retrieved)
  Optimization: Plan hydration applied
  Baseline tokens (no optimization): 3,200
  Tokens saved: 1,010 (32%)
  Cost saved: $0.0034
```

Every single turn shows you exactly what was consumed and what it cost. Not estimates. 
Actual token counts. Actual model-specific pricing.

**PROVIDER-SPECIFIC PRICING:**

Different models have different pricing structures. Uderia tracks them all accurately:

**Claude (Anthropic):**
- Claude Opus: $15 per 1M input, $75 per 1M output
- Claude Sonnet 3.5: $3 per 1M input, $15 per 1M output  
- Claude Haiku: $0.25 per 1M input, $1.25 per 1M output

**GPT-4 (OpenAI):**
- GPT-4o: $2.50 per 1M input, $10 per 1M output
- GPT-4o-mini: $0.15 per 1M input, $0.60 per 1M output

**Gemini (Google):**
- Gemini 1.5 Pro: $1.25 per 1M input, $5 per 1M output (≤128K context)
- Gemini 1.5 Pro: $2.50 per 1M input, $10 per 1M output (>128K context)
- Gemini 1.5 Flash: $0.075 per 1M input, $0.30 per 1M output

**AWS Bedrock:**
- Various foundation models
- Cross-region inference profiles
- Custom pricing tracked

**Ollama (Local):**
- Cost: $0.00 (local execution)

Every interaction calculates cost based on the actual model and pricing tier used.

**SESSION-LEVEL COST SUMMARY:**

At the top of every session, you see cumulative costs:

```
📊 SESSION SUMMARY: "Q4 Revenue Analysis"

Turns completed: 12
Total tokens: 28,450 (input: 19,200 | output: 9,250)
Total cost: $0.2134

Average per turn:
  Tokens: 2,371
  Cost: $0.0178

Most expensive turn: Turn 7 - "Complex multi-table analysis" ($0.0456)
Most efficient turn: Turn 3 - "Simple product lookup" ($0.0032)

Optimization impact:
  Baseline (no optimization): $0.3287
  Actual (with optimization): $0.2134
  Savings: $0.1153 (35%)
```

You can see exactly where costs are concentrated and where optimizations delivered value.

**HISTORICAL TOKEN TRENDS:**

Go to Intelligence → Token Analytics.

You'll see charts showing usage over time:

**30-Day Token Usage:**
```
    Tokens (thousands)
    ↑
50  │                                    ●
40  │                    ●           ●
30  │          ●    ●         ●
20  │    ●                        ●
10  │●
    └─────────────────────────────────────→
     Day 1    5    10   15   20   25   30
```

You can spot trends:
- Usage spike on Day 23 (what happened?)
- Declining baseline after Day 15 (optimizations kicking in?)
- Consistent daily average ~25K tokens

**Cost Trends:**
```
    Cost ($)
    ↑
2.0 │                                    ●
1.5 │                    ●           ●
1.0 │          ●    ●         ●
0.5 │    ●                        ●
    └─────────────────────────────────────→
     Day 1    5    10   15   20   25   30

Total 30-day spend: $34.20
Average daily: $1.14
Projected monthly: $35.04
```

This helps with budgeting and cost forecasting.

**PROVIDER COST COMPARISON:**

Now here's where it gets strategic. Go to Intelligence → Provider Comparison.

You can run the same workload on different models and see actual cost differences:

```
WORKLOAD: "Standard Revenue Analysis" (10 typical queries)

┌─────────────────────────┬──────────┬─────────┬──────────┐
│ Provider/Model          │ Tokens   │ Cost    │ Duration │
├─────────────────────────┼──────────┼─────────┼──────────┤
│ Claude Opus             │ 24,500   │ $0.487  │ 8.2s     │
│ Claude Sonnet 3.5       │ 24,500   │ $0.097  │ 7.8s     │
│ GPT-4o                  │ 26,100   │ $0.131  │ 9.1s     │
│ Gemini 1.5 Pro          │ 25,800   │ $0.077  │ 6.9s     │
│ Gemini 1.5 Flash        │ 25,800   │ $0.010  │ 4.2s     │
│ Ollama (Llama 3.1 70B)  │ 28,200   │ $0.000  │ 12.3s    │
└─────────────────────────┴──────────┴─────────┴──────────┘

Insights:
- Gemini Flash: Lowest cost, fastest (4.2s), great for batch jobs
- Claude Sonnet 3.5: Best balance of cost ($0.097) and quality
- Claude Opus: 5x more expensive than Sonnet for similar results
- Ollama: Zero cost but slowest (acceptable for non-urgent queries)

Recommendation: Use Gemini Flash for routine queries (@COST profile),
                Claude Sonnet for complex analysis (@PROD profile),
                Ollama for sensitive data (@LOCAL profile)
```

This data-driven comparison helps you optimize your profile strategy.

**RAG EFFICIENCY SAVINGS:**

Back to Intelligence → RAG Efficiency.

The RAG system tracks how much it saves you:

```
RAG COST IMPACT ANALYSIS:

Total queries: 247
RAG-guided queries: 183 (74%)

Without RAG (projected baseline):
  Average tokens per query: 3,612
  Total tokens: 892,164
  Total cost: $52.30

With RAG (actual usage):
  Average tokens per query: 2,611  
  Total tokens: 645,013
  Total cost: $37.60

RAG SAVINGS:
  Tokens saved: 247,151 (28%)
  Cost saved: $14.70 (28%)
  
Cost per query:
  Without RAG: $0.212
  With RAG: $0.152
  Savings per query: $0.060

Projected annual savings (at current usage): $876
```

The RAG system pays for itself through continuous optimization.

**OPTIMIZATION INSIGHTS:**

Every cost display includes optimization context:

```
💡 COST OPTIMIZATION TIPS:

1. Turn 7 used Claude Opus ($0.0456) for a simple lookup.
   → Could use Gemini Flash ($0.0018) for 96% cost reduction
   
2. 34% of queries are suitable for fast-path execution.
   → Enable tactical fast path for ~$12/month savings
   
3. Session "Daily Reports" runs at peak hours with Sonnet.
   → Switch to Gemini Flash off-peak for 90% cost reduction
   
4. 12 queries loaded >10K context unnecessarily.
   → Enable context distillation for ~$8/month savings
```

Actionable recommendations based on your actual usage patterns.

**COST ALERTS:**

You can set spending alerts:

```
🚨 COST ALERT CONFIGURATION:

✓ Daily spending exceeds $5
✓ Session cost exceeds $1  
✓ Single query exceeds $0.50
✓ Monthly projected spend exceeds $150

Alert method: Email + Dashboard notification
```

If a query unexpectedly balloons in cost, you'll know immediately.

**EXPORT AND REPORTING:**

All cost data is exportable:

```
EXPORT OPTIONS:
- CSV (for Excel analysis)
- JSON (for API integration)
- PDF (for stakeholder reports)

Filters:
- Date range
- User (multi-user environments)
- Session
- Model/Provider
- Cost threshold
```

Generate monthly reports for finance. Track ROI. Justify infrastructure costs.

**THE BOTTOM LINE:**

From individual tokens to organizational budgets, Uderia gives you complete visibility:

- Turn-level: See every token, every cent
- Session-level: Track cumulative costs per workflow
- Historical: Identify trends and forecast spending
- Comparative: Choose optimal models based on real data
- RAG-attributed: Measure continuous improvement ROI
- Optimization-aware: Understand what's saving money

No hidden costs. No surprises. Complete financial transparency.

Because in enterprise AI, trust requires knowing exactly what you're paying for.

Every token. Every penny. Every optimization. All visible. All actionable.

This is financial governance for the AI age.
```

**Screen Capture Plan:**
- [ ] Session History with turn-level cost displays
- [ ] Turn 3 expanded: Token breakdown (input/output)
- [ ] Cost breakdown with model-specific pricing
- [ ] Efficiency section showing RAG guidance and optimization savings
- [ ] Provider pricing reference table (Claude, GPT, Gemini, Bedrock, Ollama)
- [ ] Session summary at top: 12 turns, $0.2134 total
- [ ] Average per turn, most expensive turn, most efficient turn
- [ ] Optimization impact: $0.3287 baseline vs $0.2134 actual
- [ ] Intelligence → Token Analytics dashboard
- [ ] 30-day token usage chart with trend line
- [ ] 30-day cost trend chart
- [ ] Projected monthly spend calculation
- [ ] Intelligence → Provider Comparison
- [ ] Workload comparison table across 6 providers
- [ ] Cost range: $0.487 (Opus) to $0.000 (Ollama)
- [ ] Recommendation box with strategic guidance
- [ ] Intelligence → RAG Efficiency dashboard
- [ ] RAG cost impact: $52.30 baseline vs $37.60 actual
- [ ] Savings: $14.70 (28%), projected annual: $876
- [ ] Optimization insights panel with 4 actionable tips
- [ ] Cost alert configuration interface
- [ ] Export options: CSV, JSON, PDF with filters

**Supporting Materials:**
- Cost tracking documentation
- Provider pricing reference (updated monthly)
- Cost optimization strategies guide
- ROI calculation methodology
- Budget forecasting tools
- Cost alert setup guide
- Financial reporting templates

**Supporting Materials:**
- Token tracking documentation
- Cost optimization guide
- Pricing model reference

---

## Module 5: SOVEREIGNTY - Your Data, Your Rules
**Goal:** Demonstrate ultimate flexibility in data exposure and infrastructure choice

### 5.1 Multi-Provider LLM Support: Freedom to Choose
**Duration:** 3-4 minutes  
**Learning Objectives:**
- Explore supported LLM providers
- Learn provider switching mechanics
- Understand use cases for different providers

**Key Topics to Cover:**
- [ ] Cloud hyperscalers (Google, Anthropic, OpenAI, Azure)
- [ ] AWS Bedrock support
- [ ] Friendli.AI integration
- [ ] Ollama for local execution
- [ ] Dynamic provider switching
- [ ] Live model refresh

**Narration Script:**
```
[SCRIPT PLACEHOLDER]
```

**Screen Capture Plan:**
- [ ] LLM Provider configuration panel
- [ ] Adding a new provider
- [ ] Model selection dropdown
- [ ] Provider switching demonstration
- [ ] Encrypted credential storage

**Supporting Materials:**
- Multi-provider documentation
- Provider setup guides
- Credential management guide

---

### 5.2 Hybrid Intelligence: Cloud Power + Local Privacy
**Duration:** 4-5 minutes  
**Learning Objectives:**
- Understand hybrid architecture
- See cloud planning + local execution
- Learn champion case injection for local models

**Key Topics to Cover:**
- [ ] Hybrid architecture concept (strategic planner vs executor)
- [ ] Cloud LLM for planning intelligence
- [ ] Local Ollama for private execution
- [ ] Champion case injection to boost local model performance
- [ ] Complete data sovereignty

**Narration Script:**
```
[SCRIPT PLACEHOLDER]
```

**Screen Capture Plan:**
- [ ] Hybrid architecture diagram
- [ ] Profile configuration for hybrid mode
- [ ] Query execution showing cloud planning
- [ ] Local execution with Ollama
- [ ] Performance comparison

**Supporting Materials:**
- Hybrid intelligence documentation
- Architecture diagrams
- Ollama setup guide

---

### 5.3 Security & Multi-User Isolation
**Duration:** 3-4 minutes  
**Learning Objectives:**
- Understand JWT authentication
- Learn user isolation mechanisms
- Explore role-based access control

**Key Topics to Cover:**
- [ ] JWT-based authentication (24-hour expiry)
- [ ] User-specific session directories
- [ ] Database-level UUID isolation
- [ ] Role-based access (User, Developer, Admin)
- [ ] Encrypted credential storage
- [ ] Multi-user simultaneous support

**Narration Script:**
```
[SCRIPT PLACEHOLDER]
```

**Screen Capture Plan:**
- [ ] Login/registration security
- [ ] User session isolation demonstration
- [ ] Admin panel showing users
- [ ] Role assignment
- [ ] Credential encryption visualization

**Supporting Materials:**
- Security architecture guide
- Multi-user setup documentation
- Authentication flow diagrams

---

## Module 6: COLLABORATIVE - Intelligence Marketplace
**Goal:** Transform individual expertise into collective organizational knowledge

### 6.1 Marketplace Overview: Collective Intelligence
**Duration:** 3-4 minutes  
**Learning Objectives:**
- Understand marketplace value proposition
- Learn dual repository architecture (Planner vs Knowledge)
- See community ecosystem vision

**Key Topics to Cover:**
- [ ] From isolated expertise to collective intelligence
- [ ] Planner Repositories (📋 execution patterns)
- [ ] Knowledge Repositories (📄 domain knowledge)
- [ ] Visual separation and organization
- [ ] Network effects and cost reduction

**Narration Script:**
```
[SCRIPT PLACEHOLDER]
```

**Screen Capture Plan:**
- [ ] Marketplace landing page
- [ ] Dual repository tabs
- [ ] Collection cards with badges
- [ ] Value proposition visualization
- [ ] Community statistics

**Supporting Materials:**
- Marketplace documentation
- Architecture diagrams
- Use case examples

---

### 6.2 Planner Repositories: Share Execution Patterns
**Duration:** 3-4 minutes  
**Learning Objectives:**
- Create templates from successful cases
- Browse and discover planner collections
- Deploy patterns to your repository

**Key Topics to Cover:**
- [ ] "Create Template" from RAG case
- [ ] Template metadata (name, description, tags)
- [ ] Browsing planner collections
- [ ] "Deploy to My Repository" workflow
- [ ] Pattern reuse and cost savings

**Narration Script:**
```
[SCRIPT PLACEHOLDER]
```

**Screen Capture Plan:**
- [ ] Creating template from successful query
- [ ] Template creation form
- [ ] Browsing marketplace (Planner tab)
- [ ] Deploying a collection
- [ ] Seeing deployed patterns in Intelligence View

**Supporting Materials:**
- Planner repository guide
- Template creation best practices
- Deployment workflow documentation

---

### 6.3 Knowledge Repositories: Share Domain Expertise
**Duration:** 3-4 minutes  
**Learning Objectives:**
- Upload documents to knowledge collections
- Publish knowledge for community access
- Deploy knowledge to your environment

**Key Topics to Cover:**
- [ ] Creating knowledge collections
- [ ] Document upload (PDF, TXT, DOCX, MD)
- [ ] Chunking strategies
- [ ] Publishing to marketplace
- [ ] Subscribing to expert knowledge

**Narration Script:**
```
[SCRIPT PLACEHOLDER]
```

**Screen Capture Plan:**
- [ ] Creating knowledge collection
- [ ] Document upload interface
- [ ] Chunking configuration
- [ ] Publishing collection
- [ ] Subscribing to community knowledge

**Supporting Materials:**
- Knowledge repository documentation
- Document preparation guide
- Chunking strategy reference

---

### 6.4 Subscribe, Fork, Rate: Community Ecosystem
**Duration:** 3-4 minutes  
**Learning Objectives:**
- Subscribe to collections (reference-based)
- Fork collections for customization
- Rate and review for quality assurance

**Key Topics to Cover:**
- [ ] Subscribe workflow (no data duplication)
- [ ] Fork workflow (independent copy)
- [ ] Rating system (1-5 stars)
- [ ] Publishing options (Public, Unlisted, Private)
- [ ] Community quality assurance

**Narration Script:**
```
[SCRIPT PLACEHOLDER]
```

**Screen Capture Plan:**
- [ ] Subscribing to a collection
- [ ] Forking a collection
- [ ] Rating and reviewing
- [ ] Visibility settings
- [ ] Top-rated collections view

**Supporting Materials:**
- Marketplace user guide
- Subscription vs fork comparison
- Quality assurance guidelines

---

## Module 7: FINANCIAL GOVERNANCE
**Goal:** Complete transparency and control over LLM spending

### 7.1 Real-Time Cost Tracking Dashboard
**Duration:** 3-4 minutes  
**Learning Objectives:**
- Access cost analytics dashboard
- Understand per-session cost tracking
- Learn token-to-cost mapping

**Key Topics to Cover:**
- [ ] Admin Cost Analytics access
- [ ] Total cost across all sessions
- [ ] Average cost per session/turn
- [ ] Per-turn token breakdown
- [ ] Real-time cost updates

**Narration Script:**
```
[SCRIPT PLACEHOLDER]
```

**Screen Capture Plan:**
- [ ] Admin dashboard navigation
- [ ] Cost Analytics main view
- [ ] Session cost drill-down
- [ ] Turn-level cost details
- [ ] Token usage visualization

**Supporting Materials:**
- Cost tracking documentation
- Analytics dashboard guide
- Financial governance overview

---

### 7.2 Cost Analytics & Optimization
**Duration:** 4-5 minutes  
**Learning Objectives:**
- Analyze cost distribution by provider
- Identify most expensive models and queries
- Explore cost trends and optimization opportunities

**Key Topics to Cover:**
- [ ] Cost distribution by provider chart
- [ ] Top 5 most expensive models
- [ ] 30-day cost trend visualization
- [ ] Most expensive sessions/queries
- [ ] RAG efficiency savings metrics
- [ ] Optimization recommendations

**Narration Script:**
```
[SCRIPT PLACEHOLDER]
```

**Screen Capture Plan:**
- [ ] Provider cost comparison chart
- [ ] Model expense breakdown
- [ ] Trend analysis over time
- [ ] Expensive query drill-down
- [ ] RAG savings attribution
- [ ] Optimization insights panel

**Supporting Materials:**
- Cost analytics documentation
- Optimization strategies guide
- Provider comparison reference

---

### 7.3 Consumption Profiles & Rate Limiting
**Duration:** 3-4 minutes  
**Learning Objectives:**
- Understand consumption profile tiers
- Configure rate limits and quotas
- Monitor usage enforcement

**Key Topics to Cover:**
- [ ] Four profile tiers (Free, Pro, Enterprise, Unlimited)
- [ ] Per-user rate limits (hourly/daily prompts)
- [ ] Monthly token quotas
- [ ] Configuration change limits
- [ ] Admin bypass capabilities
- [ ] Real-time enforcement

**Narration Script:**
```
[SCRIPT PLACEHOLDER]
```

**Screen Capture Plan:**
- [ ] Consumption profile configuration
- [ ] User profile assignment
- [ ] Rate limit enforcement demonstration
- [ ] Quota tracking dashboard
- [ ] Admin override example

**Supporting Materials:**
- Consumption profiles documentation
- Rate limiting guide
- Quota management reference

---

## Module 8: Administration
**Goal:** Complete platform administration and governance capabilities

### 8.1 User & Access Management
**Duration:** 3-4 minutes  
**Learning Objectives:**
- Manage user accounts
- Assign roles and permissions
- Monitor user activity

**Key Topics to Cover:**
- [ ] User administration panel
- [ ] Creating/editing users
- [ ] Role assignment (User, Developer, Admin)
- [ ] Consumption profile assignment
- [ ] User activity monitoring
- [ ] Account suspension/activation

**Narration Script:**
```
[SCRIPT PLACEHOLDER]
```

**Screen Capture Plan:**
- [ ] Admin Users panel
- [ ] User creation workflow
- [ ] Role assignment interface
- [ ] Profile assignment
- [ ] Activity log review

**Supporting Materials:**
- User management documentation
- Role permissions matrix
- Admin guide

---

### 8.2 Long-Lived Access Tokens
**Duration:** 3-4 minutes  
**Learning Objectives:**
- Generate long-lived access tokens
- Manage token lifecycle
- Track token usage

**Key Topics to Cover:**
- [ ] Token generation (90 days or never expire)
- [ ] One-time display security pattern
- [ ] SHA256 hashed storage
- [ ] Usage tracking (last used, count, IP)
- [ ] Token revocation and soft-delete
- [ ] API authentication with tokens

**Narration Script:**
```
[SCRIPT PLACEHOLDER]
```

**Screen Capture Plan:**
- [ ] Token generation interface
- [ ] One-time token display
- [ ] Token management panel
- [ ] Usage statistics view
- [ ] Token revocation
- [ ] API call with bearer token

**Supporting Materials:**
- Access token documentation
- Security best practices
- API authentication guide

---

### 8.3 System Configuration & Monitoring
**Duration:** 3-4 minutes  
**Learning Objectives:**
- Configure system-wide settings
- Monitor platform health
- Manage LLM provider costs

**Key Topics to Cover:**
- [ ] System settings panel
- [ ] LLM provider configuration
- [ ] MCP server management
- [ ] Cost pricing configuration (manual overrides, LiteLLM sync)
- [ ] Audit log access
- [ ] System health monitoring

**Narration Script:**
```
[SCRIPT PLACEHOLDER]
```

**Screen Capture Plan:**
- [ ] System configuration dashboard
- [ ] Provider settings
- [ ] MCP server configuration
- [ ] Cost pricing editor
- [ ] Audit log viewer
- [ ] System status indicators

**Supporting Materials:**
- System administration guide
- Configuration reference
- Troubleshooting documentation

---

## Module 9: Advanced Topics
**Goal:** Deep-dive into specialized integrations and deployment scenarios

### 9.1 Flowise Integration: Low-Code Workflows
**Duration:** 4-5 minutes  
**Learning Objectives:**
- Understand Flowise + Uderia architecture
- Import pre-built agent flows
- Build custom workflows visually

**Key Topics to Cover:**
- [ ] Flowise overview and value proposition
- [ ] Pre-built Uderia agent flow
- [ ] Async submit + poll pattern implementation
- [ ] Session management in workflows
- [ ] Bearer token authentication
- [ ] TTS payload extraction for voice chatbots

**Narration Script:**
```
[SCRIPT PLACEHOLDER]
```

**Screen Capture Plan:**
- [ ] Flowise interface overview
- [ ] Importing Uderia template
- [ ] Flow design walkthrough
- [ ] Testing workflow execution
- [ ] Chatbot integration example

**Supporting Materials:**
- docs/Flowise documentation
- Pre-built flow JSON
- Integration guide

---

### 9.2 Docker Deployment: Production Setup
**Duration:** 4-5 minutes  
**Learning Objectives:**
- Build Uderia Docker image
- Configure production deployment
- Manage multi-user container

**Key Topics to Cover:**
- [ ] Dockerfile overview
- [ ] Docker Compose configuration
- [ ] Environment variable overrides
- [ ] Volume mounts (sessions, logs, keys)
- [ ] Multi-user shared container
- [ ] Load balancer configuration
- [ ] Horizontal scaling considerations

**Narration Script:**
```
[SCRIPT PLACEHOLDER]
```

**Screen Capture Plan:**
- [ ] Docker build process
- [ ] docker-compose.yml walkthrough
- [ ] Container startup
- [ ] Volume mount verification
- [ ] Multi-user access demonstration
- [ ] Production deployment checklist

**Supporting Materials:**
- Docker deployment documentation
- docker-compose.yml reference
- Production deployment guide

---

### 9.3 Developer Mode & Custom Integrations
**Duration:** 3-4 minutes  
**Learning Objectives:**
- Enable developer features
- Create custom MCP servers
- Build custom integrations

**Key Topics to Cover:**
- [ ] Developer role activation
- [ ] Custom MCP server development
- [ ] Tool/prompt registration
- [ ] Custom prompt templates
- [ ] Plugin system for Planner Repository Constructors
- [ ] REST API extension patterns

**Narration Script:**
```
[SCRIPT PLACEHOLDER]
```

**Screen Capture Plan:**
- [ ] Developer mode features
- [ ] Custom MCP server example
- [ ] Tool registration
- [ ] Custom prompt creation
- [ ] Plugin architecture

**Supporting Materials:**
- Developer documentation
- MCP server development guide
- Plugin system reference

---

### 9.4 Installing Your Own Uderia Platform
**Duration:** 5-6 minutes  
**Learning Objectives:**
- Clone repository and setup
- Configure environment
- Run platform locally
- Verify installation

**Key Topics to Cover:**
- [ ] Prerequisites (Python, Node.js, etc.)
- [ ] Git clone from GitHub
- [ ] Virtual environment setup
- [ ] Dependencies installation (requirements.txt)
- [ ] Configuration file setup (tda_config.json)
- [ ] Database initialization
- [ ] First run and verification
- [ ] Troubleshooting common issues

**Narration Script:**
```
[SCRIPT PLACEHOLDER]
```

**Screen Capture Plan:**
- [ ] GitHub repository page
- [ ] Terminal: git clone command
- [ ] Terminal: environment setup
- [ ] Terminal: pip install
- [ ] Config file editing
- [ ] Database initialization
- [ ] Platform startup
- [ ] Browser: first access verification

**Supporting Materials:**
- README.md installation section
- Installation and Setup Guide
- Troubleshooting documentation

---

## Module 10: User Journey Scenarios
**Goal:** Demonstrate end-to-end workflows for different user personas

### 10.1 Knowledge Worker: Data Discovery Journey
**Duration:** 4-5 minutes  
**Learning Objectives:**
- Follow realistic data analysis workflow
- See conversational discovery in action
- Understand iterative refinement

**Key Topics to Cover:**
- [ ] Scenario: Business analyst exploring sales data
- [ ] Initial exploratory question
- [ ] Follow-up clarifications
- [ ] Drilling into anomalies
- [ ] Exporting insights
- [ ] Sharing findings with team

**Narration Script:**
```
[SCRIPT PLACEHOLDER]
```

**Screen Capture Plan:**
- [ ] Initial query ("What are our top products?")
- [ ] Results visualization
- [ ] Follow-up ("Why did Product X decline?")
- [ ] Context management throughout
- [ ] Insight extraction
- [ ] Export/share functionality

**Supporting Materials:**
- User persona documentation
- Example business scenarios
- Sample datasets

---

### 10.2 Content Developer: Building Intelligence
**Duration:** 4-5 minutes  
**Learning Objectives:**
- Create valuable knowledge collections
- Build reusable planner templates
- Contribute to marketplace

**Key Topics to Cover:**
- [ ] Scenario: Data team creating SQL pattern library
- [ ] Developing champion query strategies
- [ ] Creating planner repository templates
- [ ] Uploading domain knowledge documents
- [ ] Publishing to marketplace
- [ ] Tracking community adoption

**Narration Script:**
```
[SCRIPT PLACEHOLDER]
```

**Screen Capture Plan:**
- [ ] Crafting effective queries
- [ ] Reviewing RAG cases
- [ ] Template creation workflow
- [ ] Knowledge document upload
- [ ] Publishing to marketplace
- [ ] Monitoring ratings and usage

**Supporting Materials:**
- Content development guide
- Template best practices
- Marketplace contributor guide

---

### 10.3 DevOps Engineer: Production Deployment
**Duration:** 5-6 minutes  
**Learning Objectives:**
- Deploy Uderia in production environment
- Configure automation pipelines
- Monitor production operations

**Key Topics to Cover:**
- [ ] Scenario: DevOps team deploying for enterprise
- [ ] Docker containerization
- [ ] Load balancer configuration
- [ ] Airflow DAG deployment
- [ ] REST API integration testing
- [ ] Monitoring and alerting setup
- [ ] Security hardening

**Narration Script:**
```
[SCRIPT PLACEHOLDER]
```

**Screen Capture Plan:**
- [ ] Production architecture diagram
- [ ] Docker deployment process
- [ ] Airflow integration setup
- [ ] API testing suite
- [ ] Monitoring dashboard
- [ ] Security configuration

**Supporting Materials:**
- Production deployment checklist
- DevOps best practices
- Security hardening guide

---

### 10.4 Administrator: Governance & Control
**Duration:** 4-5 minutes  
**Learning Objectives:**
- Establish governance policies
- Monitor platform usage
- Control costs and access

**Key Topics to Cover:**
- [ ] Scenario: Admin managing enterprise platform
- [ ] Setting consumption profiles
- [ ] Configuring rate limits
- [ ] Cost monitoring and optimization
- [ ] User access management
- [ ] Audit log review
- [ ] Marketplace curation

**Narration Script:**
```
[SCRIPT PLACEHOLDER]
```

**Screen Capture Plan:**
- [ ] Admin dashboard overview
- [ ] Profile assignment workflow
- [ ] Cost analytics review
- [ ] User management operations
- [ ] Audit log filtering
- [ ] Marketplace admin controls

**Supporting Materials:**
- Administrator guide
- Governance framework
- Compliance documentation

---

## 🗄️ Demo Environment Reference

### Database Schema: fitness_db

**Business Context:** Fitness equipment retail company with sales tracking and customer service management

**Tables Overview:**

1. **Customers** (Base table)
   - CustomerID, FirstName, LastName, Email, Phone
   - Address, City, State, ZipCode
   - RegistrationDate
   - **Use Cases:** Customer demographics, geographic analysis, customer lifetime value

2. **Products** (Inventory table)
   - ProductID, ProductName, ProductType, Brand
   - Price, StockQuantity
   - **Use Cases:** Product catalog queries, inventory tracking, pricing analysis

3. **Sales** (Transaction header)
   - SaleID, CustomerID, SaleDate, TotalAmount, SalesPersonID
   - **Use Cases:** Revenue trends, sales performance, temporal analysis

4. **SaleDetails** (Transaction line items)
   - SaleDetailID, SaleID, ProductID, Quantity, UnitPrice
   - **Use Cases:** Product-level revenue, quantity analysis, pricing validation

5. **ServiceTickets** (Customer support)
   - TicketID, CustomerID, ProductID, TicketDate
   - IssueDescription, Status, ResolutionDate
   - **Use Cases:** Product quality analysis, customer satisfaction, warranty tracking

**Key Relationships:**
- Sales → Customers (one-to-many)
- SaleDetails → Sales (one-to-many)
- SaleDetails → Products (many-to-one)
- ServiceTickets → Customers (many-to-one)
- ServiceTickets → Products (many-to-one)

### MCP Tools Configuration

#### Core MCP Tools (Teradata Server)

**BASE Category - Database Operations:**
- `base_databaseList` - List all databases in the system
- `base_tableList` - List all tables in a database  
- `base_tableDDL` - Retrieve table DDL (CREATE TABLE statement)
- `base_readQuery` - Execute SELECT queries and return results
- `base_databaseBusinessDesc` (prompt) - Get business description of database
- `base_tableBusinessDesc` (prompt) - Get business description of table

**QUALITY Category - Data Validation:**
- `qlty_*` tools - Data profiling, validation, anomaly detection
- `qlty_databaseQuality` (prompt) - Comprehensive database quality assessment

**DBA Category - Administration:**
- `dba_databaseVersion` - Get Teradata system version
- `dba_databaseLineage` (prompt) - Data lineage analysis
- `dba_databaseHealthAssessment` (prompt) - System health check
- `dba_userActivityAnalysis` (prompt) - User activity tracking
- `dba_systemVoice` (prompt) - System status narrative
- `dba_tableArchive` (prompt) - Table archiving recommendations
- `dba_tableDropImpact` (prompt) - Impact analysis for dropping tables

#### Client-Side Tools (Built into Uderia)

**TDA Category - Platform Tools:**
- `TDA_FinalReport` - Format structured final report for UI
- `TDA_ComplexPromptReport` - Execute complex prompt workflows
- `TDA_LLMTask` - Delegate tasks to LLM for analysis
- `TDA_CurrentDate` - Get current date/time
- `TDA_SystemLog` - Log system messages to Live Status Panel
- `TDA_Charting` - Generate data visualizations (charts)

**MCP Tools by User Persona:**

**For Business Users (Modules 1-4, 6, 10.1, 10.2):**
- Primary: `base_readQuery`, `base_tableList`, `base_tableDDL`, `base_databaseList`
- Secondary: `TDA_FinalReport`, `TDA_LLMTask`, `TDA_Charting`
- Prompts: `base_databaseBusinessDesc`, `base_tableBusinessDesc`

**For Administrators (Modules 7, 8, 10.4):**
- Primary: `dba_databaseVersion`, all `dba_*` prompts
- Secondary: All consumption tracking endpoints (via REST API)
- Focus: Cost analytics, user management, system monitoring

**For DevOps/Advanced (Modules 9, 10.3):**
- All tools available: Full system access for integration demonstrations
- Focus: REST API automation, Airflow integration, profile switching

### Sample Queries by Persona

**Knowledge Worker Queries:**
- "What are the top 5 fitness products by revenue this month?"
- "Show me customer demographics for people who bought treadmills"
- "Which products have the highest return/service ticket rates?"
- "Compare sales performance across different states"
- "What's the average time to resolve service tickets by product type?"

**Content Developer Queries:**
- "Analyze the data quality of the Email field in Customers table"
- "Create a comprehensive sales pattern for Q4 holiday season"
- "What are the most common SQL patterns for revenue analysis?"

**Administrator Queries:**
- "Show me total LLM costs for the past 30 days"
- "Which users are consuming the most tokens?"
- "What are the top 5 most expensive queries this week?"
- "Display current consumption profile allocations"

**DevOps Engineer Queries:**
- "Execute this query asynchronously and poll for results"
- "Create an Airflow DAG for daily sales aggregation"
- "Test the same query across Claude and GPT-4 for comparison"

### Expected Demonstrations

**Module 1 (First Conversation):**
- Query: "Top 5 products by revenue"
- **MCP Tools Shown:** `base_readQuery` (executing SQL query)
- **Shows:** Strategic planning, SQL generation, table rendering
- Follow-up: "Customer demographics for top product"
- **Shows:** Context retention, multi-table joins, `TDA_FinalReport` formatting

**Module 3.2 (Capabilities Discovery):**
- **MCP Tools Tab:** Show `base_tableList`, `base_readQuery`, `base_tableDDL`, `dba_databaseVersion`
- **MCP Prompts Tab:** Show `base_databaseBusinessDesc`, `base_tableBusinessDesc`, categorized display
- **Demonstrate:** Adding new tool to profile, seeing it appear in capabilities

**Module 3.4 (System Customization):**
- **Demonstrate:** Disabling `base_tableDDL` tool and seeing queries fail without it
- **Demonstrate:** Re-enabling tool and query succeeding
- **Show:** Dynamic capability management (enable/disable specific tools/prompts)

**Module 4.2 (RAG Self-Learning):**
- **Show:** RAG case containing `base_readQuery` tool execution
- **Demonstrate:** Similar query retrieving past `base_readQuery` pattern from RAG
- **MCP Context:** How RAG captures tool names, arguments, and results

**Module 2 (REST API):**
- Convert above conversational query to cURL command
- Show session management and result retrieval

**Module 3 (Transparency):**
- Complex multi-phase query requiring recursive planning
- Demonstrate self-correction when initial approach fails

**Module 4 (Efficiency):**
- Show RAG case capture after successful query
- Demonstrate plan hydration with follow-up question
- Display token savings from RAG-guided planning

**Module 6 (Marketplace):**
- Create template from successful revenue analysis query
- Publish to marketplace as "Retail Revenue Patterns"
- Show another user deploying and using the pattern

**Module 10 (User Journeys):**
- Knowledge Worker: Full exploratory analysis workflow
- Administrator: Cost monitoring and user management
- DevOps: Production deployment with Airflow integration

---

## 📝 Tutorial Creation Workflow

### For Each Section:

1. **Preparation Phase**
   - [ ] Review learning objectives
   - [ ] Prepare demo environment/data
   - [ ] Test all screen captures
   - [ ] Write and refine narration script

2. **Recording Phase**
   - [ ] Record screen capture (Tight.studio)
   - [ ] Record narration (voice-over or live)
   - [ ] Capture B-roll (UI elements, diagrams)
   - [ ] Ensure 2-5 minute target duration

3. **Post-Production Phase**
   - [ ] Edit for clarity and pacing
   - [ ] Add callouts/highlights
   - [ ] Insert transition slides
   - [ ] Review for technical accuracy

4. **Quality Assurance**
   - [ ] Verify learning objectives achieved
   - [ ] Test with sample audience
   - [ ] Gather feedback
   - [ ] Iterate if needed

---

## 🎯 Success Metrics

**Tutorial Effectiveness Indicators:**
- [ ] Viewers can successfully complete learning objectives
- [ ] Clear differentiation from competitors established
- [ ] All six core principles comprehensively covered
- [ ] Actionable takeaways in every section
- [ ] Professional production quality (Tight.studio)

**Key Messaging Achieved:**
- [ ] "Two-in-one" conversation → API paradigm clear
- [ ] "Hybrid intelligence" cloud + local positioning understood
- [ ] "Self-learning RAG" continuous improvement demonstrated
- [ ] "Marketplace" collective intelligence ecosystem showcased
- [ ] "Complete transparency" black box elimination proven
- [ ] "Financial governance" cost control demonstrated

---

## 📚 Reference Materials

**Primary Sources:**
- README.md (comprehensive feature documentation)
- www.uderia.com (value proposition and messaging)
- docs/ directory (technical deep-dives)
- Source code (implementation details)

**Visual Assets Needed:**
- Architecture diagrams
- UI screenshots (all major views)
- Workflow comparison diagrams
- Cost savings visualizations
- Marketplace ecosystem graphics

**Demo Environment Requirements:**
- Configured MCP servers (database, API)
- Sample data for realistic queries
- Multiple LLM providers configured
- Pre-populated RAG collections
- Multiple user accounts for multi-user demos

---

## 🚀 Next Steps

1. **Review & Refine:** Validate this structure with stakeholders
2. **Script Writing:** Fill in narration placeholders section-by-section
3. **Environment Setup:** Prepare demo environment and sample data
4. **Pilot Recording:** Create 2-3 sample sections for feedback
5. **Iteration:** Refine based on pilot feedback
6. **Full Production:** Record all sections systematically
7. **Launch:** Publish to Tight.studio and promote

---

**Document Status:** Structure Complete - Ready for Narration Scripting  
**Next Action Required:** Begin filling in narration scripts starting with Module 1

