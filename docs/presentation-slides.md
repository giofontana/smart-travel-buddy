# Building AI Agents on Red Hat OpenShift

Presentation template: Red Hat standard presentation template (standard light theme).

---

## Slide 1 — Title Slide

**Layout:** Title slide (red background)

**Title:** Building AI Agents on Red Hat OpenShift

**Subtitle:** From LLM inference to production deployment

**Presenter:** Giovanni Fontana

**Speaker Notes:**
Welcome everyone. Today I'll walk you through how we built a real AI agent application — Smart Travel Buddy — and show how Red Hat technologies power every layer, from local LLM inference with OpenShift AI to GitOps-driven deployments with ArgoCD. We'll finish with a live demo.

---

## Slide 2 — Agenda

**Layout:** Agenda slide (two columns)

**Title:** What we'll cover today

**Left column:**
- The challenge of AI agents
- Smart Travel Buddy
- Application architecture
- The AI layer

**Right column:**
- OpenShift AI + vLLM
- OpenShift platform
- GitOps + ArgoCD
- Live demo

**Speaker Notes:**
Here's our roadmap. We'll start with why AI agents are harder than they look, introduce the application, dive into the architecture, and then focus on four Red Hat technologies that make it production-ready. We'll wrap up with a live demo.

---

## Slide 3 — Divider

**Layout:** Divider slide (large red text, white background)

**Title:** The challenge

**Supporting text:** AI applications need more than just a model

**Speaker Notes:**
Let's start with the problem. Everyone is excited about LLMs, but building a useful AI application requires much more than just calling an API.

---

## Slide 4 — AI agents are complex systems

**Layout:** Content slide (title + bullet points)

**Title:** AI agents are complex systems

**Content:**

**Beyond the LLM**
- An AI agent is not just a chat interface — it orchestrates tools, data, and reasoning
- Real-world agents need access to live data: weather, currencies, knowledge bases
- They must manage multi-step workflows with state and memory

**Production challenges**
- Model hosting: GPU resources, low latency, model flexibility
- Microservices: each tool as an isolated, scalable service
- Data privacy: keeping models and data within your infrastructure
- Deployment: reproducible, auditable, GitOps-driven releases

**Speaker Notes:**
An AI agent does much more than generate text. It needs to call external tools, manage conversation state across multiple phases, and synthesize information from different sources. When you move to production, you face additional challenges: where does the model run? How do you manage secrets? How do you deploy reliably? These are infrastructure problems, and that's where Red Hat comes in.

---

## Slide 5 — Divider

**Layout:** Divider slide (large red text, white background)

**Title:** The solution

**Supporting text:** Smart Travel Buddy — an AI travel planning agent built on Red Hat technologies

**Speaker Notes:**
To demonstrate how Red Hat technologies solve these challenges, we built Smart Travel Buddy — a fully functional AI travel agent running entirely on OpenShift.

---

## Slide 6 — Smart Travel Buddy

**Layout:** Content slide (title + bullet points)

**Title:** Smart Travel Buddy

**Content:**

**What it does**
- Conversational AI agent that creates personalized day-by-day travel itineraries
- Collects preferences through natural dialogue, researches live data, generates plans

**Three-phase agentic workflow**
- Interview — LLM collects travel details: destination, dates, interests, budget
- Research — MCP tools fetch real-time weather, exchange rates, Wikipedia info + RAG retrieval
- Itinerary — LLM synthesizes research into a structured JSON itinerary with day cards

**Tech stack**
- Frontend: React 19 + Tailwind CSS  |  Backend: FastAPI + LangGraph
- 3 MCP servers (weather, currency, wikipedia)  |  PostgreSQL + pgvector for RAG

