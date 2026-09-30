"""Shared manifest schema and registry validation, independent of directing policies."""
import json
from pathlib import Path
from jsonschema import Draft202012Validator

ROOT = Path(__file__).resolve().parents[1]


def read_json(path):
    return json.loads(Path(path).read_text(encoding='utf-8'))


def validate_schema(name, value):
    schema = read_json(ROOT / 'schemas' / (name + '.schema.json'))
    errors = sorted(Draft202012Validator(schema).iter_errors(value), key=lambda e: str(e.path))
    if errors:
        raise ValueError(name + ': ' + '; '.join(f'{list(e.path)}: {e.message}' for e in errors))


def registry_path(folder, identifier, filename=None):
    if not isinstance(identifier, str) or not identifier or any(c not in 'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_-' for c in identifier):
        raise ValueError('Invalid registry ID ' + str(identifier))
    path = ROOT / folder / identifier / filename if filename else ROOT / folder / (identifier + '.json')
    if not path.is_file():
        raise ValueError('Unknown ' + folder + ' ID ' + identifier)
    return path


