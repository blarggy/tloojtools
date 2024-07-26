import unittest
from unittest.mock import patch, mock_open
from nfl.utils import create_backup
import json
from nfl.utils import rename_keys_in_json


class TestRenameKeysInJson(unittest.TestCase):

    @patch("builtins.open", new_callable=mock_open, read_data='{"Unnamed_0": "value", "key_1": "value"}')
    @patch("json.load")
    @patch("json.dump")
    def test_rename_keys_in_json_renames_unnamed_keys(self, mock_json_dump, mock_json_load, mock_open):
        mock_json_load.return_value = json.loads(mock_open().read())
        rename_keys_in_json('dummy_path')
        mock_json_dump.assert_called_once_with({"0": "value", "key_1": "value"}, mock_open(), indent=4)

    @patch("builtins.open", new_callable=mock_open, read_data='{"key_1": "value"}')
    @patch("json.load")
    @patch("json.dump")
    def test_rename_keys_in_json_does_not_rename_non_unnamed_keys(self, mock_json_dump, mock_json_load, mock_open):
        mock_json_load.return_value = json.loads(mock_open().read())
        rename_keys_in_json('dummy_path')
        mock_json_dump.assert_called_once_with({"key_1": "value"}, mock_open(), indent=4)

    @patch("builtins.open", new_callable=mock_open, read_data='[{"Unnamed_0": "value"}, {"key_1": "value"}]')
    @patch("json.load")
    @patch("json.dump")
    def test_rename_keys_in_json_handles_list_of_dicts(self, mock_json_dump, mock_json_load, mock_open):
        mock_json_load.return_value = json.loads(mock_open().read())
        rename_keys_in_json('dummy_path')
        mock_json_dump.assert_called_once_with([{"0": "value"}, {"key_1": "value"}], mock_open(), indent=4)

    @patch("builtins.open", new_callable=mock_open, read_data='{"key_1": {"Unnamed_0": "value"}}')
    @patch("json.load")
    @patch("json.dump")
    def test_rename_keys_in_json_handles_nested_dicts(self, mock_json_dump, mock_json_load, mock_open):
        mock_json_load.return_value = json.loads(mock_open().read())
        rename_keys_in_json('dummy_path')
        mock_json_dump.assert_called_once_with({"key_1": {"0": "value"}}, mock_open(), indent=4)


class TestCreateBackup(unittest.TestCase):

    @patch("os.path.exists", return_value=False)
    @patch("logging.info")
    def test_create_backup_logs_and_returns_none_if_file_does_not_exist(self, mock_logging_info, mock_path_exists):
        result = create_backup("non_existent_file.txt")
        mock_logging_info.assert_called_once_with("create_backup() file non_existent_file.txt does not exist.")
        self.assertIsNone(result)

    @patch("os.path.exists", return_value=True)
    @patch("shutil.copy2")
    @patch("shutil.move")
    def test_create_backup_creates_backup_successfully(self, mock_shutil_move, mock_shutil_copy2, mock_path_exists):
        mock_shutil_move.return_value = "../backups/file_20230101010101_backup"
        with patch("nfl.utils.datetime") as mock_datetime:
            mock_datetime.now.return_value.strftime.return_value = "20230101010101"
            result = create_backup("file.txt")
            mock_shutil_copy2.assert_called_once_with("file.txt", "file.txt_20230101010101_backup")
            mock_shutil_move.assert_called_once_with("file.txt_20230101010101_backup", "../backups/file.txt_20230101010101_backup")
            self.assertEqual(result, "file.txt_20230101010101_backup")

    @patch("os.path.exists", return_value=True)
    @patch("shutil.copy2", side_effect=Exception("Copy failed"))
    @patch("logging.info")
    def test_create_backup_logs_error_if_copy_fails(self, mock_logging_info, mock_shutil_copy2, mock_path_exists):
        result = create_backup("file.txt")
        mock_logging_info.assert_called_with("create_backup() Failed to create backup: Copy failed")
        self.assertIsNone(result)


if __name__ == '__main__':
    unittest.main()
