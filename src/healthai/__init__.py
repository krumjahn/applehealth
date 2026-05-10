from importlib.metadata import version, PackageNotFoundError

try:
    __version__ = version("healthai")
except PackageNotFoundError:
    __version__ = "dev"
