"""Integration tests for parallel implementation."""
import asyncio
import time
import pytest
from unittest.mock import AsyncMock, MagicMock

from app.agents.developer_v2.src.nodes.parallel_utils import (
    get_layer_priority,
    group_steps_by_layer,
    detect_file_conflicts,
    should_use_parallel,
    run_layer_parallel,
    merge_parallel_results,
    MAX_CONCURRENT,
)


class TestLayerPriority:
    """Test get_layer_priority function."""
    
    def test_schema_is_first(self):
        assert get_layer_priority("prisma/schema.prisma") == 1
    
    def test_seed_is_second(self):
        assert get_layer_priority("prisma/seed.ts") == 2
    
    def test_types_is_third(self):
        assert get_layer_priority("src/types/index.ts") == 3
    
    def test_lib_is_fourth(self):
        assert get_layer_priority("src/lib/prisma.ts") == 4
    
    def test_api_routes_is_fifth(self):
        assert get_layer_priority("src/app/api/books/route.ts") == 5
    
    def test_actions_is_sixth(self):
        assert get_layer_priority("src/app/actions/book-actions.ts") == 6
    
    def test_cards_before_sections(self):
        card = get_layer_priority("src/components/BookCard.tsx")
        section = get_layer_priority("src/components/BooksSection.tsx")
        assert card < section  # 7.1 < 7.2
    
    def test_page_is_last(self):
        assert get_layer_priority("src/app/page.tsx") == 8
    
    def test_priority_order(self):
        """Full order: schema < seed < types < lib < api < actions < cards < sections < page"""
        files = [
            "src/app/page.tsx",
            "src/components/BooksSection.tsx",
            "src/components/BookCard.tsx",
            "src/app/actions/book.ts",
            "src/app/api/books/route.ts",
            "src/lib/prisma.ts",
            "src/types/index.ts",
            "prisma/seed.ts",
            "prisma/schema.prisma",
        ]
        
        sorted_files = sorted(files, key=get_layer_priority)
        
        assert sorted_files[0] == "prisma/schema.prisma"
        assert sorted_files[1] == "prisma/seed.ts"
        assert sorted_files[-1] == "src/app/page.tsx"


class TestGroupStepsByLayer:
    """Test group_steps_by_layer function."""
    
    def test_groups_correctly(self):
        steps = [
            {"file_path": "prisma/schema.prisma"},
            {"file_path": "src/app/api/books/route.ts"},
            {"file_path": "src/app/api/categories/route.ts"},
            {"file_path": "src/components/BookCard.tsx"},
            {"file_path": "src/app/page.tsx"},
        ]
        
        layers = group_steps_by_layer(steps)
        
        # Should have 4 layers: 1, 5, 7.1, 8
        assert len(layers) == 4
        assert len(layers[1]) == 1   # schema
        assert len(layers[5]) == 2   # 2 api routes
        assert len(layers[7.1]) == 1 # 1 card
        assert len(layers[8]) == 1   # page
    
    def test_empty_steps(self):
        layers = group_steps_by_layer([])
        assert layers == {}


class TestDetectFileConflicts:
    """Test detect_file_conflicts function."""
    
    def test_no_conflicts(self):
        steps = [
            {"file_path": "a.ts"},
            {"file_path": "b.ts"},
            {"file_path": "c.ts"},
        ]
        conflicts = detect_file_conflicts(steps)
        assert conflicts == []
    
    def test_detects_conflict(self):
        steps = [
            {"file_path": "a.ts"},
            {"file_path": "b.ts"},
            {"file_path": "a.ts"},  # Duplicate
        ]
        conflicts = detect_file_conflicts(steps)
        assert "a.ts" in conflicts
    
    def test_multiple_conflicts(self):
        steps = [
            {"file_path": "a.ts"},
            {"file_path": "a.ts"},
            {"file_path": "b.ts"},
            {"file_path": "b.ts"},
        ]
        conflicts = detect_file_conflicts(steps)
        assert len(conflicts) == 2


class TestShouldUseParallel:
    """Test should_use_parallel function."""
    
    def test_few_steps_returns_false(self):
        steps = [{"file_path": "a.ts"}, {"file_path": "b.ts"}]
        assert should_use_parallel(steps) is False
    
    def test_many_steps_same_layer_returns_true(self):
        steps = [
            {"file_path": "src/app/api/a/route.ts"},
            {"file_path": "src/app/api/b/route.ts"},
            {"file_path": "src/app/api/c/route.ts"},
            {"file_path": "src/app/api/d/route.ts"},
        ]
        assert should_use_parallel(steps) is True
    
    def test_many_steps_different_layers_returns_false(self):
        steps = [
            {"file_path": "prisma/schema.prisma"},
            {"file_path": "prisma/seed.ts"},
            {"file_path": "src/types/index.ts"},
            {"file_path": "src/app/page.tsx"},
        ]
        # All different layers, no parallelism benefit
        assert should_use_parallel(steps) is False