**Speaker Notes:**
Smart Travel Buddy is a three-phase AI agent. First, it interviews you — asking about your destination, dates, interests, and budget through natural conversation. Then it enters a research phase where it calls external tools: weather forecasts, currency exchange rates, Wikipedia, and a curated knowledge base using RAG. Finally, it synthesizes everything into a structured day-by-day itinerary. The frontend is React with Tailwind, communicating with the backend over WebSocket for real-time updates. The backend uses LangGraph to orchestrate the workflow and MCP — the Model Context Protocol — to connect to external tools.

---

## Slide 7 — Architecture Diagram

**Layout:** Content slide with image

**Title:** Application architecture

**Image:** Architecture diagram showing:
- Red Hat OpenShift Container Platform (outer boundary)
- React Frontend → WebSocket → FastAPI Backend
- LangGraph Orchestrator with 3 phases: Interview → Research → Itinerary
- 3 MCP servers: Weather (OpenWeatherMap), Currency (Frankfurter), Wikipedia (REST)
- RAG Retriever (sentence-transformers, pgvector)
- PostgreSQL 16 (pgvector, knowledge base)
- OpenShift AI zone with LLM Inference (vLLM, OpenAI-compatible API)
- GitOps Pipeline: Git Repository (Kustomize) → Red Hat ArgoCD → OpenShift Cluster
- Container Registry (quay.io, 5 container images)

**Speaker Notes:**
Here's the full architecture. Everything runs inside OpenShift. The user interacts with a React frontend, which connects via WebSocket to a FastAPI backend. The LangGraph orchestrator manages the three-phase workflow. During research, it calls three MCP servers — each is its own pod — and a RAG retriever backed by PostgreSQL with pgvector. The LLM itself runs on OpenShift AI using vLLM, exposed as an OpenAI-compatible API. At the bottom, you can see the GitOps pipeline: Kustomize manifests in Git, synced to the cluster by ArgoCD. And all container images are stored in Quay.io. That's 7 pods total, all managed declaratively.

---

## Slide 8 — The AI Layer

**Layout:** Content slide (title + bullet points)

**Title:** The AI layer

**Content:**

**LangGraph orchestrator**
- State machine with 3 subgraphs: interview, research, itinerary
- Manages conversation memory, phase transitions, and tool coordination
- Real-time progress updates to the browser via WebSocket

**Model Context Protocol (MCP)**
- Open standard for connecting LLMs to external tools and data
- Each MCP server is a standalone microservice with SSE transport
- Weather (OpenWeatherMap), Currency (Frankfurter), Wikipedia (REST)

**RAG with pgvector**
- 24 curated knowledge files: destinations, cultural tips, packing guides
- Embeddings via sentence-transformers (all-MiniLM-L6-v2, 384 dimensions)
- Semantic search enriches the LLM's responses with domain knowledge

**Speaker Notes:**
Let's look at the AI layer in more detail. LangGraph is the orchestration framework — it models the agent as a state machine with three subgraphs. Each phase has its own logic, and transitions happen based on structured JSON signals from the LLM. MCP — the Model Context Protocol — is an open standard that Anthropic introduced for connecting LLMs to tools. Each of our three tool servers is a standalone FastMCP application running in its own pod, communicating via SSE. For RAG, we chunk 24 markdown files into 71 knowledge chunks, embed them with sentence-transformers, and store them in PostgreSQL using pgvector. During research, the agent does a semantic search to pull relevant travel tips into the LLM context.

---

## Slide 9 — Divider

**Layout:** Divider slide (large red text, white background)

**Title:** Red Hat technologies

**Supporting text:** How the Red Hat stack powers every layer of this application

**Speaker Notes:**
Now let's focus on the four Red Hat technologies that make this production-ready.

---

## Slide 10 — OpenShift AI + vLLM

**Layout:** Content slide (title + bullet points)

**Title:** OpenShift AI + vLLM

**Content:**

**Local LLM serving**
- vLLM runs on OpenShift AI with GPU acceleration
- Exposes an OpenAI-compatible API — drop-in replacement, no code changes
- Swap models freely: Llama, Mistral, Granite — same endpoint, different weights

