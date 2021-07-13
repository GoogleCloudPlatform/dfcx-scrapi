"""Pytest config file"""
# Copyright 2021 Google LLC. This software is provided as-is, without warranty
# or representation for any use or purpose. Your use of it is subject to your
# agreement with Google.

import pytest


def pytest_addoption(parser):
    """Method to add option for creds in tests."""
    parser.addoption("--creds", action="store")


@pytest.fixture(scope="session")
def creds(request):
    """Fixture to share creds across the test class"""
    return request.config.getoption("--creds")
