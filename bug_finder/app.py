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

    if options:
        selected_file_path = st.selectbox(
            "Select a report file:",
            options=options,
            index=default_index if options else 0,
            placeholder="No JSON reports found",
        )
    else:
        st.info("No existing report files found in current or examples directory.")
        selected_file_path = None

    uploaded_file = st.file_uploader("Or upload a JSON report", type="json")

    st.divider()

    st.header("Run Analysis")
    
    # Target Selection
    default_target = str(Path.cwd())
    target_path = st.text_input("Target Path", value=default_target, help="Absolute path to file or directory to analyze")
    diff_only = st.checkbox("Analyze Git Diff Only", value=False, help="Only analyze files changed in git")

    st.divider()
    
    st.header("🔍 PR Review Mode")
    st.caption("Review a GitHub Pull Request with AI agents")
    
    enable_pr_mode = st.checkbox(
        "Enable PR Review Mode", 
        value=False,
        help="Switch to review mode for a specific GitHub Pull Request"
    )
    
    if enable_pr_mode:
        pr_number_input = st.number_input(
            "PR Number", 
            min_value=1, 
            value=1, 
            step=1,
            help="GitHub PR number to review"
        )
        pr_repo_input = st.text_input(
            "Repository (optional)", 
            value="",
            placeholder="owner/repo",
            help="Leave empty to use current repo"
        )
        
        col1, col2 = st.columns(2)
        with col1:
            include_pr_comments = st.checkbox("Include Comments", value=True)
        with col2:
            include_pr_reviews = st.checkbox("Include Reviews", value=True)
        
        checkout_branch = st.checkbox(
            "Checkout PR Branch", 
            value=True,
            help="Check out the PR branch locally for analysis"
        )
    else:
        pr_number_input = None
        pr_repo_input = ""
        include_pr_comments = False
        include_pr_reviews = False
        checkout_branch = False
    
    st.divider()

    # Model Selection
    available_models = [cfg.get("model", cfg.get("type", "unknown")) for cfg in DEFAULT_WORKER_CONFIGS]
    model_labels = [f"{cfg['role']} ({cfg.get('model', cfg.get('type', 'unknown'))})" for cfg in DEFAULT_WORKER_CONFIGS]
    
    st.subheader("Select Models")
    selected_indices = []
    
    # Create checkboxes for each model
    for i, cfg in enumerate(DEFAULT_WORKER_CONFIGS):
        default_checked = True 
        # Uncheck higher cost models by default if desired, or keep all checked
        model_label = cfg.get("model", cfg.get("type", "unknown"))
        if st.checkbox(f"{cfg['role']} - {model_label}", value=default_checked, key=f"model_{i}"):
            selected_indices.append(i)

    run_button = st.button("🚀 Run Analysis", type="primary", use_container_width=True)

