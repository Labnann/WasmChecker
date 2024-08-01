import os

emsdk_node = os.environ.get("EMSDK_NODE")
logs_path = os.getcwd() + os.sep + "logs"
cmake_log = logs_path + os.sep + "cmake.log"
build_log = logs_path + os.sep + "build.log"
tests_log = logs_path + os.sep + "tests.log"
header_map = os.getcwd() + os.sep + "map.csv"
query_path = os.getcwd() + os.sep + "queries"