**Why this matters**
- Data sovereignty — prompts and responses never leave your infrastructure
- Cost control — no per-token API charges, predictable GPU resource costs
- Latency — co-located model serving, no external network hops
- Compliance — full audit trail of model versions and configurations

**OpenShift AI value**
- Model lifecycle management, serving runtimes, and GPU scheduling
- Multi-model serving on shared GPU infrastructure
- Integrated monitoring and scaling for inference workloads

**Speaker Notes:**
The LLM runs locally on OpenShift AI using vLLM as the serving runtime. vLLM exposes an OpenAI-compatible API, which means our backend code doesn't know or care whether it's talking to OpenAI, a local Llama model, or IBM Granite. We just point the base URL to the internal service. This gives us three critical benefits. First, data sovereignty — every prompt and response stays within the cluster. Second, cost predictability — no per-token charges, just GPU resource costs. Third, model flexibility — we can swap models by changing a single configuration value, no code changes needed. OpenShift AI adds model lifecycle management, GPU scheduling, and monitoring on top.

---

## Slide 11 — OpenShift Container Platform

**Layout:** Content slide (title + bullet points)

**Title:** OpenShift Container Platform

**Content:**

**7 microservices, one platform**
- Frontend (nginx) · Backend (FastAPI) · 3 MCP servers · PostgreSQL · Seed Job
- Each service has its own container image, independently deployable
- Service mesh networking: internal DNS, automatic service discovery

**Enterprise-grade security**
- Random non-root UIDs — no container runs as root
- Secret management for API keys and database credentials
- TLS edge termination via Routes for external access

**Operational benefits**
- Resource requests/limits per pod for predictable scheduling
- PersistentVolumeClaims for database storage
- Container registry (Quay.io) for image management and scanning
- Rolling updates with zero-downtime deployments

**Speaker Notes:**
OpenShift is the foundation. We have 7 microservices — each with its own container image, each independently deployable. OpenShift handles service discovery automatically — the backend just calls "mcp-weather:8000" and DNS resolution takes care of the rest. Security is enforced by default: containers run with random non-root UIDs, secrets are managed as Kubernetes resources, and external traffic gets TLS edge termination through OpenShift Routes. On the operational side, we set resource requests and limits for each pod, use PersistentVolumeClaims for PostgreSQL data, and store all images in Quay.io. This is the kind of enterprise infrastructure you get out of the box — we didn't have to build any of it.

---

## Slide 12 — GitOps with Kustomize

**Layout:** Content slide (title + bullet points)

**Title:** GitOps with Kustomize

**Content:**

**Declarative infrastructure**
- Every Kubernetes resource is defined in YAML — deployments, services, secrets, routes
- Git is the single source of truth for the entire application state
- Changes go through pull requests: reviewed, approved, auditable

**Base + overlay pattern**
- Base: environment-agnostic manifests (7 deployments, services, PVCs)
- Overlays: environment-specific config (dev, staging, prod)
- Dev overlay: image registry (quay.io), secrets, TLS routes, debug flags

**Reproducibility**
- Any environment can be rebuilt from scratch with a single command
- Image transformers automatically apply registry prefixes across all resources
- ConfigMaps for knowledge data, Secrets for credentials — all version-controlled

**Speaker Notes:**
Our entire infrastructure is declared in Git using Kustomize. The base directory contains environment-agnostic manifests — deployments, services, PVCs — for all 7 components. The dev overlay adds environment-specific configuration: the Quay.io image registry, API key secrets, TLS routes, and debug flags. Kustomize's image transformer is particularly useful — we define container images as "smart-travel-buddy/backend" in the base, and the overlay automatically rewrites them to "quay.io/gfontana/smart-travel-buddy-backend." This means the base manifests work locally with Podman and on any registry. Everything is reproducible — we can tear down the entire environment and rebuild it from scratch with a single "oc apply -k" command.