if run_button:
    if not selected_indices:
        st.error("Please select at least one model to run.")
    else:
        selected_configs = [DEFAULT_WORKER_CONFIGS[i] for i in selected_indices]
        
        # Validate orchestrator API key upfront
        import os
        orchestrator_api_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
        if not orchestrator_api_key:
            st.error("❌ Orchestrator API key not configured. Please set `GEMINI_API_KEY` or `GOOGLE_API_KEY` in your environment or `.env` file.")
            st.stop()
        
        target = Path(target_path)
        if not target.exists():
            st.error(f"Target path does not exist: {target_path}")
        else:
            specific_files = None
            
            # Determine the effective PR number (handle type safety)
            effective_pr_number = None
            if enable_pr_mode and pr_number_input is not None and pr_number_input > 0:
                effective_pr_number = int(pr_number_input)
            
            # Handle conflict between diff_only and PR mode
            if diff_only and effective_pr_number:
                st.warning("Both 'Analyze Git Diff Only' and 'PR Number' are set. PR mode takes precedence.")
                # PR mode takes precedence, so we don't populate specific_files from git diff
            elif diff_only:
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
                    import concurrent.futures
                    import queue
                    import time

                    # Create a queue for status updates
                    status_queue = queue.Queue(maxsize=100)
                    
                    def status_callback(msg):
                        try:
                            status_queue.put_nowait(msg)
                        except queue.Full:
                            pass # Drop if full to prevent blocking

                    # Create a placeholder for status updates
                    status_placeholder = st.empty()
                    status_placeholder.info("Initializing analysis...")
                    
                    # Keep track of all status messages for display
                    status_messages = []

                    # Run the async function in a separate thread to avoid event loop conflicts with Streamlit
                    with concurrent.futures.ThreadPoolExecutor() as executor:
                        future = executor.submit(
                            asyncio.run,
                            find_bugs_with_consensus(
                                target_path=str(target),
                                worker_configs=selected_configs,
                                verbose=True,
                                specific_files=specific_files,
                                pr_number=effective_pr_number,
                                repo=pr_repo_input if pr_repo_input else None,
                                include_pr_comments=include_pr_comments,
                                include_pr_reviews=include_pr_reviews,
                                checkout_pr_branch_flag=checkout_branch,
                                status_callback=status_callback,
                            ),
                        )
                        
                        # Poll for status updates while waiting for result
                        while not future.done():
                            try:
                                # Get all available messages and add to our list
                                while not status_queue.empty():
                                    msg = status_queue.get_nowait()
                                    status_messages.append(msg)
                                
                                # Display all messages as a running log
                                if status_messages:
                                    # Show all messages, one per line
                                    display_text = "\n".join(status_messages[-20:])  # Keep last 20 to avoid too long
                                    status_placeholder.text(display_text)
                            except queue.Empty:
                                pass
                            
                            time.sleep(0.1)
                        
                        # Process any remaining messages
                        try:
                            while not status_queue.empty():
                                msg = status_queue.get_nowait()
                                status_messages.append(msg)
                        except queue.Empty:
                            pass
                        
                        # Final display of all messages
                        if status_messages:
                            display_text = "\n".join(status_messages[-20:])
                            status_placeholder.text(display_text)

                        result = future.result()
                        
                    # Defensive check: ensure result is a dict before accessing keys
                    if not isinstance(result, dict):
                        st.error(f"Unexpected result type: {type(result)}. Expected dict.")
                        st.stop()
                    
                    # Check for worker failures before showing success
                    worker_results = result.get("worker_results", [])
                    failed_workers = [w for w in worker_results if not w.get("success", True)]
                    
                    if failed_workers:
                        status_placeholder.warning(f"Analysis complete with {len(failed_workers)} worker failure(s)!")
                    else:
                        status_placeholder.success("Analysis complete! Reloading report...")
                    
                    # Save the result to a file so we can reload it
                    output_file = Path("bug_report.json")
                    with open(output_file, "w") as f:
                        json.dump(result, f, indent=2, default=str)
                        
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
        # Security: Validate path is within allowed directories (prevent path traversal)
        selected_path = Path(selected_file_path).resolve()
        allowed_dirs = [Path.cwd().resolve(), (Path.cwd() / "examples").resolve()]
        is_allowed = False
        try:
            is_allowed = any(selected_path.is_relative_to(d) for d in allowed_dirs)
        except (AttributeError, ValueError):
            # Fallback for Python versions < 3.9 or other path issues
            is_allowed = any(
                selected_path == d or d in selected_path.parents
                for d in allowed_dirs
            )
        if not is_allowed:
            st.error("Access denied: File must be within current or examples directory")
            data = None
        else:
            with open(selected_file_path, "r") as f:
                data = json.load(f)
    except Exception as e:
        st.error(f"Error loading {selected_file_path}: {e}")
else:
    # Fallback to try loading the just generated report if run just finished
    if Path("bug_report.json").exists():
        try:
            with open("bug_report.json", "r") as f:
                data = json.load(f)
            # Update selection to point to this new file if possible, or just use data
        except (json.JSONDecodeError, OSError) as e:
             # Could not auto-load bug_report.json, user will need to select manually
             import os
             if os.getenv("DEBUG"):
                 print(f"Warning: Could not auto-load bug_report.json: {e}")
             pass
            
    if not data:
        st.info(
            "No report file found or selected. Please run the bug finder script first to generate a 'bug_report.json'."
        )
        st.code("python examples/bug_finder_example.py <path_to_code>")
        st.stop()
    
if not data:
    st.info("No report file found or selected. Use the sidebar to run a new analysis.")
    st.stop()

# Display Task Info
review_mode = data.get("review_mode", "local")
st.markdown(f"**Task:** {data.get('task', 'Unknown Task')}")

if review_mode == "github_pr":
    pr_details = data.get("pr_details", {})
    st.markdown(f"**Mode:** 🔍 PR Review | **PR:** [#{pr_details.get('number', 'N/A')}]({pr_details.get('url', '#')})")

# Tabs - dynamic based on review mode (now includes Worker Errors tab)
if review_mode == "github_pr":
    tab1, tab_pr, tab_errors, tab2, tab3, tab4 = st.tabs(
        ["📝 Final Report", "📌 PR Context", "⚠️ Worker Errors", "👷 Worker Findings", "📊 Consensus Stats", "🔍 Raw Data"]
    )
