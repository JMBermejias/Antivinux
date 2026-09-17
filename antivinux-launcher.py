#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Arranque de Antivinux desde el sistema instalado (no en consola)."""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from antivinux.__main__ import main  # noqa: E402

if __name__ == "__main__":
    sys.exit(main())