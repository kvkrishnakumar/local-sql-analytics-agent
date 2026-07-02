---
# Local Agentic SQL Analytics Engine

An advanced, privacy-first Text-to-SQL data analytics platform designed to run entirely locally. Powered by **LLaMA3 via Ollama**, **DuckDB**, and **Streamlit**, this intelligent data agent features automated database quoting logic, dynamic cross-dataset visual analytics, and an autonomous **Self-Healing SQL Repair Loop** to intercept and resolve database parser errors on the fly.

---

## System Architecture & Workflow

The architecture is built for extreme fault-tolerance, ensuring that natural language queries translate cleanly into valid relational operations without exposing raw data rows to the LLM engine.

1. **Schema Extraction (Privacy-First):** Only the structural metadata (column names and data types) is sent to the local LLaMA3 model. Zero operational data rows are transmitted outside the runtime environment.
2. **Text-to-SQL Compilation:** The local model parses the user's plain-English intent, automatically applying strict structural rules (such as auto-wrapping multi-word columns containing spaces or parentheses like `"Temperature (C)"` in double quotes).
3. **Execution Layer (DuckDB):** The query executes instantly inside an in-memory DuckDB database engine for lightning-fast aggregation.
4. **Autonomous Self-Healing Loop:** If DuckDB encounters an execution exception (e.g., syntax error, column mismatch, or structural bug), the background **SQL Correction Agent** captures the runtime error footprint, bundles it with the broken query, and instructs LLaMA3 to debug, rewrite, and re-execute the query cleanly.
5. **Smart Analytics Visualizer:** The resultant Pandas DataFrame is dynamically analyzed; if matching categorical strings and numerical metrics are identified, the system automatically builds interactive statistical bar/line charts.

---

## One-Command Quick Start (Docker Deployment)

The entire application ecosystem is fully containerized. To build and launch the platform without needing a local Python configuration, execute the following commands in your terminal.

### Prerequisites
* Ensure [Docker Desktop](https://www.docker.com/products/docker-desktop/) is installed and running on your host machine.
* Ensure [Ollama](https://ollama.com/) is running locally with the `llama3` model downloaded (`ollama run llama3`).

### 1. Navigate to the Repository
Open your terminal and navigate to your core project directory:
```bash
cd "sql_agt"

---

## Universal Dataset Ingestion (CSV / XLSX / JSON)

The engine is engineered with an arbitrary, schema-agnostic ingestion pipeline. Users do not need to hardcode paths or reconfigure backend tables; any user can bring their own data and start querying immediately.

### Supported File Frameworks:
* **CSV (`.csv`):** Auto-detects delimiters, handles malformed lines, and dynamically infers schemas.
* **Excel (`.xlsx`):** Parses multi-tab sheets and transforms tabular matrices into clean relational data structures.
* **JSON (`.json`):** flattens structured arrays or key-value object streams into queryable flat-table formats.

### How to Ingest Your Own Data:
1. **Launch the Platform:** Open the workspace dashboard at `http://localhost:8501`.
2. **Upload via UI:** Use the interactive drag-and-drop file uploader component in the workspace sidebar to upload your local `.csv`, `.xlsx`, or `.json` file.
3. **Automated Structural Ingestion:** The moment a file registers, the backend instantly uses **DuckDB** to execute an in-memory conversion, map the columns, and register the dataset as a local relational target.
4. **Immediate Analysis:** Type a question in plain English relative to your uploaded file headers. The underlying compiler will immediately map your question directly to the fresh dataset schema.

---

## Key Functional Features Completed

* **Dynamic Multi-Format Ingestion:** Seamlessly processes ad-hoc user uploads (CSV, Excel, JSON) via the web UI, sanitizing bad row configurations or unexpected text-delimiter configurations on the fly without system restarts.
* **Double-Quoting Schema Automation:** Prompt-engineered instructions force the engine to natively recognize and handle complex column headers with spaces, backslashes, and parentheses.
* **Self-Correction SQL Loop:** Background retry agent catches exceptions, reasons through database logs, and displays the successfully healed query and data parameters without manual developer intervention.
* **Automated Visual Analytics:** Scans query columns dynamically to suggest and render meaningful graphical plots right under the grid.
* **SQLite Audit Logging:** Every transactional execution, operational state, error signature, and successful execution parameter is serialized locally into a `logs.db` database for auditing.


## Technical Bottlenecks & Engineered Mitigations
During development and testing, several low-level database constraints and execution bottlenecks were identified. The following architectural strategies were implemented to guarantee system stability:

### 1. In-Memory Kernel Crashes (Large Dataset Operations)
* **The Bottleneck:** When running heavy aggregation queries or self-healing loops on massive source datasets, the local memory allocation boundaries would occasionally breach, causing the local execution kernel to silently hang or crash.
* **The Mitigation:** We transitioned the relational data tier entirely to **DuckDB**. Because DuckDB is highly optimized for vectorized columnar operations, it reads and processes chunks of data efficiently without overwhelming the execution thread memory pool, eliminating kernel crashes entirely.

### 2. SQL Syntax Mismatches with Complex Column Names
* **The Bottleneck:** Source files frequently contain complex business metadata columns with spaces or brackets, such as `Temperature (C)` or `Weekly Sales`. Standard Text-to-SQL translations generated raw strings like `WHERE Temperature (C) > 20`, which breaks the database parser because it tries to interpret `(C)` as a SQL function call.
* **The Mitigation:** We established strict, zero-temperature prompt engineering constraint rules inside LLaMA3, mandating that any multi-word column header or header containing special characters *must* be natively encapsulated inside double quotes (e.g., `"Temperature (C)"`).

### 3. Column Ambiguity and Target Mapping Disconnects
* **The Bottleneck:** When users supplied broad, conversational queries (e.g., *"Show data for the top region"*), the LLM layer would occasionally guess or generate column identifiers that did not exist in the source dataset, causing execution exceptions.
* **The Mitigation:** We built a dedicated **Schema-Reflector Pre-Pass Layer**. Before LLaMA3 evaluates the plain-English string, your script explicitly extracts the exact, current table schema structure and binds it directly into the prompt context window. By forcing the LLM to map its relational decisions against a rigid column structural dictionary, semantic guesswork was completely eliminated.
