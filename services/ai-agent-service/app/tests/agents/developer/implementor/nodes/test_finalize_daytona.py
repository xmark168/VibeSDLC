"""
Unit tests for Daytona sandbox cleanup in finalize node.

Tests the _handle_sandbox_cleanup() function to ensure proper
sandbox cleanup and error handling.
"""

from unittest.mock import MagicMock, Mock, patch

import pytest

from agents.developer.implementor.nodes.finalize import _handle_sandbox_cleanup
from agents.developer.implementor.state import ImplementorState, SandboxDeletion


# ============================================================================
# Test _handle_sandbox_cleanup()
# ============================================================================

class TestHandleSandboxCleanup:
    """Test Daytona sandbox cleanup logic."""
    
    def test_cleanup_sandbox_mode_disabled(self):
        """Test that cleanup is skipped when sandbox_mode=False."""
        # Setup
        state = ImplementorState(
            task_id="TEST-001",
            feature_branch="feature/test",
            base_branch="main",
            sandbox_mode=False,
            sandbox_id="",
            status="completed"
        )
        
        # Execute
        _handle_sandbox_cleanup(state)
        
        # Verify
        assert state.sandbox_deletion is not None
        assert state.sandbox_deletion.skipped is True
        assert "Not using Daytona sandbox mode" in state.sandbox_deletion.skip_reason
        assert state.sandbox_deletion.success is False
    
    def test_cleanup_no_sandbox_id(self):
        """Test that cleanup is skipped when sandbox_id is empty."""
        # Setup
        state = ImplementorState(
            task_id="TEST-001",
            feature_branch="feature/test",
            base_branch="main",
            sandbox_mode=True,
            sandbox_id="",  # Empty sandbox ID
            status="completed"
        )
        
        # Execute
        _handle_sandbox_cleanup(state)
        
        # Verify
        assert state.sandbox_deletion is not None
        assert state.sandbox_deletion.skipped is True
        assert "No sandbox ID provided" in state.sandbox_deletion.skip_reason
    
    def test_cleanup_workflow_not_completed(self):
        """Test that cleanup is skipped when workflow status is not completed."""
        # Setup
        state = ImplementorState(
            task_id="TEST-001",
            feature_branch="feature/test",
            base_branch="main",
            sandbox_mode=True,
            sandbox_id="test_sandbox_123",
            status="error"  # Not completed
        )
        
        # Execute
        _handle_sandbox_cleanup(state)
        
        # Verify
        assert state.sandbox_deletion is not None
        assert state.sandbox_deletion.skipped is True
        assert "Workflow not completed successfully" in state.sandbox_deletion.skip_reason
        assert "error" in state.sandbox_deletion.skip_reason
    
    @patch('agents.developer.implementor.nodes.finalize.get_sandbox_manager')
    @patch('agents.developer.implementor.nodes.finalize.DaytonaConfig')
    def test_cleanup_successful(self, mock_config_class, mock_get_manager):
        """Test successful sandbox cleanup."""
        # Setup
        mock_config = MagicMock()
        mock_config_class.from_env.return_value = mock_config
        
        mock_manager = MagicMock()
        mock_manager.cleanup_sandbox.return_value = {
            "status": "deleted",
            "sandbox_id": "test_sandbox_123"
        }
        mock_get_manager.return_value = mock_manager
        
        state = ImplementorState(
            task_id="TEST-001",
            feature_branch="feature/test",
            base_branch="main",
            sandbox_mode=True,
            sandbox_id="test_sandbox_123",
            status="completed"
        )
        
        # Execute
        _handle_sandbox_cleanup(state)
        
        # Verify
        assert state.sandbox_deletion is not None
        assert state.sandbox_deletion.success is True
        assert state.sandbox_deletion.sandbox_id == "test_sandbox_123"
        assert "deleted successfully" in state.sandbox_deletion.message
        assert state.sandbox_deletion.skipped is False
        
        # Verify cleanup was called
        mock_manager.cleanup_sandbox.assert_called_once()
    
    @patch('agents.developer.implementor.nodes.finalize.get_sandbox_manager')
    @patch('agents.developer.implementor.nodes.finalize.DaytonaConfig')
    def test_cleanup_failed(self, mock_config_class, mock_get_manager):
        """Test cleanup failure handling."""
        # Setup
        mock_config = MagicMock()
        mock_config_class.from_env.return_value = mock_config
        
        mock_manager = MagicMock()
        mock_manager.cleanup_sandbox.side_effect = Exception("Cleanup failed")
        mock_get_manager.return_value = mock_manager
        
        state = ImplementorState(
            task_id="TEST-001",
            feature_branch="feature/test",
            base_branch="main",
            sandbox_mode=True,
            sandbox_id="test_sandbox_123",
            status="completed"
        )
        
        # Execute
        _handle_sandbox_cleanup(state)
        
        # Verify
        assert state.sandbox_deletion is not None
        assert state.sandbox_deletion.success is False
        assert "Exception during sandbox cleanup" in state.sandbox_deletion.message
        assert "Cleanup failed" in state.sandbox_deletion.error
        assert state.sandbox_deletion.skipped is False
    
    @patch('agents.developer.implementor.nodes.finalize.DaytonaConfig')
    def test_cleanup_config_not_found(self, mock_config_class):
        """Test cleanup when Daytona config is not found."""
        # Setup
        mock_config_class.from_env.return_value = None
        
        state = ImplementorState(
            task_id="TEST-001",
            feature_branch="feature/test",
            base_branch="main",
            sandbox_mode=True,
            sandbox_id="test_sandbox_123",
            status="completed"
        )
        
        # Execute
        _handle_sandbox_cleanup(state)
        
        # Verify
        assert state.sandbox_deletion is not None
        assert state.sandbox_deletion.success is False
        assert "Daytona configuration not found" in state.sandbox_deletion.message or \
               "Exception during sandbox cleanup" in state.sandbox_deletion.message
    
    @patch('agents.developer.implementor.nodes.finalize.get_sandbox_manager')
    @patch('agents.developer.implementor.nodes.finalize.DaytonaConfig')
    def test_cleanup_with_pr_ready_status(self, mock_config_class, mock_get_manager):
        """Test cleanup works with pr_ready status."""
        # Setup
        mock_config = MagicMock()
        mock_config_class.from_env.return_value = mock_config
        
        mock_manager = MagicMock()
        mock_manager.cleanup_sandbox.return_value = {
            "status": "deleted",
            "sandbox_id": "test_sandbox_123"
        }
        mock_get_manager.return_value = mock_manager
        
        state = ImplementorState(
            task_id="TEST-001",
            feature_branch="feature/test",
            base_branch="main",
            sandbox_mode=True,
            sandbox_id="test_sandbox_123",
            status="pr_ready"  # Alternative success status
        )
        
        # Execute
        _handle_sandbox_cleanup(state)
        
        # Verify
        assert state.sandbox_deletion is not None
        assert state.sandbox_deletion.success is True
        mock_manager.cleanup_sandbox.assert_called_once()
    
    @patch('agents.developer.implementor.nodes.finalize.get_sandbox_manager')
    @patch('agents.developer.implementor.nodes.finalize.DaytonaConfig')
    def test_cleanup_with_finalized_status(self, mock_config_class, mock_get_manager):
        """Test cleanup works with finalized status."""
        # Setup
        mock_config = MagicMock()
        mock_config_class.from_env.return_value = mock_config
        
        mock_manager = MagicMock()
        mock_manager.cleanup_sandbox.return_value = {
            "status": "deleted",
            "sandbox_id": "test_sandbox_123"
        }
        mock_get_manager.return_value = mock_manager
        
        state = ImplementorState(
            task_id="TEST-001",
            feature_branch="feature/test",
            base_branch="main",
            sandbox_mode=True,
            sandbox_id="test_sandbox_123",
            status="finalized"  # Alternative success status
        )
        
        # Execute
        _handle_sandbox_cleanup(state)
        
        # Verify
        assert state.sandbox_deletion is not None
        assert state.sandbox_deletion.success is True
        mock_manager.cleanup_sandbox.assert_called_once()
    
    @patch('agents.developer.implementor.nodes.finalize.get_sandbox_manager')
    @patch('agents.developer.implementor.nodes.finalize.DaytonaConfig')
    def test_cleanup_partial_success(self, mock_config_class, mock_get_manager):
        """Test cleanup when sandbox returns non-deleted status."""
        # Setup
        mock_config = MagicMock()
        mock_config_class.from_env.return_value = mock_config
        
        mock_manager = MagicMock()
        mock_manager.cleanup_sandbox.return_value = {
            "status": "pending",  # Not fully deleted
            "sandbox_id": "test_sandbox_123"
        }
        mock_get_manager.return_value = mock_manager
        
        state = ImplementorState(
            task_id="TEST-001",
            feature_branch="feature/test",
            base_branch="main",
            sandbox_mode=True,
            sandbox_id="test_sandbox_123",
            status="completed"
        )
        
        # Execute
        _handle_sandbox_cleanup(state)
        
        # Verify
        assert state.sandbox_deletion is not None
        assert state.sandbox_deletion.success is False  # Not fully successful
        assert "cleanup status: pending" in state.sandbox_deletion.message

