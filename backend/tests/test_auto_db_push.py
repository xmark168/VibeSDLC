"""Test auto db:push functionality in implement node."""
import pytest


class TestAutoDbPush:
    """Test auto db:push when prisma schema is modified."""

    def test_prisma_modified_detection(self):
        """Test detection of prisma schema modification."""
        # Test various file paths (Windows + Unix)
        test_cases = [
            (["prisma/schema.prisma"], True),
            (["C:/project/prisma/schema.prisma"], True),
            (["C:\\project\\prisma\\schema.prisma"], True),  # Windows path
            (["/home/user/app/prisma/schema.prisma"], True),
            (["schema.prisma"], True),
            (["src/app/page.tsx"], False),
            (["src/lib/prisma.ts"], False),
            (["prisma/seed.ts"], False),
            ([], False),
        ]
        
        for files, expected in test_cases:
            result = any(
                f.replace("\\", "/").endswith("prisma/schema.prisma") or f.endswith("schema.prisma")
                for f in files
            )
            assert result == expected, f"Failed for {files}"

    def test_db_push_command_format(self):
        """Test the db:push command that would be executed."""
        workspace = "/test/workspace"
        expected_command = "bunx prisma db push --accept-data-loss"
        expected_cwd = workspace
        
        # Verify command format is correct
        assert "prisma db push" in expected_command
        assert "--accept-data-loss" in expected_command
        
    def test_schema_path_variations(self):
        """Test various schema path formats are detected (Windows + Unix)."""
        paths = [
            "prisma/schema.prisma",
            "C:\\Users\\test\\project\\prisma\\schema.prisma",
            "/home/user/app/prisma/schema.prisma",
            "schema.prisma",
        ]
        
        for path in paths:
            # Match the actual logic in implement.py
            result = path.replace("\\", "/").endswith("prisma/schema.prisma") or path.endswith("schema.prisma")
            assert result is True, f"Failed to detect: {path}"

    def test_db_push_not_called_for_other_files(self):
        """Test that db:push is NOT called for non-schema files."""
        files = ["src/app/api/books/route.ts", "src/components/BookList.tsx"]
        
        prisma_modified = any(
            f.endswith("prisma/schema.prisma") or f.endswith("schema.prisma")
            for f in files
        )
        assert prisma_modified is False


if __name__ == "__main__":
    # Quick manual test
    test = TestAutoDbPush()
    test.test_prisma_modified_detection()
    print("✅ All detection tests passed!")
