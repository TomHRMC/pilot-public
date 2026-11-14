### 1. The Topics: What Wikis to Build

Since you want to avoid one giant, monolithic wiki, breaking them down by domain is smart. For a SaaS app entering the integration and usability testing phase, I recommend the following five focused wikis:

| Wiki Domain | Purpose for the Agent during Testing | Key Inputs (Raw Docs) |
| --- | --- | --- |
| **Help & User Docs** | To quickly answer "How do I do X?" or generate tooltips during usability testing. | Product requirements, user flows, frontend designs. |
| **Frontend State & UI** | To understand how components interact, where state is managed, and UI logic. | Frontend implementations, component libraries. |
| **Data & DB Schema** | To trace where information is stored when testing frontend inputs. | DB schema, data dictionaries, migration logs. |
| **API & Routing** | To map frontend actions to backend logic (crucial for integration testing). | `openapi.json`, backend designs, endpoint specs. |
| **Business Logic & Market** | To verify if the app actually meets the core product requirements and market needs. | PRDs, market analysis, competitor research. |

---

### 2. The Formal Methodology: The 3-Layer Architecture

To build this systematically, you should adopt the 3-layer architecture of the LLM Wiki pattern. Create a master directory for your wikis, and for *each* of the domains listed above, structure them into these three distinct layers:

* **Layer 1: Raw Sources (`/raw`)**
This is where you drop your existing Markdown docs, JSON files, and designs. **These files are immutable.** You never edit them, and the LLM never edits them. They act as the absolute source of truth.
* **Layer 2: The Compiled Wiki (`/wiki`)**
This is the folder the LLM owns. It contains the highly structured, heavily cross-linked Markdown pages (e.g., entity pages, concept summaries, state management maps) that the AI generates based on the raw sources.
* **Layer 3: The Schema (`schema.md`)**
This is a single configuration file that sits at the top of the directory. It tells your Llama agent *how* to write the wiki. It defines the required YAML frontmatter (tags, date updated, source files), the tone, the naming conventions, and the rules for cross-linking pages.

---

### 3. The 3 Core Operations

Once the structure is in place, you manage the wikis using three distinct processes (which you can script your local Llama agent to run):

**1. Ingest (Compile Once)**
You do not want the agent reading raw documents at runtime. Instead, run an "Ingest" script. You point the Llama agent at the `/raw` folder and tell it to read the files and compile them into the `/wiki` folder according to the rules in `schema.md`. It creates an `index.md` (a master map of the wiki) and individual concept pages.

**2. Query (Read Fast)**
During your integration testing, when you ask the agent a question (e.g., *"What endpoint does the checkout button hit?"*), the agent should **only** be allowed to read the `index.md` file and the specific `/wiki` pages it references. It never touches the raw OpenAPI JSON at this stage, saving massive amounts of tokens.

**3. Lint (Maintain Health)**
Because you are actively testing and likely finding bugs or missing features, the code will change. Once a week, you run a "Lint" prompt. You ask the Llama agent to scan the `/wiki` folder and look for:

* Contradictions (e.g., the DB schema wiki says a field is a string, but the API wiki says it is an integer).
* Orphaned pages with no links.
* Stale information that doesn't match newly added raw files.

### A Quick Note on the Router

Because you are breaking this into multiple wikis, you will need a "Router" prompt for your Llama agent. When you ask a question, the agent's very first task should be evaluating the prompt and deciding *which* of the five wikis to query (or if it needs to query two, like Frontend and API, to trace an integration bug).
