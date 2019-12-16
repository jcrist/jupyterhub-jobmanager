import asyncio
import logging
import signal

from tornado import web
from tornado.log import LogFormatter
from tornado.gen import IOLoop
from tornado.platform.asyncio import AsyncIOMainLoop
from traitlets import Unicode, Integer
from traitlets.config import Application, catch_config_error

from . import __version__ as VERSION
from . import handlers
from .utils import TaskPool


Application.log_level.default_value = "INFO"
Application.log_format.default_value = (
    "%(color)s[%(levelname)1.1s %(asctime)s.%(msecs).03d "
    "%(name)s]%(end_color)s %(message)s"
)


class JobManager(Application):
    """Manage jobs for JupyterHub users"""

    name = "jupyterhub-jobmanager"
    version = VERSION

    description = """Start jupyterhub-jobmanager"""

    examples = """

    Start the server with config file ``config.py``

        jupyterhub-jobmanager -f config.py
    """

    aliases = {
        "f": "JobManager.config_file",
        "config": "JobManager.config_file",
    }

    config_file = Unicode(
        "jobmanager_config.py", help="The config file to load", config=True
    )

    # Fail if the config file errors
    raise_config_file_errors = True

    _log_formatter_cls = LogFormatter

    listen_host = Unicode(
        "0.0.0.0", help="The host the server should listen at", config=True,
    )

    listen_port = Integer(
        8000, help="The port the server should listen at", config=True,
    )

    @catch_config_error
    def initialize(self, argv=None):
        super().initialize(argv)
        if self.subapp is not None:
            return
        self.log.info("Starting jupyterhub-jobmanager - version %s", VERSION)
        self.load_config_file(self.config_file)
        self.init_logging()
        self.init_asyncio()
        self.init_tornado_application()

    def init_logging(self):
        # Prevent double log messages from tornado
        self.log.propagate = False

        # hook up tornado's loggers to our app handlers
        from tornado.log import app_log, access_log, gen_log

        for log in (app_log, access_log, gen_log):
            log.name = self.log.name
            log.handlers[:] = []
        logger = logging.getLogger("tornado")
        logger.handlers[:] = []
        logger.propagate = True
        logger.parent = self.log
        logger.setLevel(self.log.level)

    def init_asyncio(self):
        self.task_pool = TaskPool()

    def init_tornado_application(self):
        self.handlers = list(handlers.default_handlers)
        self.tornado_application = web.Application(
            self.handlers, log=self.log, jobmanager=self,
        )

    async def start_async(self):
        self.init_signal()
        await self.start_tornado_application()

    async def start_tornado_application(self):
        self.http_server = self.tornado_application.listen(
            self.listen_port, self.listen_host
        )
        self.log.info("JupyterHub Job Manager started successfully!")
        self.log.info("API listening at %s:%d", self.listen_host, self.listen_port)

    async def start_or_exit(self):
        try:
            await self.start_async()
        except Exception:
            self.log.critical(
                "Failed to start JupyterHub Job Manager, shutting down", exc_info=True
            )
            await self.stop_async(stop_event_loop=False)
            self.exit(1)

    def start(self):
        if self.subapp is not None:
            return self.subapp.start()
        AsyncIOMainLoop().install()
        loop = IOLoop.current()
        loop.add_callback(self.start_or_exit)
        try:
            loop.start()
        except KeyboardInterrupt:
            print("\nInterrupted")

    def init_signal(self):
        loop = asyncio.get_event_loop()
        for s in (signal.SIGTERM, signal.SIGINT):
            loop.add_signal_handler(s, self.handle_shutdown_signal, s)

    def handle_shutdown_signal(self, sig):
        self.log.info("Received signal %s, initiating shutdown...", sig.name)
        asyncio.ensure_future(self.stop_async())

    async def stop_async(self, timeout=5, stop_event_loop=True):
        try:
            # Stop the server to prevent new requests
            if hasattr(self, "http_server"):
                self.http_server.stop()

            if hasattr(self, "task_pool"):
                await self.task_pool.close(timeout=timeout)
        except Exception:
            self.log.error("Error while shutting down:", exc_info=True)
        # Stop the event loop
        if stop_event_loop:
            IOLoop.current().stop()


main = JobManager.launch_instance
