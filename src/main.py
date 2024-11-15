import signal
import sys

from program import Program
from utils.logger import logger

program = Program()


def signal_handler(signum, frame):
    logger.log("PROGRAM", "Exiting Gracefully.")
    program.stop()
    sys.exit(0)


signal.signal(signal.SIGINT, signal_handler)
signal.signal(signal.SIGTERM, signal_handler)


def main():
    """Run the main application"""
    try:
        program.start()
    except Exception as e:
        logger.exception(f"Program error: {e}")
    finally:
        logger.log("PROGRAM", "Shutdown requested. Exiting gracefully...")
        program.stop()
        program.join()


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        logger.exception(f"Fatal error: {e}")
    finally:
        logger.log("PROGRAM", "Exiting.")
        sys.exit(0)
