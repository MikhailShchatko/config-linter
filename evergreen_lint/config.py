import os
from typing import Any, List, cast

import yaml
from typing_extensions import TypedDict

from evergreen_lint.rules import RULES


class Rule(TypedDict, total=False):
    rule: str


class Config(TypedDict):
    files: List[str]
    rules: List[Rule]


def load(stream: Any, path: os.PathLike) -> Config:
    def _validate(rawconf: dict) -> Config:
        if not isinstance(rawconf, dict):
            raise RuntimeError(f"expected to read a dictionary, but read a {type(rawconf)}")
        if "files" not in rawconf or not rawconf["files"]:
            raise RuntimeError("'files' key: a list of files is required")
        for i, file in enumerate(rawconf["files"]):
            if not isinstance(file, str):
                raise RuntimeError(f"'files', index {i}: expected a str, got a {type(file)}")
            rawconf["files"][i] = os.path.abspath(os.path.join(path, rawconf["files"][i]))

        if "rules" not in rawconf or not rawconf["rules"]:
            raise RuntimeError("'rules' key: a list of rules is required")
        for i, rule in enumerate(rawconf["rules"]):
            if "rule" not in rule:
                raise RuntimeError("'rules' index {i}: unnamed rule (missing 'rule' key)")
            if rule["rule"] not in RULES:
                raise RuntimeError("'rules' index {i}: unknown rule '{rule[]}'")

            config_file_params = set(rule.keys())
            config_file_params.remove("rule")

            rulecls = RULES[rule["rule"]]
            default_rule_params = set(rulecls.defaults().keys())
            # if default_rule_params is not a super or the same set of config_file_params
            if not (default_rule_params >= config_file_params):
                raise RuntimeError(
                    f"'rules' index {i}: rule '{rule['rule']}': unknown config params: "
                    f"{config_file_params - default_rule_params}"
                )

        return cast(Config, rawconf)

    try:
        rawconf = yaml.safe_load(stream)
        return _validate(rawconf)
    except RuntimeError as e:
        raise RuntimeError(f"config file invalid: {str(e)}")


def load_file(fh) -> Config:
    with open(fh, "r") as handle:
        return load(handle, os.path.dirname(fh))


STUB = """
# These paths are relative to the directory containing this configuration file
files:
    - ./evergreen.yml

rules:
    # this is a list of all rules available, their parameters, and their
    # default values. Comment out a rule to disable it

    # Limit to maximum number of uses of keyval.inc to the limit parameter.
    - rule: "limit-keyval-inc"
      # the maximum number of keyval.inc commands to allow in your YAML
      limit: 0

    # Require that shell.exec invocations explicitly set their shell
    - rule: "shell-exec-explicit-shell"
    # Do not allow working_dir to be set on shell.exec, and subprocess.exec
    - rule: "no-working-dir-on-shell"
    # Lint the names of functions using the given regex
    - rule: "invalid-function-name"
      # a Python3 re compatible regex to describe a valid function name
      # You are strongly advised to leave the optional quotes around the regex
      # to avoid subtle bugs introduced by YAML parsing.
      regex: "^f_[a-z][A-Za-z0-9_]*"
    # Do not allow use of shell.exec (Use subprocess.exec)
    - rule: "no-shell-exec"
    # Do not allow multi-line values for expansions.update
    - rule: "no-multiline-expansions-update"
    # Lint build parameter names using the given regex, and optionally require
    # descriptions for the parameter
    - rule: "invalid-build-parameter"
      # a Python3 re compatible regex to describe a valid build parameter name
      regex: "[a-z][a-z0-9_]*"
      # if true, require a non-empty description for the parameter.
      require-description: true
    # Require expansions.write to be placed before subprocess.exec commands
    # for scripts that match the given regex
    - rule: "required-expansions-write"
      # applicable shell script
      regex: .*\\/evergreen\\/.*\\.sh
"""[
    1:-1
]  # <--- this strips the leading and trailing newlines from this HEREDOC