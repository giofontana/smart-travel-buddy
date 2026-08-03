# Building AI Agents on Red Hat OpenShift -- Speaker Notes

# Demo Narrative

**Duration:** ~15 minutes
**Goal:** Show Smart Travel Buddy running live on OpenShift, highlighting agentic AI, MCP tools, RAG, and the unified container+VM platform.

## Pre-Demo Setup Checklist

- [ ] OpenShift console open in a browser tab
- [ ] Smart Travel Buddy frontend open in a browser tab (fresh session, no prior conversation)
- [ ] OpenShift AI dashboard open showing the vLLM model serving endpoint (Qwen-14b-fp8)
- [ ] MLflow UI open in a tab (optional, for showing traces after)
- [ ] Terminal with `oc` CLI ready (for showing pods/VMs if needed)

---

## Act 1: Set the Stage (~3 min)

### Show the OpenShift Console

**Say:** "Before we start chatting with the agent, let me show you what's running behind the scenes."

1. **Switch to the OpenShift console.** Navigate to the project/namespace where Smart Travel Buddy is deployed.

2. **Show the running pods.** Point out:
   - `backend` pod -- the FastAPI backend with the LangGraph orchestrator
   - `frontend` pod -- the React UI, served by nginx
   - `mcp-weather`, `mcp-currency`, `mcp-wikipedia` pods -- the three MCP tool servers
   - The PostgreSQL VM (if using the VM overlay) -- highlight that this is a VirtualMachine, not a Pod

   **Say:** "Notice we have containers and a virtual machine running side by side on the same platform. The application services are containers, but the PostgreSQL database for our RAG knowledge base is running as a VM using OpenShift Virtualization. This is a single platform for all your workloads."

3. **Show the model serving endpoint in OpenShift AI.** Navigate to the OpenShift AI dashboard and show the vLLM InferenceService for Qwen-14b-fp8.

   **Say:** "Our LLM is Qwen 14-billion parameters, quantized to FP8 for efficiency. It's served by vLLM and managed by OpenShift AI using KServe. It exposes an OpenAI-compatible API, so any framework -- LangChain, LangGraph, or even a simple HTTP client -- can talk to it."

---

## Act 2: The Conversation (~7 min)

### Switch to the Smart Travel Buddy UI

**Say:** "Now let's plan a trip. I'll show you the three phases of the agent: interview, research, and itinerary generation."

### Phase 1: Interview

4. **Type the first message:**

   > "Paris"

   **Say:** "I'm starting a conversation with the agent. Right now we're in the Interview phase. The LangGraph orchestrator is running the interview subgraph, which uses the LLM to ask clarifying questions."

5. **Wait for the agent to respond.** It will ask about dates, interests, budget, etc.

   **Say:** "Notice the agent is asking follow-up questions -- it needs to know my dates, what I'm interested in, and my budget. This isn't a simple prompt-response. The agent has a structured state machine that tracks what information it has collected and what it still needs."

6. **Reply with dates:**

   > "Oct 1st to 5th"

7. **Reply with interests:**

   > "Arts and food"

8. **Reply with budget and constraints:**

   > "Mid-range. No special requirements."

   **Say:** "Once the agent has gathered enough information -- destination, dates, interests, budget -- it transitions to the Research phase automatically."

### Phase 2: Research

9. **Point out the progress cards** that appear on the right panel as research starts.

   **Say:** "Now watch the right panel. The agent is calling its external tools in parallel:"

   - "**Weather MCP** -- querying the OpenWeatherMap API for a 5-day forecast for Tokyo."
   - "**Currency MCP** -- fetching the USD to JPY exchange rate from the Frankfurter API."
   - "**Wikipedia MCP** -- pulling a summary about Tokyo from Wikipedia."
   - "**RAG** -- searching our curated knowledge base of destination guides, cultural tips, and packing lists using semantic search against pgvector."

   **Say:** "Each of these is a separate MCP server -- a containerized microservice that exposes tools via the Model Context Protocol. The weather, currency, and Wikipedia calls happen in parallel using asyncio. The RAG retrieval runs after, enriching the context with curated travel knowledge."

10. **Open MLflow interface**, toggle it open to show the trace visualization.

    **Say:** "This flow view shows the trace of the agent's actions -- you can see the messages flowing between the backend, each MCP server, and the RAG system."

