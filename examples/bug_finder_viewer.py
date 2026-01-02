import streamlit as st
import json
from pathlib import Path

st.set_page_config(page_title="Bug Finder Consensus Viewer", layout="wide")

st.title("🐞 Bug Finder Consensus Viewer")

# Sidebar for file selection
with st.sidebar:
    st.header("Report Selection")

    # Check local directory for JSON files
    # We check current directory and examples directory
    current_dir = Path.cwd()
    search_paths = [current_dir]
    if (current_dir / "examples").exists():
        search_paths.append(current_dir / "examples")

    local_files = []
    for path in search_paths:
        local_files.extend(list(path.glob("*.json")))

    # Filter out package.json or similar if accidentally in root
    local_files = [
        f for f in local_files if "package.json" not in f.name and "tsconfig.json" not in f.name
    ]

    options = [str(f) for f in local_files]
    # Remove duplicates if any
    options = list(set(options))
    options.sort()

    default_index = 0
    # Try to find bug_report.json as default
    bug_report_candidates = [o for o in options if "bug_report.json" in o]
    if bug_report_candidates:
        default_index = options.index(bug_report_candidates[0])

    selected_file_path = st.selectbox(
        "Select a report file:",
        options=options,
        index=default_index if options else 0,
        placeholder="No JSON reports found",
    )

    uploaded_file = st.file_uploader("Or upload a JSON report", type="json")

# Load data
data = None

if uploaded_file:
    try:
        data = json.load(uploaded_file)
    except Exception as e:
        st.error(f"Error loading uploaded file: {e}")
elif selected_file_path:
    try:
        with open(selected_file_path, "r") as f:
            data = json.load(f)
    except Exception as e:
        st.error(f"Error loading {selected_file_path}: {e}")
else:
    st.info(
        "No report file found or selected. Please run the bug finder script first to generate a 'bug_report.json'."
    )
    st.code("python examples/bug_finder_example.py <path_to_code>")
    st.stop()

if not data:
    st.stop()

# Display Task Info
st.markdown(f"**Task:** {data.get('task', 'Unknown Task')}")

# Tabs
tab1, tab2, tab3, tab4 = st.tabs(
    ["📝 Final Report", "👷 Worker Findings", "📊 Consensus Stats", "🔍 Raw Data"]
)

with tab1:
    st.header("Consolidated Final Report")
    report = data.get("final_report", "")

    # Check if report is empty or purely whitespace
    if report and str(report).strip():
        st.markdown(report)
        st.divider()
        st.caption(
            "Use the copy button in the top-right of the code block below to copy the report."
        )
        st.code(report, language="markdown")
    else:
        st.warning("⚠️ No final report available.")
        st.markdown(
            """
        **Possible reasons:**
        - The Orchestrator agent failed to generate a response.
        - API connection issues (check logs).
        - No consensus was reached among workers (though usually a report is still attempted).
        
        👉 **Please check the 'Worker Findings' tab to see individual bug reports.**
        """
        )

        # Check for worker errors to display here as a hint
        workers = data.get("worker_results", [])
        failures = [w for w in workers if not w.get("success", True)]
        if failures:
            st.error(f"Found {len(failures)} worker agent failures:")
            for f in failures:
                st.write(f"- **{f.get('role')}**: {f.get('error', 'Unknown error')}")

    if "orchestrator_result" in data:
        with st.expander("Orchestrator Details"):
            st.json(data["orchestrator_result"])

with tab2:
    st.header("Individual Worker Findings")
    workers = data.get("worker_results", [])

    if not workers:
        st.info("No worker results found.")

    for i, worker in enumerate(workers):
        role = worker.get("role", f"Worker {i + 1}")
        # Try to infer model/type if available in result or try to parse from role/id
        agent_id = worker.get("agent_id", "")

        success = worker.get("success", True)
        status_icon = "✅" if success else "❌"

        with st.expander(f"{status_icon} {role}"):
            if not success:
                st.error(f"Error: {worker.get('error', 'Unknown error')}")

            response = worker.get("response", "")
            if response:
                st.markdown(response)
            else:
                st.text("No response content.")

            st.divider()
            st.caption(f"Agent ID: {agent_id}")
            st.caption(f"Value: {worker.get('value', 'N/A')}")

            if "context" in worker and worker["context"]:
                with st.expander("Context provided to agent"):
                    st.json(worker["context"])

with tab3:
    st.header("Consensus Statistics")
    consensus = data.get("worker_consensus", {})

    if consensus:
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Converged", "Yes" if consensus.get("converged") else "No")
        with col2:
            st.metric("Iterations", consensus.get("iterations", 0))
        with col3:
            st.metric("Agent Count", len(data.get("worker_results", [])))

        st.subheader("Convergence History")
        # If we have history data, we could plot it, but simple JSON is fine for now
        st.json(consensus)
    else:
        st.info("No consensus data available.")

with tab4:
    st.json(data)
