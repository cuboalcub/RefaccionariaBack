# Copyright (c) Meta Platforms, Inc. and affiliates.
#
# This source code is licensed under the MIT license found in the
# LICENSE file in the root directory of this source tree.

import subprocess
import sys


if __name__ == "__main__":
    proc = subprocess.run(["pyrefly", *sys.argv[1:]])
    sys.exit(proc.returncode)
