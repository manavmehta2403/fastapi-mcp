import os
import subprocess
import sys


def test_cli_inspect():
    env = os.environ.copy()
    env["PYTHONPATH"] = r"c:\Users\manav\Downloads\fastapi-mcp"

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
        cwd=r"c:\Users\manav\Downloads\fastapi-mcp",
    )
    print("CLI inspect output:")
    print(result.stdout)
    assert "get_product" in result.stdout
    assert "create_product" in result.stdout
    print("test_cli_inspect passed successfully!")


if __name__ == "__main__":
    test_cli_inspect()
