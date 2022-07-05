import sys

def is_virtual_env():
    base_prefix = getattr(sys, "base_prefix", None) or getattr(sys, "real_prefix", None) or sys.prefix
    if sys.prefix == base_prefix:
        print("Remember to source bin/activate!")
        sys.exit(1)
