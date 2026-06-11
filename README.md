# todo

A small command-line todo app written in Python. No dependencies beyond the
standard library. Todos are stored as JSON (default: `~/.todo.json`).

## Usage

```bash
python3 todo.py add "Buy milk"
python3 todo.py add "Write the report"
python3 todo.py list
python3 todo.py done 1
python3 todo.py list --pending
python3 todo.py remove 2
python3 todo.py clear        # drop all completed todos
```

### Commands

| Command            | Description                          |
| ------------------ | ------------------------------------ |
| `add <text>`       | Add a new todo                       |
| `list`             | List all todos                       |
| `list --pending`   | List only unfinished todos           |
| `list --done`      | List only completed todos            |
| `done <id>`        | Mark a todo as complete              |
| `remove <id>`      | Delete a todo                        |
| `clear`            | Remove all completed todos           |

Use `--store <path>` to point at a different JSON file.

## Optional: install as a `todo` command

```bash
chmod +x todo.py
ln -s "$(pwd)/todo.py" ~/.local/bin/todo   # ensure ~/.local/bin is on PATH
todo add "Now I can run it anywhere"
```

## Running the tests

```bash
python3 -m unittest
```
