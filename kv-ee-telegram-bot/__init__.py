import os
import sys
from pathlib import Path


def setup_environment():
    """Setup environment and working directory"""
    # Set working directory to script location
    script_dir = Path(__file__).parent.absolute()
    os.chdir(script_dir)

    # Add current directory to Python path
    sys.path.insert(0, str(script_dir))

    # Load environment variables
    from dotenv import load_dotenv

    load_dotenv()

    # Set up logging
    from utils import setup_logging

    setup_logging()

    logger = logging.getLogger(__name__)
    logger.info(f"Working directory: {script_dir}")
    logger.info(f"Python path: {sys.path}")

    return script_dir


# Setup environment when module is imported
setup_environment()