else:
    tab1, tab_errors, tab2, tab3, tab4 = st.tabs(
        ["📝 Final Report", "⚠️ Worker Errors", "👷 Worker Findings", "📊 Consensus Stats", "🔍 Raw Data"]
    )
    tab_pr = None  # No PR tab in non-PR mode

with tab1:
    st.header("Consolidated Final Report")
    
    # Show infrastructure error summary if any were filtered
    infrastructure_errors = data.get("infrastructure_errors", [])
    if infrastructure_errors:
        with st.expander(f"⚠️ {len(infrastructure_errors)} Worker(s) Failed (Infrastructure Issues)", expanded=False):
            for err in infrastructure_errors:
                st.markdown(f"**{err.get('role')}**: `{err.get('error_type')}` - {err.get('description')}")
            st.caption("These errors are unrelated to the code being analyzed and were filtered from the synthesis.")
    
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

# Worker Errors tab - detailed view of all infrastructure errors
with tab_errors:
    st.header("Worker Infrastructure Errors")
    
    infrastructure_errors = data.get("infrastructure_errors", [])
    workers = data.get("worker_results", [])
    failed_workers = [w for w in workers if not w.get("success", True)]
    
    if not infrastructure_errors and not failed_workers:
        st.success("✅ All workers completed successfully!")
    else:
        # Summary metrics
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Total Workers", len(workers))
        with col2:
            st.metric("Successful", len(workers) - len(failed_workers))
        with col3:
            st.metric("Failed", len(failed_workers))
        
        st.divider()
        
        if infrastructure_errors:
            st.subheader("🔧 Infrastructure Errors (Filtered from Synthesis)")
            st.caption("These errors were identified as environment/tool issues and excluded from the final analysis.")
            
            for err in infrastructure_errors:
                with st.expander(f"❌ {err.get('role')} - {err.get('error_type')}", expanded=True):
                    st.markdown(f"**Error Type:** `{err.get('error_type')}`")
                    st.markdown(f"**Description:** {err.get('description')}")
                    
                    # Find the full error from worker_results
                    for w in workers:
                        if w.get("role") == err.get("role"):
                            full_error = w.get("error", "")
                            response = w.get("response", "")
                            if full_error:
                                st.subheader("Full Error Output")
                                st.code(full_error, language="text")
                            if response and response != full_error:
                                st.subheader("Response Content")
                                st.code(response, language="text")
                            break
        
        # Show any other failures not caught by filter
        filtered_roles = [e.get("role") for e in infrastructure_errors]
        other_failures = [w for w in failed_workers if w.get("role") not in filtered_roles]
        if other_failures:
            st.subheader("⚠️ Other Worker Failures")
            for w in other_failures:
                with st.expander(f"❌ {w.get('role')}", expanded=True):
                    st.error(w.get("error", "Unknown error"))
                    response = w.get("response", "")
                    if response:
                        st.subheader("Response Content")
                        st.code(response, language="text")
        
        # Filter model raw response for debugging
        filter_result = data.get("filter_result", {})
        if filter_result:
            with st.expander("🔍 Filter Model Response (Debug)"):
                st.json(filter_result)



