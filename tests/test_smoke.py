# SPDX-License-Identifier: Apache-2.0
import omnisbench


def test_version_present():
    assert isinstance(omnisbench.__version__, str)
    assert omnisbench.__version__
