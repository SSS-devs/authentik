import os
import sys

from django.core.management.base import BaseCommand
from django.utils.module_loading import module_has_submodule

from authentik.lib.utils.reflection import get_apps


class Command(BaseCommand):
    """Run worker"""

    def add_arguments(self, parser):
        parser.add_argument(
            "--pid-file",
            action="store",
            default=None,
            dest="pid_file",
            help="PID file",
        )
        parser.add_argument(
            "--reload",
            action="store_true",
            dest="use_watcher",
            help="Enable autoreload",
        )
        parser.add_argument(
            "--reload-use-polling",
            action="store_true",
            dest="use_polling_watcher",
            help="Use a poll-based file watcher for autoreload",
        )
        parser.add_argument(
            "--use-gevent",
            action="store_true",
            help="Use gevent for worker concurrency",
        )
        parser.add_argument(
            "--processes",
            "-p",
            default=1,
            type=int,
            help="The number of processes to run",
        )
        parser.add_argument(
            "--threads",
            "-t",
            default=1,
            type=int,
            help="The number of threads per process to use",
        )

    def handle(
        self,
        pid_file,
        use_watcher,
        use_polling_watcher,
        use_gevent,
        processes,
        threads,
        verbosity,
        **options,
    ):
        executable_name = "dramatiq-gevent" if use_gevent else "dramatiq"
        executable_path = self._resolve_executable(executable_name)
        watch_args = ["--watch", "authentik"] if use_watcher else []
        if watch_args and use_polling_watcher:
            watch_args.append("--watch-use-polling")

        pid_file_args = []
        if pid_file is not None:
            pid_file_args = ["--pid-file", pid_file]

        verbosity_args = ["-v"] * (verbosity - 1)

        tasks_modules = self._discover_tasks_modules()
        process_args = [
            executable_name,
            "--path",
            ".",
            "--processes",
            str(processes),
            "--threads",
            str(threads),
            *watch_args,
            *pid_file_args,
            *verbosity_args,
            *tasks_modules,
        ]

        os.execvp(executable_path, process_args)  # nosec

    def _resolve_executable(self, exec_name: str):
        bin_dir = os.path.dirname(sys.executable)
        if bin_dir:
            for d in [bin_dir, os.path.join(bin_dir, "Scripts")]:
                exec_path = os.path.join(d, exec_name)
                if os.path.isfile(exec_path):
                    return exec_path
        return exec_name

    def _discover_tasks_modules(self) -> list[str]:
        # Does not support a tasks directory
        return ["authentik.tasks.setup"] + [
            f"{app.name}.tasks" for app in get_apps() if module_has_submodule(app.module, "tasks")
        ]
