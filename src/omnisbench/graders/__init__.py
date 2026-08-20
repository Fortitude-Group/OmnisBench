# SPDX-License-Identifier: Apache-2.0
"""Grader registry. Importing this package registers every grader into GRADERS."""
from . import code_unittest as _code_unittest  # noqa: F401  registers "code_unittest"
from . import stdin_tests as _stdin_tests  # noqa: F401  registers "livecodebench"
from .matchers import GRADERS

__all__ = ["GRADERS"]
