import logging.handlers
import os
import datetime

from constants import APP_LOG_DIRECTORY


def is_file_older_than_one_week(file_path):
    current_time = datetime.datetime.now()
    creation_time = datetime.datetime.fromtimestamp(os.path.getctime(file_path))
    file_age_days = (current_time - creation_time).days
    return file_age_days > 7


def validate_file(file_name):
    if os.path.exists(file_name):
        validated = True
    else:
        validated = False
    return validated


def logging_steup():
    app_log_directory = APP_LOG_DIRECTORY
    if not os.path.exists(app_log_directory):
        os.makedirs(app_log_directory)
    log_file = f'{APP_LOG_DIRECTORY}/tloojtools.log'
    should_roll_over = os.path.isfile(log_file)
    handler = logging.handlers.RotatingFileHandler(log_file, mode='w', backupCount=5, delay=True)
    if should_roll_over:
        handler.doRollover()
    logging.basicConfig(filename=log_file,
                        filemode='a',
                        format='[%(asctime)s] p%(process)s {%(pathname)s:%(lineno)d}\n%(levelname)s - %(message)s',
                        level=logging.DEBUG)
    logging.info(f'Application started')
