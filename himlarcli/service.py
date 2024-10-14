#
# Based on example from https://pagure.io/python-daemon/
#
import errno
import os
import signal
import sys
import warnings

from daemon import pidfile
from daemon.daemon import DaemonContext
import lockfile

class HimlarServiceError(Exception):
    """ Abstract base class for errors from HimlarService. """


class HimlarServiceInvalidActionError(HimlarServiceError, ValueError):
    """ Raised when specified action for HimlarService is invalid. """


class HimlarServiceStartFailureError(HimlarServiceError, RuntimeError):
    """ Raised when failure starting HimlarService. """


class HimlarServiceStopFailureError(HimlarServiceError, RuntimeError):
    """ Raised when failure stopping HimlarService. """


class HimlarService:
    """ Controller for a callable running in a separate background process.

        The first command-line argument is the action to take:

        * 'start': Become a daemon and call `app.run()`.
        * 'stop': Exit the daemon process specified in the PID file.
        * 'restart': Stop, then start.
        """

    start_message = "started with pid {pid:d}"

    def __init__(self, app):
        """ Set up the parameters of a new runner.

            :param app: The application instance; see below.
            :return: ``None``.

            The `app` argument must have the following attributes:

            * `pidfile_path`: Absolute filesystem path to a file that will
              be used as the PID file for the daemon. If ``None``, no PID
              file will be used.

            * `pidfile_timeout`: Used as the default acquisition timeout
              value supplied to the runner's PID lock file.

            * `run`: Callable that will be invoked when the daemon is
              started.
            """
        self.parse_args()
        self.app = app
        self.daemon_context = DaemonContext()
        self.daemon_context.stdin = sys.stdin
        self.daemon_context.stdout = sys.stdout
        self.daemon_context.stderr = sys.stderr

        self.pidfile = None
        if app.pidfile_path is not None:
            self.pidfile = make_pidlockfile(
                    app.pidfile_path, app.pidfile_timeout)
        self.daemon_context.pidfile = self.pidfile

    # def _open_streams_from_app_stream_paths(self, app):
    #     """ Open the `daemon_context` streams from the paths specified.
    #
    #         :param app: The application instance.
    #
    #         Open the `daemon_context` standard streams (`stdin`,
    #         `stdout`, `stderr`) as stream objects of the appropriate
    #         types, from each of the corresponding filesystem paths
    #         from the `app`.
    #         """
    #     self.daemon_context.stdin = sys.stdin #sopen(app.stdin_path, 'rt')
    #     self.daemon_context.stdout = sys.stdout #open(app.stdout_path, 'w+t')
    #     self.daemon_context.stderr = sys.stderr #open(
    #             #app.stderr_path, 'w+t', buffering=0)

    def _usage_exit(self, argv):
        """ Emit a usage message, then exit.

            :param argv: The command-line arguments used to invoke the
                program, as a sequence of strings.
            :return: ``None``.
            """
        progname = os.path.basename(argv[0])
        usage_exit_code = 2
        action_usage = "|".join(self.action_funcs.keys())
        message = "usage: {progname} {usage}".format(
                progname=progname, usage=action_usage)
        emit_message(message)
        sys.exit(usage_exit_code)

    def parse_args(self, argv=None):
        """ Parse command-line arguments.

            :param argv: The command-line arguments used to invoke the
                program, as a sequence of strings.

            :return: ``None``.

            The parser expects the first argument as the program name, the
            second argument as the action to perform.

            If the parser fails to parse the arguments, emit a usage
            message and exit the program.
            """
        if argv is None:
            argv = sys.argv

        min_args = 2
        if len(argv) < min_args:
            self._usage_exit(argv)

        self.action = str(argv[1])
        if self.action not in self.action_funcs:
            self._usage_exit(argv)

    def _start(self):
        """ Open the daemon context and run the application.

            :return: ``None``.
            :raises HimlarServiceStartFailureError: If the PID file cannot
                be locked by this process.
            """
        if is_pidfile_stale(self.pidfile):
            self.pidfile.break_lock()

        try:
            self.daemon_context.open()
        except lockfile.AlreadyLocked as exc:
            error = HimlarServiceStartFailureError(
                    "PID file {pidfile.path!r} already locked".format(
                        pidfile=self.pidfile))
            raise error from exc

        pid = os.getpid()
        message = self.start_message.format(pid=pid)
        emit_message(message)

        self.app.run()

    def _terminate_daemon_process(self):
        """ Terminate the daemon process specified in the current PID file.

            :return: ``None``.
            :raises HimlarServiceStopFailureError: If terminating the daemon
                fails with an OS error.
            """
        pid = self.pidfile.read_pid()
        try:
            os.kill(pid, signal.SIGTERM)
        except OSError as exc:
            error = HimlarServiceStopFailureError(
                    "Failed to terminate {pid:d}: {exc}".format(
                        pid=pid, exc=exc))
            raise error from exc

    def _stop(self):
        """ Exit the daemon process specified in the current PID file.

            :return: ``None``.
            :raises HimlarServiceStopFailureError: If the PID file is not
                already locked.
            """
        if not self.pidfile.is_locked():
            error = HimlarServiceStopFailureError(
                    "PID file {pidfile.path!r} not locked".format(
                        pidfile=self.pidfile))
            raise error

        if is_pidfile_stale(self.pidfile):
            self.pidfile.break_lock()
        else:
            self._terminate_daemon_process()

    def _restart(self):
        """ Stop, then start. """
        self._stop()
        self._start()

    def  _status(self):
        if self.pidfile:
            emit_message(f'pid={self.pidfile.read_pid()}')
            emit_message(f'path={self.pidfile.path}')

    action_funcs = {
            'start': _start,
            'stop': _stop,
            'restart': _restart,
            'status': _status,
            }

    def _get_action_func(self):
        """ Get the function for the specified action.

            :return: The function object corresponding to the specified
                action.
            :raises HimlarServiceInvalidActionError: if the action is
               unknown.

            The action is specified by the `action` attribute, which is set
            during `parse_args`.
            """
        try:
            func = self.action_funcs[self.action]
        except KeyError:
            error = HimlarServiceInvalidActionError(
                    "Unknown action: {action!r}".format(
                        action=self.action))
            raise error
        return func

    def do_action(self):
        """ Perform the requested action.

            :return: ``None``.

            The action is specified by the `action` attribute, which is set
            during `parse_args`.
            """
        func = self._get_action_func()
        func(self)


def emit_message(message, stream=None):
    """ Emit a message to the specified stream (default `sys.stderr`). """
    if stream is None:
        stream = sys.stderr
    stream.write("{message}\n".format(message=message))
    stream.flush()


def make_pidlockfile(path, acquire_timeout):
    """ Make a PIDLockFile instance with the given filesystem path. """
    if not isinstance(path, str):
        error = ValueError("Not a filesystem path: {path!r}".format(
                path=path))
        raise error
    if not os.path.isabs(path):
        error = ValueError("Not an absolute path: {path!r}".format(
                path=path))
        raise error
    lockfile = pidfile.TimeoutPIDLockFile(path, acquire_timeout)

    return lockfile


def is_pidfile_stale(pidfile):
    """ Determine whether a PID file is stale.

        :return: ``True`` iff the PID file is stale; otherwise ``False``.

        The PID file is “stale” if its contents are valid but do not
        match the PID of a currently-running process.
        """
    result = False

    pidfile_pid = pidfile.read_pid()
    if pidfile_pid is not None:
        try:
            os.kill(pidfile_pid, signal.SIG_DFL)
        except ProcessLookupError:
            # The specified PID does not exist.
            result = True

    return result
