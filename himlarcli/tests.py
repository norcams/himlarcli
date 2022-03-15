import sys

def is_virtual_env():
    if not hasattr(sys, 'real_prefix'):
        print("Remember to source bin/activate!")
        sys.exit(1)
