import argparse
import re
from collections import defaultdict
from functools import cache
from pathlib import Path


NAME = re.compile(r"[a-z0-9!-]+")
ATTRIBUTE = re.compile(r"[a-z0-9!]+")
TYPES = {"domain": "DOMAIN-SUFFIX", "full": "DOMAIN", "keyword": "DOMAIN-KEYWORD"}
ECR_REGEX = r".+\.dkr\.ecr\.[^\.]+\.amazonaws\.com$"
# Require one non-empty region label between ecr and amazonaws.com.
ECR_RULE = (
    "AND,((DOMAIN-WILDCARD,?*.dkr.ecr.?*.amazonaws.com),"
    "(NOT,((DOMAIN-WILDCARD,?*.dkr.ecr.*.*.amazonaws.com))))"
)


def load_lists(data_dir):
    entries = defaultdict(list)
    includes = defaultdict(list)
    names = set()
    for file in sorted(data_dir.rglob("*")):
        if not file.is_file():
            continue
        name = file.name.lower()
        if file.is_symlink() or not NAME.fullmatch(name) or name in names:
            raise ValueError(f"Unexpected data file: {file}")
        names.add(name)
        for number, raw in enumerate(file.read_text(encoding="utf-8").splitlines(), 1):
            fields = raw.partition("#")[0].split()
            if not fields:
                continue
            location = f"{file.name}:{number}"
            kind, delimiter, value = fields[0].partition(":")
            kind, value = (kind.lower(), value) if delimiter else ("domain", kind)
            modifiers = [field.lower() for field in fields[1:]]
            if kind == "include":
                value = value.lower()
                if not NAME.fullmatch(value) or any(
                    not field.startswith("@") or not ATTRIBUTE.fullmatch(field[1:].removeprefix("-"))
                    for field in modifiers
                ):
                    raise ValueError(f"{location}: malformed include")
                required = {field[1:] for field in modifiers if not field.startswith("@-")}
                excluded = {field[2:] for field in modifiers if field.startswith("@-")}
                includes[name].append((value, required, excluded))
                continue

            for field in modifiers:
                if not (field.startswith("@") and ATTRIBUTE.fullmatch(field[1:])) and not (
                    field.startswith("&") and NAME.fullmatch(field[1:])
                ):
                    raise ValueError(f"{location}: malformed attribute or affiliation")
            attributes = frozenset(field[1:] for field in modifiers if field.startswith("@"))
            affiliations = [field[1:] for field in modifiers if field.startswith("&")]
            entry = (kind, value, attributes, location)
            for target in {name, *affiliations}:
                entries[target].append(entry)
    return names | entries.keys(), entries, includes


def convert(upstream):
    names, entries, includes = load_lists(upstream / "data")
    resolving = set()

    @cache
    def resolve(name):
        if name in resolving:
            raise ValueError(f"Circular include: {name}")
        if name not in names:
            raise ValueError(f"Missing list: {name}")
        resolving.add(name)
        result = list(entries[name])
        for source, required, excluded in includes[name]:
            result.extend(
                entry for entry in resolve(source)
                if required <= entry[2] and excluded.isdisjoint(entry[2])
            )
        resolving.remove(name)
        return result

    rules = set()
    for kind, value, _, location in resolve("category-dev"):
        if kind == "regexp" and value == ECR_REGEX:
            rules.add(ECR_RULE)
        elif kind in TYPES and re.fullmatch(r"[a-zA-Z0-9_.-]+", value):
            rules.add(f"{TYPES[kind]},{value.lower()}")
        else:
            raise ValueError(f"{location}: cannot convert {kind}:{value}")
    if not rules:
        raise ValueError("Category-Dev contains no rules")

    license_text = (upstream / "LICENSE").read_text(encoding="utf-8")
    print("# Generated from v2fly/domain-list-community/data/category-dev")
    for line in license_text.splitlines():
        print(f"# {line}" if line else "#")
    print(*sorted(rules), sep="\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Convert the v2fly category-dev list to Loon.")
    parser.add_argument("upstream", type=Path)
    args = parser.parse_args()
    try:
        convert(args.upstream)
    except (OSError, ValueError) as error:
        parser.exit(1, f"{error}\n")
