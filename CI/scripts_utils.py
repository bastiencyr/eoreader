""" Utils module for scripts """

import logging
import os
from functools import wraps
from typing import Callable

import tempenv
from sertit import AnyPath, s3
from sertit.s3 import USE_S3_STORAGE
from sertit.types import AnyPathType
from sertit.unistra import (
    UNISTRA_S3_ENPOINT,
    get_db2_path,
    get_db3_path,
    get_geodatastore,
)

from eoreader import EOREADER_NAME
from eoreader.env_vars import TILE_SIZE
from eoreader.reader import Reader
from eoreader.utils import use_dask

LOGGER = logging.getLogger(EOREADER_NAME)
READER = Reader()

CI_EOREADER_S3 = "CI_EOREADER_USE_S3"


def get_ci_dir() -> AnyPathType:
    """
    Get CI DATA directory
    Returns:
        str: CI DATA directory
    """
    return AnyPath(__file__).parent.parent


def get_ci_db_dir() -> AnyPathType:
    """
    Get CI database directory (S3 bucket)
    Returns:
        str: CI database directory
    """
    if int(os.getenv(CI_EOREADER_S3, 0)):
        # ON S3
        s3.define_s3_client(default_endpoint=UNISTRA_S3_ENPOINT)
        return AnyPath("s3://sertit-eoreader-ci")
    else:
        # ON DISK
        try:
            # CI
            return AnyPath(get_db3_path(), "CI", "eoreader")
        except NotADirectoryError:
            # Windows
            db_path = AnyPath(r"//ds2/database03/CI/eoreader")
            if not db_path.is_dir():
                raise NotADirectoryError("Impossible to find get_ci_db_dir")

            return db_path


def get_ci_data_dir() -> AnyPathType:
    """
    Get CI DATA directory (S3 bucket)
    Returns:
        str: CI DATA directory
    """
    return get_ci_db_dir().joinpath("DATA")


def get_db_dir_on_disk() -> AnyPathType:
    """
    Get database directory in the DS2

    Returns:
        str: Database directory
    """
    # ON DISK
    db_dir = AnyPath(r"//ds2/database02/BASES_DE_DONNEES")

    if not db_dir.is_dir():
        try:
            db_dir = AnyPath(get_db2_path(), "BASES_DE_DONNEES")
        except NotADirectoryError:
            db_dir = AnyPath("/home", "ds2_db2", "BASES_DE_DONNEES")

    if not db_dir.is_dir():
        raise NotADirectoryError("Impossible to open database directory !")

    return db_dir


def get_db_dir() -> AnyPathType:
    """
    Get database directory in the DS2

    Returns:
        str: Database directory
    """
    with tempenv.TemporaryEnvironment({USE_S3_STORAGE: os.getenv(CI_EOREADER_S3, "0")}):
        return get_geodatastore()


def dask_env(function: Callable):
    """
    Create dask-using environment
    Args:
        function (Callable): Function to decorate

    Returns:
        Callable: decorated function
    """

    @wraps(function)
    def dask_env_wrapper():
        """S3 environment wrapper"""
        # os.environ[
        #     USE_DASK
        # ] = "0"  # For now, our CI cannot create a cluster (memory insufficient)
        # if use_dask():
        #     from dask.distributed import Client, LocalCluster
        #
        #     with LocalCluster(
        #         n_workers=4, threads_per_worker=4, processes=True
        #     ) as cluster, Client(cluster):
        #         LOGGER.info("Using DASK Local Cluster")
        #         function()
        # else:
        os.environ[TILE_SIZE] = "2048"
        if use_dask():
            LOGGER.info("Using DASK threading by chunking the data")
        else:
            LOGGER.info("No chunking will be done. Beware of memory overflow errors!")

        function()

    return dask_env_wrapper


def opt_path():
    return get_ci_db_dir().joinpath("optical")


def sar_path():
    return get_ci_db_dir().joinpath("sar")


def others_path():
    return get_ci_db_dir().joinpath("others")


def broken_s2_path():
    return get_ci_db_dir().joinpath("broken_s2")


def s3_env(function):
    return s3.s3_env(endpoint=UNISTRA_S3_ENPOINT, use_s3_env_var=CI_EOREADER_S3)(
        function
    )


def compare(to_be_checked, ref, topic):
    """
    Compare two fields
    """
    try:
        assert (
            ref == to_be_checked
        ), f"Non equal {topic}: ref ={ref} != to_be_checked={to_be_checked}"
    except AssertionError:
        assert to_be_checked.startswith("No") and to_be_checked.endswith(
            "available"
        ), f"Non equal {topic}: ref={ref} != to_be_checked={to_be_checked}"
