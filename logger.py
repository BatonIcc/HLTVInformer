import logging

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(name)s - %(message)s",
    filename="logs/logs.log",
    filemode="a"
)
logger = logging.getLogger(__name__)