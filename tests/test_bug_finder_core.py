
import pytest
import asyncio
from unittest.mock import patch, MagicMock, AsyncMock
from pathlib import Path
from bug_finder.cli import find_bugs_with_consensus


def test_find_bugs_with_consensus_flow(tmp_path):
    async def run_async_test():
        # Setup a dummy target
        target_file = tmp_path / "test_code.py"
        target_file.write_text("print('hello')")
        
        # Mock dependencies
        with patch("bug_finder.cli.ExternalCLIConsensusAgent") as MockWorkerAgent, \
             patch("bug_finder.cli.LiteLLMAgent") as MockOrchestratorAgent, \
             patch("bug_finder.cli.ConsensusManager") as MockConsensusManager:
            
            # Setup Worker Agent Mock
            mock_worker_instance = MagicMock()
            mock_worker_instance.role = "MockWorker"
            MockWorkerAgent.return_value = mock_worker_instance
            
            # Setup Orchestrator Agent Mock
            mock_orchestrator_instance = MagicMock()
            mock_orchestrator_instance.role = "MockOrchestrator"
            mock_orchestrator_result = {"response": "Final Report"}
            
            # execute is synchronous in LiteLLMAgent usage
            mock_orchestrator_instance.execute.return_value = mock_orchestrator_result
            MockOrchestratorAgent.return_value = mock_orchestrator_instance
            
            # Setup Consensus Manager Mock
            mock_manager_instance = MagicMock()
            # execute_collaborative_task return value
            mock_worker_results = {
                "agent_results": [
                    {"role": "MockWorker", "response": "Bug found", "success": True}
                ],
                "consensus": {"converged": True},
                "final_decision": "Approved"
            }
            mock_manager_instance.execute_collaborative_task.return_value = mock_worker_results
            MockConsensusManager.return_value = mock_manager_instance
            
            # Mock get_available_integrations to avoid external checks
            with patch("bug_finder.cli.get_available_integrations") as mock_get_integrations:
                mock_get_integrations.return_value = {
                    "mock_cli": {"ready": True},
                    "gemini": {"ready": True}
                }
                
                result = await find_bugs_with_consensus(
                    target_path=str(target_file),
                    # pass specific configs 
                    worker_configs=[{"type": "mock_cli", "role": "TestWorker", "mode": "cli"}],
                    verbose=False
                )
                
            # Verify Interactions
            
            # 1. Check if agents were initialized
            MockWorkerAgent.assert_called()
            MockOrchestratorAgent.assert_called()
            
            # 2. Check if consensus manager was initialized and executed
            MockConsensusManager.assert_called()
            mock_manager_instance.execute_collaborative_task.assert_called_once()
            
            # 3. Check if orchestrator was executed
            # Note: execute is called twice - once for filter agent, once for orchestrator
            assert mock_orchestrator_instance.execute.call_count == 2
            
            # 4. Check result structure
            assert result["worker_results"] == mock_worker_results["agent_results"]
            assert result["final_report"] == "Final Report"
            assert result["final_decision"] == "Approved"

    asyncio.run(run_async_test())
