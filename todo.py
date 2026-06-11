#!/usr/bin/env python3
"""A simple command-line todo application with JSON persistence."""

import argparse
import json
import os
import sys
from datetime import datetime

DEFAULT_STORE = os.path.expanduser("~/.todo.json")


class TodoStore:
    """Loads, mutates, and saves a list of todo items backed by a JSON file."""

    def __init__(self, path=DEFAULT_STORE):
        self.path = path
        self.items = self._load()

    def _load(self):
        if not os.path.exists(self.path):
            return []
        try:
            with open(self.path, "r", encoding="utf-8") as fh:
                data = json.load(fh)
        except (json.JSONDecodeError, OSError):
            return []
        return data if isinstance(data, list) else []

    def save(self):
        with open(self.path, "w", encoding="utf-8") as fh:
            json.dump(self.items, fh, indent=2)

    def _next_id(self):
        return max((item["id"] for item in self.items), default=0) + 1

    def add(self, text):
        item = {
            "id": self._next_id(),
            "text": text,
            "done": False,
            "created": datetime.now().isoformat(timespec="seconds"),
        }
        self.items.append(item)
        self.save()
        return item

    def _find(self, item_id):
        for item in self.items:
            if item["id"] == item_id:
                return item
        return None

    def complete(self, item_id):
        item = self._find(item_id)
        if item is None:
            return None
        item["done"] = True
        self.save()
        return item

    def remove(self, item_id):
        item = self._find(item_id)
        if item is None:
            return None
        self.items.remove(item)
        self.save()
        return item

    def clear_done(self):
        removed = [i for i in self.items if i["done"]]
        self.items = [i for i in self.items if not i["done"]]
        self.save()
        return removed


def cmd_add(store, args):
    item = store.add(args.text)
    print(f"Added #{item['id']}: {item['text']}")


def cmd_list(store, args):
    items = store.items
    if args.pending:
        items = [i for i in items if not i["done"]]
    elif args.done:
        items = [i for i in items if i["done"]]
    if not items:
        print("No todos. Add one with: todo add \"your task\"")
        return
    for item in items:
        mark = "x" if item["done"] else " "
        print(f"  [{mark}] #{item['id']} {item['text']}")


def cmd_done(store, args):
    item = store.complete(args.id)
    if item is None:
        print(f"No todo with id #{args.id}", file=sys.stderr)
        sys.exit(1)
    print(f"Completed #{item['id']}: {item['text']}")


def cmd_remove(store, args):
    item = store.remove(args.id)
    if item is None:
        print(f"No todo with id #{args.id}", file=sys.stderr)
        sys.exit(1)
    print(f"Removed #{item['id']}: {item['text']}")


def cmd_clear(store, args):
    removed = store.clear_done()
    print(f"Cleared {len(removed)} completed todo(s)")


def build_parser():
    parser = argparse.ArgumentParser(prog="todo", description="A simple todo app.")
    parser.add_argument(
        "--store",
        default=DEFAULT_STORE,
        help=f"Path to the JSON store (default: {DEFAULT_STORE})",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    p_add = sub.add_parser("add", help="Add a new todo")
    p_add.add_argument("text", help="The todo text")
    p_add.set_defaults(func=cmd_add)

    p_list = sub.add_parser("list", help="List todos")
    group = p_list.add_mutually_exclusive_group()
    group.add_argument("--pending", action="store_true", help="Show only pending")
    group.add_argument("--done", action="store_true", help="Show only completed")
    p_list.set_defaults(func=cmd_list)

    p_done = sub.add_parser("done", help="Mark a todo as complete")
    p_done.add_argument("id", type=int, help="The todo id")
    p_done.set_defaults(func=cmd_done)

    p_remove = sub.add_parser("remove", help="Remove a todo")
    p_remove.add_argument("id", type=int, help="The todo id")
    p_remove.set_defaults(func=cmd_remove)

    p_clear = sub.add_parser("clear", help="Remove all completed todos")
    p_clear.set_defaults(func=cmd_clear)

    return parser


def main(argv=None):
    parser = build_parser()
    args = parser.parse_args(argv)
    store = TodoStore(args.store)
    args.func(store, args)


if __name__ == "__main__":
    main()
