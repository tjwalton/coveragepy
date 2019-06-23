# Licensed under the Apache License: http://www.apache.org/licenses/LICENSE-2.0
# For details: https://github.com/nedbat/coveragepy/blob/master/NOTICE.txt

"""A pytest plugin to define dynamic contexts"""

import coverage

def pytest_runtest_setup(item):
    doit(item, "setup")

def pytest_runtest_teardown(item):
    doit(item, "teardown")

def pytest_runtest_call(item):
    doit(item, "call")

def doit(item, when):
    current = coverage.Coverage.current
    if len(current) == 1:
        cov = next(iter(current))
        context = "{item.nodeid}|{when}".format(item=item, when=when)
        cov.switch_context(context)
