import streamlit as st
import json
import asyncio
from pathlib import Path
from bug_finder.cli import find_bugs_with_consensus, get_git_changed_files, DEFAULT_WORKER_CONFIGS

st.set_page_config(page_title="Bug Finder Consensus Viewer", layout="wide")

st.title("🐞 Bug Finder Consensus Viewer")

# Sidebar for file selection
with st.sidebar:
    st.header("Report Selection")

    # Check local directory for JSON files
    # We check current directory and examples directory
    current_dir = Path.cwd()
    search_paths = [current_dir, current_dir / "examples"]

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

    st.divider()

    st.header("Run Analysis")
    
    # Target Selection
    default_target = str(Path.cwd())
    target_path = st.text_input("Target Path", value=default_target, help="Absolute path to file or directory to analyze")
    diff_only = st.checkbox("Analyze Git Diff Only", value=False, help="Only analyze files changed in git")

    # Model Selection
    available_models = [cfg["model"] for cfg in DEFAULT_WORKER_CONFIGS]
    model_labels = [f"{cfg['role']} ({cfg['model']})" for cfg in DEFAULT_WORKER_CONFIGS]
    
    st.subheader("Select Models")
    selected_indices = []
    
    # Create checkboxes for each model
    for i, cfg in enumerate(DEFAULT_WORKER_CONFIGS):
        default_checked = True 
        # Uncheck higher cost models by default if desired, or keep all checked
        if st.checkbox(f"{cfg['role']} - {cfg['model']}", value=default_checked, key=f"model_{i}"):
            selected_indices.append(i)

    run_button = st.button("🚀 Run Analysis", type="primary", use_container_width=True)

if run_button:
    if not selected_indices:
        st.error("Please select at least one model to run.")
    else:
        selected_configs = [DEFAULT_WORKER_CONFIGS[i] for i in selected_indices]
        
        target = Path(target_path)
        if not target.exists():
            st.error(f"Target path does not exist: {target_path}")
        else:
            specific_files = None
            if diff_only:
                if not target.is_dir():
                     st.error("Git diff can only be run on a directory/repo.")
                     st.stop()
                     
                with st.spinner("Detecting git changes..."):
                    specific_files = get_git_changed_files(target)
                
                if not specific_files:
                    st.warning("No git changes detected.")
                    st.stop()
                else:
                    st.success(f"Found {len(specific_files)} changed files.")
            
            # Create a placeholder for logs
            log_container = st.empty()
            
            with st.spinner(f"Running analysis on {target.name}... This may take a few minutes."):
                try:
                    # Run the async function
                    # We need a new event loop policy for streamlit if it doesn't handle it well, 
                    # but typically asyncio.run works if no other loop is running.
                    result = asyncio.run(
                        find_bugs_with_consensus(
                            target_path=str(target),
                            worker_configs=selected_configs,
                            verbose=True,
                            specific_files=specific_files
                        )
                    )
                    
                    # Save the result to a file so we can reload it
                    output_file = Path("bug_report.json")
                    with open(output_file, "w") as f:
                        json.dump(result, f, indent=2, default=str)
                        
                    st.success("Analysis complete! Reloading report...")
                    # Set the state to reload or just let the report loader pick it up
                    # forcing a rerun might be good
                    st.rerun()
                    
                except Exception as e:
                    st.error(f"Analysis failed: {e}")
                    import traceback
                    st.code(traceback.format_exc())

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
    
    # Fallback to try loading the just generated report if run just finished
    if Path("bug_report.json").exists():
        try:
            with open("bug_report.json", "r") as f:
                data = json.load(f)
            # Update selection to point to this new file if possible, or just use data
        except:
            pass
            
    if not data:
         # If still no data
        st.info(
            "No report file found or selected. Use the sidebar to run a new analysis."
        )
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