### Phase 3: Itinerary

11. **Wait for the itinerary to render.** Day cards will appear on the right side with:
    - Day-by-day activities (morning, afternoon, evening)
    - Weather forecast per day (temperature, conditions)
    - Currency converter widget
    - Packing list with checkboxes
    - Cultural tips

    **Say:** "And here's the final itinerary. The LLM synthesized all the research data -- weather, exchange rates, Wikipedia info, and RAG knowledge -- into a structured, day-by-day plan. Each day has morning, afternoon, and evening activities, tailored to my interests in nature, culture, and food."

12. **Walk through the itinerary highlights:**

    - **Day cards:** "Each day shows activities with descriptions and practical tips."
    - **Weather:** "Real weather data for my travel dates -- so the agent planned outdoor activities for clear days."
    - **Currency:** "A live converter showing 1 USD equals approximately 150 JPY."
    - **Packing list:** "Generated based on the destination climate and trip type."
    - **Cultural tips:** "Japan-specific etiquette -- bowing, removing shoes, chopstick etiquette -- pulled from our RAG knowledge base."

---

## Act 3: Behind the Scenes (~3 min)

### Show the GitOps Manifests (optional, if time permits)

13. **Briefly show the Kustomize structure:**

    **Say:** "The entire application is deployed via GitOps. We have a base layer of Kubernetes manifests -- deployments, services, PVCs -- and a dev overlay that adds secrets, configmaps, routes, and image registry references. A single `oc apply -k` or ArgoCD sync deploys everything."

14. **Briefly show the Application on ArgoCD:**

    **Say:** "And here is the ArgoCD application, where you can see all application components, including the VM! All deployed and managed through ArgoCD. If someone by any reason makes a mistake, ArgoCD will detect it and revert to the desired state.

    - On OpenShift delete the backend-config ConfigMap and sync the ArgoCD app. Show that the CM is reverted back.

    **Say:** "As you can see, ArgoCD was able to detect the change and revert back to the desired state."

### Show MLflow (optional, if time permits)

14. **Switch to MLflow UI** and show the trace of the conversation:

    **Say:** "We also have MLflow integrated for experiment tracking and observability. Each conversation is logged as a run with traces for every LLM call and MCP tool invocation. You can see token usage, latency, and cost per interaction. This is critical for production -- you need to know how your agent is performing and how much it's costing."

### Wrap Up the Demo

15. **Switch back to the architecture slide (slide 29).**

    **Say:** "So to recap what you just saw: a conversational AI agent with a three-phase agentic workflow, powered by an LLM served by vLLM on OpenShift AI, calling external tools via MCP servers running as containers, enriched by a RAG knowledge base in a PostgreSQL VM -- all running on a single Red Hat OpenShift platform, deployed via GitOps."

---

## Demo Recovery Plan

**If the LLM is slow:** "The model is running inference on a single GPU -- in a production deployment you'd scale this horizontally with llm-d for distributed inference. Let me show you the architecture while we wait."

**If an MCP server fails:** "This is a live demo with real API calls. Let me show you the pod logs to diagnose." (`oc logs deployment/mcp-weather -n smart-travel-buddy`). The itinerary will still generate with partial data.

**If WebSocket disconnects:** Refresh the browser. The backend creates a new session automatically.

**If nothing works:** Switch to a pre-recorded video or screenshots (slide 27 has the app screenshot). "Let me walk you through a completed session instead."

---

## Key Talking Points to Weave In During Demo

- **MCP is the open standard** for connecting AI agents to tools. Each MCP server is a self-contained microservice with a defined interface. This is how agents interact with the real world.
- **LangGraph gives you control** over the agent flow. Unlike a simple chain, you get a state machine with explicit phases and transitions. The agent knows what it has collected and what it still needs.
- **RAG grounds the agent** in curated knowledge. The LLM's general knowledge is enriched with specific, verified travel information that you control.
- **Containers + VMs on one platform** is a real-world pattern. Databases, legacy systems, and appliances often run as VMs. OpenShift Virtualization means you don't need a separate infrastructure for them.
- **GitOps makes it reproducible.** The entire stack -- application, MCP servers, database, model serving -- is defined as code and deployed declaratively.
- **Observability is not optional.** MLflow traces every LLM call and tool invocation. In production, you need to know what your agent is doing, how long it takes, and how much it costs.