---

## Slide 13 — ArgoCD

**Layout:** Content slide (title + bullet points)

**Title:** ArgoCD

**Content:**

**Continuous deployment**
- ArgoCD watches the Git repository and syncs changes to the cluster
- Push to main → ArgoCD detects → applies Kustomize manifests → pods update
- No manual kubectl/oc commands in production — everything flows through Git

**Drift detection and self-healing**
- Continuously compares desired state (Git) vs. live state (cluster)
- Automatically corrects manual changes — the cluster always matches Git
- Visual dashboard shows sync status, health, and resource tree

**Day 2 operations**
- Rollback to any previous commit — instant, auditable recovery
- Multi-environment promotion: dev → staging → prod via Git branches
- Integrated with OpenShift — runs as an operator, SSO, RBAC

**Speaker Notes:**
ArgoCD closes the loop. It watches our Git repository and continuously syncs the Kustomize manifests to the cluster. When we push a change — say, updating an image tag or adding an environment variable — ArgoCD detects it, renders the Kustomize output, and applies it. No one runs kubectl or oc in production. Drift detection is the killer feature: if someone manually edits a resource on the cluster, ArgoCD notices the difference and corrects it. The cluster always matches what's in Git. For day 2 operations, rollback is just a Git revert. Multi-environment promotion is merging between branches. And since ArgoCD runs as an OpenShift operator, it integrates with SSO and RBAC out of the box.

---

## Slide 14 — The Red Hat Advantage

**Layout:** Content slide (title + bullet points)

**Title:** The Red Hat advantage

**Content:**

**End-to-end AI platform**
- OpenShift AI serves the LLM locally — data never leaves your infrastructure
- OpenShift runs all 7 microservices with enterprise security and networking
- GitOps + ArgoCD ensures every deployment is reproducible and auditable

**Open source, no lock-in**
- LangGraph, FastAPI, MCP, PostgreSQL — all open source frameworks
- OpenAI-compatible API means any model works: swap Llama for Granite in minutes
- Kustomize and ArgoCD are CNCF projects — portable across any Kubernetes

**From prototype to production**
- Same application runs locally with Podman or at scale on OpenShift
- The platform handles the hard parts: GPU scheduling, secrets, TLS, scaling
- Developers focus on the AI logic — Red Hat handles the infrastructure

**Speaker Notes:**
Let me bring it all together. The Red Hat stack gives you an end-to-end AI platform. OpenShift AI handles model serving with data sovereignty. OpenShift provides the enterprise Kubernetes foundation with security and networking built in. GitOps and ArgoCD make deployments reproducible and auditable. The key philosophy is open source with no lock-in. Every framework we used — LangGraph, FastAPI, MCP, PostgreSQL — is open source. The OpenAI-compatible API means we can swap models without code changes. Kustomize and ArgoCD are CNCF projects that work on any Kubernetes. And the developer experience is seamless: this same application runs locally with Podman for development and at scale on OpenShift for production. The platform handles GPUs, secrets, TLS, and scaling — developers just write AI logic.

---

## Slide 15 — Demo Transition

**Layout:** Divider slide (centered, large text)

**Title:** Demo time

**Subtitle:** Live walkthrough of Smart Travel Buddy on OpenShift

**Speaker Notes:**
Let's see it in action. I'll show you the application running on OpenShift — from the conversation with the AI agent, through the real-time research phase, to the generated itinerary. I'll also show the OpenShift console so you can see the pods, the ArgoCD dashboard, and the GitOps workflow.

---

## Slide 16 — Closing

**Layout:** Closing slide (red background)

**Title:** Thank you

**Body:** Red Hat is the world's leading provider of enterprise open source software solutions. Award-winning support, training, and consulting services make Red Hat a trusted adviser to the Fortune 500.

**Speaker Notes:**
Thank you for your time. Happy to take any questions about the architecture, the Red Hat technologies, or the implementation details.
