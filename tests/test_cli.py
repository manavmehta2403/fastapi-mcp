import os
import subprocess
import sys
import pytest


def test_load_app_chains_module_import_error():
    from fastapi_mcp.cli import load_app

    missing_module = "__fastapi_mcp_test_missing_import__"
    with pytest.raises(RuntimeError) as exc_info:
        load_app(f"{missing_module}:app")

    assert isinstance(exc_info.value.__cause__, ModuleNotFoundError)
    assert exc_info.value.__cause__.name == missing_module


def test_cli_inspect():
    project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    env = os.environ.copy()
    existing_pp = env.get("PYTHONPATH", "")
    env["PYTHONPATH"] = f"{project_root}{os.pathsep}{existing_pp}" if existing_pp else project_root

    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "fastapi_mcp.cli",
            "inspect",
            "tests.test_auto_scan:create_test_app",
        ],
        capture_output=True,
        text=True,
        check=True,
        env=env,
        cwd=project_root,
    )
    print("CLI inspect output:")
    print(result.stdout)
    assert "get_product" in result.stdout
    assert "create_product" in result.stdout
    print("test_cli_inspect passed successfully!")


if __name__ == "__main__":
    test_cli_inspect()