class TestRunLayerParallel:
    """Integration tests for run_layer_parallel function."""
    
    @pytest.mark.asyncio
    async def test_runs_all_steps(self):
        """All steps in layer are executed."""
        executed = []
        
        async def mock_impl(step, state):
            executed.append(step["file_path"])
            return {"success": True, "file_path": step["file_path"]}
        
        steps = [
            {"file_path": "a.ts"},
            {"file_path": "b.ts"},
            {"file_path": "c.ts"},
        ]
        
        results = await run_layer_parallel(steps, mock_impl, {})
        
        assert len(executed) == 3
        assert set(executed) == {"a.ts", "b.ts", "c.ts"}
    
    @pytest.mark.asyncio
    async def test_parallel_speedup(self):
        """Parallel execution is faster than sequential."""
        async def mock_impl(step, state):
            await asyncio.sleep(0.2)  # 200ms each
            return {"success": True}
        
        steps = [{"file_path": f"{i}.ts"} for i in range(3)]
        
        start = time.time()
        await run_layer_parallel(steps, mock_impl, {}, max_concurrent=3)
        elapsed = time.time() - start
        
        # Should take ~200ms (parallel), not 600ms (sequential)
        assert elapsed < 0.5
    
    @pytest.mark.asyncio
    async def test_semaphore_limits_concurrent(self):
        """Semaphore limits concurrent executions."""
        concurrent = 0
        max_concurrent_seen = 0
        
        async def mock_impl(step, state):
            nonlocal concurrent, max_concurrent_seen
            concurrent += 1
            max_concurrent_seen = max(max_concurrent_seen, concurrent)
            await asyncio.sleep(0.1)
            concurrent -= 1
            return {"success": True}
        
        # 6 steps with max_concurrent=2
        steps = [{"file_path": f"{i}.ts"} for i in range(6)]
        await run_layer_parallel(steps, mock_impl, {}, max_concurrent=2)
        
        assert max_concurrent_seen <= 2
    
    @pytest.mark.asyncio
    async def test_conflict_runs_sequential(self):
        """File conflicts cause sequential execution."""
        execution_times = []
        
        async def mock_impl(step, state):
            execution_times.append(time.time())
            await asyncio.sleep(0.1)
            return {"success": True, "file_path": step["file_path"]}
        
        # Same file twice = conflict
        steps = [
            {"file_path": "same.ts"},
            {"file_path": "same.ts"},
        ]
        
        await run_layer_parallel(steps, mock_impl, {})
        
        # Sequential means second started after first finished
        if len(execution_times) == 2:
            gap = execution_times[1] - execution_times[0]
            assert gap >= 0.09  # At least 100ms apart
    
    @pytest.mark.asyncio
    async def test_handles_exceptions(self):
        """Exceptions are caught and returned as errors."""
        async def mock_impl(step, state):
            if step["file_path"] == "fail.ts":
                raise ValueError("Test error")
            return {"success": True, "file_path": step["file_path"]}
        
        steps = [
            {"file_path": "ok.ts"},
            {"file_path": "fail.ts"},
            {"file_path": "also_ok.ts"},
        ]
        
        results = await run_layer_parallel(steps, mock_impl, {})
        
        # All 3 should have results (including error)
        assert len(results) == 3
        
        # One should have error
        errors = [r for r in results if "error" in r]
        assert len(errors) == 1


class TestMergeParallelResults:
    """Test merge_parallel_results function."""
    
    def test_merges_modified_files(self):
        results = [
            {"success": True, "files_modified": ["a.ts", "b.ts"]},
            {"success": True, "files_modified": ["c.ts"]},
        ]
        
        merged = merge_parallel_results(results, {"files_modified": []})
        
        assert set(merged["files_modified"]) == {"a.ts", "b.ts", "c.ts"}
    
    def test_collects_errors(self):
        results = [
            {"success": True},
            {"error": "Failed 1"},
            {"error": "Failed 2"},
        ]
        
        merged = merge_parallel_results(results, {})
        
        assert "parallel_errors" in merged
        assert len(merged["parallel_errors"]) == 2


class TestLayerExecutionOrder:
    """Test that layers execute in correct order."""
    
    @pytest.mark.asyncio
    async def test_layers_in_order(self):
        """Schema layer completes before API layer starts."""
        layer_completion = {}
        
        async def mock_impl(step, state):
            layer = get_layer_priority(step["file_path"])
            await asyncio.sleep(0.05)
            layer_completion[step["file_path"]] = time.time()
            return {"success": True, "file_path": step["file_path"], "modified_files": [step["file_path"]]}
        
        steps = [
            {"file_path": "src/app/page.tsx"},       # Layer 8
            {"file_path": "prisma/schema.prisma"},   # Layer 1
            {"file_path": "src/app/api/a/route.ts"}, # Layer 5
        ]
        
        # Group and execute by layer
        layers = group_steps_by_layer(steps)
        
        for layer_num in sorted(layers.keys()):
            layer_steps = layers[layer_num]
            await run_layer_parallel(layer_steps, mock_impl, {})
        
        # Verify order
        schema_time = layer_completion["prisma/schema.prisma"]
        api_time = layer_completion["src/app/api/a/route.ts"]
        page_time = layer_completion["src/app/page.tsx"]
        
        assert schema_time < api_time < page_time


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
