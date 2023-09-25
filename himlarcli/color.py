import sys

class Color:

    # Check if we are on a TTY
    if sys.stdout.isatty():
        __HAVE_TTY = True
    else:
        __HAVE_TTY = False

    # General effects
    reset = '\033[0m'   if __HAVE_TTY else '' # Default color and effects
    bold  = '\033[1m'   if __HAVE_TTY else '' # Bold/brighter
    dim   = '\033[2m'   if __HAVE_TTY else '' # Dim/darker
    cur   = '\033[3m'   if __HAVE_TTY else '' # Italic font
    und   = '\033[4m'   if __HAVE_TTY else '' # Underline
    rev   = '\033[7m'   if __HAVE_TTY else '' # Reverse/Inverted
    cof   = '\033[?25l' if __HAVE_TTY else '' # Cursor Off
    con   = '\033[?25h' if __HAVE_TTY else '' # Cursor On
    stk   = '\033[09m'  if __HAVE_TTY else '' # Strikethrough
    inv   = '\033[08m'  if __HAVE_TTY else '' # Invisible

    class fg: # Foreground color

        # Check if we are on a TTY
        if sys.stdout.isatty():
            __HAVE_TTY = True
        else:
            __HAVE_TTY = False

        # Base color
        BLK = '\033[30m' if __HAVE_TTY else ''
        RED = '\033[31m' if __HAVE_TTY else ''
        GRN = '\033[32m' if __HAVE_TTY else ''
        YLW = '\033[33m' if __HAVE_TTY else ''
        BLU = '\033[34m' if __HAVE_TTY else ''
        MGN = '\033[35m' if __HAVE_TTY else ''
        CYN = '\033[36m' if __HAVE_TTY else ''
        WHT = '\033[37m' if __HAVE_TTY else ''

        # Lighter shade
        blk = '\033[90m' if __HAVE_TTY else ''
        red = '\033[91m' if __HAVE_TTY else ''
        grn = '\033[92m' if __HAVE_TTY else ''
        ylw = '\033[93m' if __HAVE_TTY else ''
        blu = '\033[94m' if __HAVE_TTY else ''
        mgn = '\033[95m' if __HAVE_TTY else ''
        cyn = '\033[96m' if __HAVE_TTY else ''
        wht = '\033[97m' if __HAVE_TTY else ''

    class bg: # Background color

        # Check if we are on a TTY
        if sys.stdout.isatty():
            __HAVE_TTY = True
        else:
            __HAVE_TTY = False

        # Base color
        BLK = '\033[40m' if __HAVE_TTY else '' # Black
        RED = '\033[41m' if __HAVE_TTY else '' # Red
        GRN = '\033[42m' if __HAVE_TTY else '' # Green
        YLW = '\033[43m' if __HAVE_TTY else '' # Yellow
        BLU = '\033[44m' if __HAVE_TTY else '' # Blue
        MGN = '\033[45m' if __HAVE_TTY else '' # Magenta
        CYN = '\033[46m' if __HAVE_TTY else '' # Cyan
        WHT = '\033[47m' if __HAVE_TTY else '' # White

        # Lighter shade
        blk = '\033[100m' if __HAVE_TTY else '' # Black
        red = '\033[101m' if __HAVE_TTY else '' # Red
        grn = '\033[102m' if __HAVE_TTY else '' # Green
        ylw = '\033[103m' if __HAVE_TTY else '' # Yellow
        blu = '\033[104m' if __HAVE_TTY else '' # Blue
        mgn = '\033[105m' if __HAVE_TTY else '' # Magenta
        cyn = '\033[106m' if __HAVE_TTY else '' # Cyan
        wht = '\033[107m' if __HAVE_TTY else '' # White
