"""Tests for the todo app."""

import os
import tempfile
import unittest

from todo import TodoStore, main


class TodoStoreTest(unittest.TestCase):
    def setUp(self):
        fd, self.path = tempfile.mkstemp(suffix=".json")
        os.close(fd)
        os.remove(self.path)  # start with no file
        self.store = TodoStore(self.path)

    def tearDown(self):
        if os.path.exists(self.path):
            os.remove(self.path)

    def test_add_assigns_incrementing_ids(self):
        a = self.store.add("first")
        b = self.store.add("second")
        self.assertEqual(a["id"], 1)
        self.assertEqual(b["id"], 2)
        self.assertFalse(a["done"])

    def test_persistence_across_instances(self):
        self.store.add("remember me")
        reopened = TodoStore(self.path)
        self.assertEqual(len(reopened.items), 1)
        self.assertEqual(reopened.items[0]["text"], "remember me")

    def test_complete(self):
        item = self.store.add("task")
        self.store.complete(item["id"])
        self.assertTrue(self.store.items[0]["done"])

    def test_complete_unknown_id_returns_none(self):
        self.assertIsNone(self.store.complete(999))

    def test_remove(self):
        item = self.store.add("task")
        removed = self.store.remove(item["id"])
        self.assertEqual(removed["id"], item["id"])
        self.assertEqual(self.store.items, [])

    def test_remove_unknown_id_returns_none(self):
        self.assertIsNone(self.store.remove(999))

    def test_clear_done(self):
        a = self.store.add("a")
        self.store.add("b")
        self.store.complete(a["id"])
        removed = self.store.clear_done()
        self.assertEqual(len(removed), 1)
        self.assertEqual(len(self.store.items), 1)
        self.assertEqual(self.store.items[0]["text"], "b")

    def test_corrupt_file_is_ignored(self):
        with open(self.path, "w", encoding="utf-8") as fh:
            fh.write("not json{")
        store = TodoStore(self.path)
        self.assertEqual(store.items, [])

    def test_next_id_is_one_above_current_max(self):
        a = self.store.add("a")
        b = self.store.add("b")
        self.store.remove(a["id"])  # remove the lower id; max is still b
        c = self.store.add("c")
        self.assertEqual(c["id"], 3)  # one above the current highest (2)


class CliTest(unittest.TestCase):
    def setUp(self):
        fd, self.path = tempfile.mkstemp(suffix=".json")
        os.close(fd)
        os.remove(self.path)

    def tearDown(self):
        if os.path.exists(self.path):
            os.remove(self.path)

    def test_add_then_list(self):
        main(["--store", self.path, "add", "buy milk"])
        store = TodoStore(self.path)
        self.assertEqual(store.items[0]["text"], "buy milk")

    def test_done_unknown_id_exits_nonzero(self):
        with self.assertRaises(SystemExit) as ctx:
            main(["--store", self.path, "done", "42"])
        self.assertNotEqual(ctx.exception.code, 0)


if __name__ == "__main__":
    unittest.main()
