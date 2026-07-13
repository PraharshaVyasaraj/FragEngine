import os
import sys

def test_environment_ci():
    """Verify basic python environment and file hierarchy inside CI runner"""
    assert sys.version_info >= (3, 10)
    assert os.path.exists("server.py")
    assert os.path.exists("parser.py")
    assert os.path.exists("requirements.txt")
