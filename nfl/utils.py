import json
import logging.handlers
import os
import datetime
import shutil
import time
from datetime import datetime

from nfl.constants import APP_LOG_DIRECTORY


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


def create_backup(file):
    """
    Creates a backup of the file in the backups directory.
    :param file: File to create backup of
    :return: str, name of the backup file
    """
    if not os.path.exists(file):
        logging.info(f"create_backup() file {file} does not exist.")
        return

    backup_file = f"{os.path.basename(file)}_{datetime.now().strftime('%Y%m%d%H%M%S')}_backup"

    try:
        shutil.copy2(file, backup_file)
        dest = shutil.move(backup_file, f"../backups/{backup_file}")
        logging.info(f"create_backup() Backup created successfully at {os.path.abspath(dest)}")
        return backup_file
    except Exception as e:
        logging.info(f"create_backup() Failed to create backup: {e}")


def delete_file(file):
    if not os.path.exists(file):
        logging.info(f"delete_file() File {file} does not exist.")
        return

    try:
        os.remove(file)
        logging.info(f"delete_file() File {file} deleted successfully.")
    except Exception as e:
        logging.info(f"delete_file() Failed to delete file: {e}")


def rename_keys_in_json(json_file_path):
    """
    Renames the keys in a json file that start with "Unnamed" to the last part of the key. PFR exports have unnamed columns that are not useful.
    :param json_file_path: Path to the json file
    """
    with open(json_file_path, 'r') as file:
        data = json.load(file)

    def rename_keys(obj):
        if isinstance(obj, dict):
            new_obj = {}
            for key, value in obj.items():
                new_key = key.split('_')[-1] if key.startswith("Unnamed") else key
                new_obj[new_key] = rename_keys(value)
            return new_obj
        elif isinstance(obj, list):
            return [rename_keys(item) for item in obj]
        else:
            return obj
    renamed_data = rename_keys(data)

    with open(json_file_path, 'w') as file:
        json.dump(renamed_data, file, indent=4)


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


if __name__ == '__main__':
    rename_keys_in_json("../data/2023_gamelogs_leagueid_1075600889420845056.json")