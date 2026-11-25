#!/usr/bin/env python3
import sys
import os

# Ensure local imports work
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import GearLeverForTarApp


def main():
    app = GearLeverForTarApp()
    return app.run(sys.argv)


if __name__ == "__main__":
    sys.exit(main())