# PR Context tab (only shown in PR mode)
if tab_pr is not None:
    with tab_pr:
        st.header("Pull Request Context")
        
        pr_details = data.get("pr_details", {})
        
        # PR Header
        col1, col2, col3 = st.columns([3, 1, 1])
        with col1:
            pr_title = pr_details.get("title", "Unknown")
            pr_num = pr_details.get("number", "N/A")
            st.subheader(f"#{pr_num} - {pr_title}")
            
            author = pr_details.get("author", {})
            author_name = author.get("login", "Unknown") if isinstance(author, dict) else str(author)
            st.caption(f"by {author_name}")
        with col2:
            state = pr_details.get("state", "UNKNOWN")
            st.metric("State", state)
        with col3:
            additions = pr_details.get("additions", 0)
            deletions = pr_details.get("deletions", 0)
            st.metric("Changes", f"+{additions} -{deletions}")
        
        # PR Description
        with st.expander("📄 Description", expanded=True):
            body = pr_details.get("body", "")
            if body and body.strip():
                st.markdown(body)
            else:
                st.caption("_No description provided_")
        
        # Changed Files
        st.subheader("📁 Changed Files")
        changed_files = data.get("changed_files", [])
        pr_files = pr_details.get("files", [])
        
        if pr_files:
            for f in pr_files[:30]:
                path = f.get("path", "Unknown")
                adds = f.get("additions", 0)
                dels = f.get("deletions", 0)
                st.code(f"{path} (+{adds} -{dels})", language=None)
            if len(pr_files) > 30:
                st.caption(f"... and {len(pr_files) - 30} more files")
        elif changed_files:
            for f in changed_files[:30]:
                st.code(f, language=None)
            if len(changed_files) > 30:
                st.caption(f"... and {len(changed_files) - 30} more files")
        else:
            st.info("No changed files information available.")
        
        # Existing Reviews
        st.subheader("💬 Existing Reviewer Comments")
        pr_reviews = data.get("pr_reviews", [])
        
        if pr_reviews:
            for i, review in enumerate(pr_reviews):
                author = review.get("author", {})
                author_name = author.get("login", "Unknown") if isinstance(author, dict) else str(author)
                state = review.get("state", "COMMENTED")
                body = review.get("body", "").strip()
                
                if body:
                    with st.expander(f"{author_name} - {state}"):
                        st.markdown(body)
                        
                        # Show inline comment location if available
                        path = review.get("path")
                        line = review.get("line")
                        if path and line:
                            st.caption(f"📍 File: {path}, Line: {line}")
        else:
            st.info("No reviewer comments found.")
        
        # PR Comments
        st.subheader("🗨️ PR Discussion")
        pr_comments = data.get("pr_comments", [])
        
        if pr_comments:
            for comment in pr_comments:
                author = comment.get("author", {})
                author_name = author.get("login", "Unknown") if isinstance(author, dict) else str(author)
                body = comment.get("body", "").strip()
                
                if body:
                    st.markdown(f"**{author_name}**: {body}")
                    st.divider()
        else:
            st.info("No PR discussion comments found.")

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
        
        # Build header with tool call count if available
        tool_calls = worker.get("tool_calls", [])
        header_suffix = f" ({len(tool_calls)} tool calls)" if tool_calls else ""

        with st.expander(f"{status_icon} {role}{header_suffix}"):
            if not success:
                st.error(f"Error: {worker.get('error', 'Unknown error')}")

            response = worker.get("response", "")
            if response:
                st.markdown(response)
            else:
                st.text("No response content.")

            st.divider()
            
            # Display tool calls if available
            if tool_calls:
                st.subheader("🔧 Tool Calls")
                for j, tool_call in enumerate(tool_calls):
                    tool_name = tool_call.get("tool", "unknown")
                    status = tool_call.get("status", "")
                    title = tool_call.get("title", "")
                    
                    tool_header = f"{tool_name}"
                    if title:
                        tool_header += f": {title}"
                    if status:
                        status_emoji = "✅" if status == "completed" else "⏳"
                        tool_header += f" {status_emoji}"
                    
                    # Use st.text to prevent XSS from LLM-generated content
                    st.text(f"🔧 {tool_header}")
                    
                    # Show input
                    tool_input = tool_call.get("input", {})
                    if tool_input:
                        if isinstance(tool_input, dict):
                            # Pretty format common inputs
                            if "command" in tool_input:
                                st.code(tool_input.get("command", ""), language="bash")
                            else:
                                st.json(tool_input)
                        else:
                            st.code(str(tool_input))
                    
                    # Show output (collapsed for long outputs)
                    tool_output = tool_call.get("output", "")
                    if tool_output:
                        output_str = str(tool_output)
                        if len(output_str) > 500:
                            with st.expander("Output (click to expand)"):
                                st.code(output_str, language="text")
                        else:
                            st.code(output_str, language="text")
                    
                    if j < len(tool_calls) - 1:
                        st.markdown("---")
                
                st.divider()
            
            # Display step information if available
            steps = worker.get("steps", [])
            if steps:
                st.subheader("📊 Execution Steps")
                start_steps = [s for s in steps if s.get("type") == "start"]
                finish_steps = [s for s in steps if s.get("type") == "finish"]
                
                col1, col2 = st.columns(2)
                with col1:
                    st.metric("Steps", len(start_steps))
                with col2:
                    total_tokens = sum(
                        s.get("tokens", {}).get("input", 0) + s.get("tokens", {}).get("output", 0)
                        for s in finish_steps
                    )
                    st.metric("Total Tokens", total_tokens)
                
                # Show token breakdown for each step
                for k, finish in enumerate(finish_steps):
                    tokens = finish.get("tokens", {})
                    reason = finish.get("reason", "")
                    input_tokens = tokens.get("input", 0)
                    output_tokens = tokens.get("output", 0)
                    st.caption(f"Step {k+1}: {input_tokens} in / {output_tokens} out ({reason})")
                
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
