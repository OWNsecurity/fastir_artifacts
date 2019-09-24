import logging


logger = logging.getLogger('fastir')
logger.setLevel(logging.DEBUG)

PROGRESS = 25
logging.addLevelName(PROGRESS, 'PROGRESS')
