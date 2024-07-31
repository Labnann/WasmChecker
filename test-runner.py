import subprocess
from pathlib import Path
import string
from collections import defaultdict
import shutil
import argparse
import os
import csv
import sys
from urllib.parse import urlparse
import re
import pandas
from alive_progress import alive_bar
import time
from rich import print
import difflib
import validators

def check_exit_with_error(error, error_message):
    
    if error:
        print("exit with error!")
        print(error_message)
        exit(0)
    else: pass

def read_file(file_path):
    
    error_message = None
    try: # read from a file and return the content
        fd = open(file_path, "r")
        text = fd.read()
        fd.close()
        return (0, text)
    except Exception as error:
        print(f"error: could not read {file_path}!")
        error_message = error
    return (1, error_message)

def write_file(file_path, file_content):

    error_message = None
    try: # write a given text in a file
        fd = open(file_path, "w")
        fd.write(file_content)
        fd.close()
        return (0, error_message)
    except Exception as error:
        print(f"error: could not write in {file_path}!")
        error_message = error
    return (1, error_message)

def modify_file(file_path, file_content):
    
    error_message = None
    try: # add a given text to the end of a file
        fd = open(file_path, "a")
        fd.write(file_content + os.linesep)
        fd.close()
        return (0, error_message)
    except Exception as error:
        print(f"error: could not write in {file_path}!")
        error_message = error
    return (1, error_message)

def get_first_error(error_keyword, file_path):

    # return the first error message
    error_message = None
    error_pattern = f"{error_keyword} (.+)"
    error, file_content = read_file(file_path)
    check_exit_with_error(error, file_content)

    matched = re.search(error_pattern, file_content)

    if matched: matched_error_line = matched.group(1)
    else: matched_error_line = "_empty_"
    return matched_error_line

def run_tests(WASM=False):

    test_command = "make test"
    if WASM: test_command = "emmake " + test_command
    try: # run make test to run tests
        fd1 = open("test_command.txt", "w")
        fd2 = open("command.txt", "w")
        subprocess.run(test_command, shell=True, check=True, stdout=fd1, stderr=fd2)
        fd1.close()
        fd2.close()
    except subprocess.CalledProcessError as error:
        print(f"testing error: {error}")
        matched_error_line = get_first_error("Output from these tests are in:", "command.txt")
        if matched_error_line != "_empty_": return (1, matched_error_line)
        matched_error_line = get_first_error("No rule to make target 'test'.", "command.txt")
        if matched_error_line != "_empty_": return (1, None)
    return (0, None)

def modify_CTestTestfile(file_path, project_path):
    
    pattern = r"add_test\(\s*(.*)\s*\)"
    error, file_content = read_file(file_path)
    check_exit_with_error(error, file_content)

    matched = re.findall(pattern, file_content)
    for match_str in matched:
        #print("match_str = ", match_str)
        test_matches = re.findall(r'"([^"]+)"|\S+', match_str)
        test_name = re.findall(r'^([^"\s]+)', match_str)
        if len(test_name) > 0:
            test_name = test_name[0]
        else:
            test_name = '"' + test_matches[0] + '"'
        test_args = test_matches[1:]
        
        #print("test_name = ", test_name)
        #print("test_args = ", test_args)
        
        end_parts = [os.path.basename(s) for s in test_args]
        #print(end_parts)
        if "node" in end_parts and any(s.endswith(".js") for s in end_parts): continue
        elif "node" in end_parts:
            index = end_parts.index("node")
            new_str = test_name
            for s in test_args:
                if test_args.index(s) == index + 1:
                    if not os.path.exists(s + ".js"):
                        #print("I'm going to find ", end_parts[test_args.index(s)] + ".js")
                        error, f = find_file(end_parts[test_args.index(s)] + ".js", project_path)
                        check_exit_with_error(error, f)
                        if (len(f) > 0): s = f[0][:-3]
                    new_str += " " + '"' + s + ".js" + '"'
                else: new_str += " " + '"' + s + '"'
            
            #print("I'm going to replace ", match_str, " with ", new_str)
            file_content = file_content.replace(match_str, new_str)
            error, error_message = write_file(file_path, file_content)
            check_exit_with_error(error, error_message)
        
        elif any(s.endswith(".js") for s in end_parts):
            new_str = test_name
            for s in test_args:
                if s.endswith(".js"):
                    if not os.path.exists(s):
                        #print("I'm going to find ", end_parts[test_args.index(s)])
                        error, f = find_file(end_parts[test_args.index(s)], project_path)
                        check_exit_with_error(error, f)
                        if (len(f) > 0): s = f[0]
                    new_str += " " + '"' + emsdk_node + '"' + " " + '"' + s + '"'
                else: new_str += " " + '"' + s + '"'
            
            #print("I'm going to replace ", match_str, " with ", new_str)
            file_content = file_content.replace(match_str, new_str)
            error, error_message = write_file(file_path, file_content)
            check_exit_with_error(error, error_message)
        
        elif len(end_parts) == 1:
            if not os.path.exists(test_args[0] + ".js"):
                #print("I'm going to find ", end_parts[0] + ".js")
                error, f = find_file(end_parts[0] + ".js", project_path)
                check_exit_with_error(error, f)
                if (len(f) > 0): test_args[0] = f[0][:-3]
            new_str = test_name + " " + '"' + emsdk_node + '"' + " " + '"' + test_args[0] + ".js" + '"'
            #print("I'm going to replace ", match_str, " with ", new_str)
            file_content = file_content.replace(match_str, new_str)
            error, error_message = write_file(file_path, file_content)
            check_exit_with_error(error, error_message)
        
        else: # test arguments are more than one
            new_str = test_name
            for s in test_args:
                if os.path.exists(s + ".js"):
                    new_str += " " + '"' + emsdk_node + '"' + " " + '"' + s + ".js" + '"'
                else: new_str += " " + '"' + s + '"'
            #print("I'm going to replace ", match_str, " with ", new_str)
            file_content = file_content.replace(match_str, new_str)
            error, error_message = write_file(file_path, file_content)
            check_exit_with_error(error, error_message)

def build_project(project_dir, WASM=False):

    # get current directory
    curr_dir = os.getcwd()

    # change to the project directory
    os.chdir(project_dir)

    # create the build directory and change into it
    #os.makedirs("build", exist_ok=True)
    os.chdir("build")
    
    make_command = "cmake --build ."
    if WASM: make_command = "emmake " + make_command

    try: # run make to build the project
        fd = open("command.txt", "w")
        subprocess.run(make_command, shell=True, check=True, stderr=fd, stdout=subprocess.PIPE)
        fd.close()
    except subprocess.CalledProcessError as error:
        log_file = build_log
        print(f"build error: {error}")
        matched_error_line = "unknown"
        matched_error_line = get_first_error("Fatal:", "command.txt")
        if matched_error_line == "_empty_":
            matched_error_line = get_first_error("error:", "command.txt")
        print(matched_error_line)
        log_text = "Error: " + matched_error_line + " happend when running " + make_command
        error, error_message = modify_file(log_file, log_text)
        check_exit_with_error(error, error_message)
        print("running make failed!***")
        return (1, matched_error_line)

    make_command = "make check"
    if WASM: make_command = "emmake " + make_command

    try: # run make to build the project
        fd = open("command.txt", "w")
        subprocess.run(make_command, shell=True, check=True, stderr=fd, stdout=subprocess.PIPE)
        fd.close()
    except subprocess.CalledProcessError as error:
        print("running make check failed!***")
        #return (1, matched_error_line)
    
    os.chdir(curr_dir)
    return (0, None)

def find_file(file_name, search_dir):

    find_command = f'find {search_dir} -name "{file_name}"'
    print(find_command)
    try: # find the path to a file and return it
        fd = open("file_paths.txt", "w")
        subprocess.run(find_command, shell=True, check=True, stdout=fd, stderr=subprocess.PIPE)
        fd.close()
    except subprocess.CalledProcessError as error:
        error_message = error
        os.remove("file_paths.txt")
        return (1, error_message)

    error, file_content = read_file("file_paths.txt")
    check_exit_with_error(error, file_content)

    files = file_content.splitlines()
    files = [os.path.abspath(file) for file in files]
    os.remove("file_paths.txt")
    return (0, files)

def check_tests(file_path):

    error, file_content = read_file(file_path)
    check_exit_with_error(error, file_content)

    pattern = r"add_test\(\s*(.*)\s*\)"
    error, file_content = read_file(file_path)
    check_exit_with_error(error, file_content)

    matched = re.findall(pattern, file_content)
    if len(matched) == 0:
        exe_pattern = r"add_executable\(((.|\n)*?)\)"
        exe_matched = re.findall(f"({exe_pattern})", file_content)
        print("** NO TEST For EXECUTABLE **")
        new_file_content = file_content
        for executable_body in exe_matched:
            print(executable_body)
            executable_file = executable_body[1].split()[0]
            #print("executable_file = ", executable_file)
            add_test = f"add_test(NAME {executable_file} COMMAND {executable_file})"
            #print(add_test)
            #print("I'm going to replace ", executable_body[0], " with ", 
            #        executable_body[0] + os.linesep + add_test)
            new_file_content = new_file_content.replace(executable_body[0], 
                    executable_body[0] + os.linesep + add_test)
            error, error_message = write_file(file_path, new_file_content)
            check_exit_with_error(error, error_message)

    for match_str in matched:
        print("match_str = ", match_str)

def enable_testing(file_path, test_flag):
    
    error, file_content = read_file(file_path)
    check_exit_with_error(error, file_content)

    pattern = r"add_subdirectory\(test(.*)"
    matched = re.search(pattern, file_content, re.IGNORECASE)
    #print(matched)
    if matched:
        str_match = matched.group()
        #print("I'm going to replace ", str_match, " with ", 
        #        os.linesep + "enable_testing()" + os.linesep, str_match)
        new_file_content = file_content.replace(str_match, 
                os.linesep + "enable_testing()" + os.linesep + str_match)
        error, error_message = write_file(file_path, new_file_content)
        check_exit_with_error(error, error_message)
        return

    pattern = f"if\s*\(\s*{test_flag}\s*\)(.*)"
    matched = re.search(pattern, file_content, re.IGNORECASE)
    if matched:
        str_match = matched.group()
        #print("I'm going to replace ", str_match, " with ", 
        #        str_match + os.linesep + "enable_testing()" + os.linesep)
        new_file_content = file_content.replace(str_match, 
                str_match + os.linesep + "enable_testing()" + os.linesep)
        error, error_message = write_file(file_path, new_file_content)
        check_exit_with_error(error, error_message)
    else:
        new_file_content = file_content + os.linesep + "enable_testing()"
        error, error_message = modify_file(file_path, new_file_content)
        check_exit_with_error(error, error_message)

def set_test_timeout(timeout, make_file):
    
    error, file_content = read_file(make_file)
    check_exit_with_error(error, file_content)
    
    pattern = r"/usr/bin/ctest (.*)"
    matched = re.search(pattern, file_content)
    #print(matched)
    
    if matched: # add --timeout to tests 
        str_match = matched.group(1)
        new_str_match = "--timeout " + timeout + " " + str_match
        new_file_content = file_content.replace(str_match, new_str_match)
        #print("I'm going to replace ", str_match, " with ", new_str_match)
        error, error_message = write_file(make_file, new_file_content)
        check_exit_with_error(error, error_message)
    else: return (1, "could not set timeout")
    return (0, None)

def build_codebase_in_WebAssembly(wasm_branch, timeout=None):

    error, library = build_project(wasm_branch, WASM=True)

    error, files = find_file("CTestTestfile.cmake", wasm_branch)
    check_exit_with_error(error, files)

    for file in files:
        modify_CTestTestfile(file, wasm_branch)

    if timeout and timeout.isdigit(): # check if timeout is a number
        make_file = wasm_branch + os.sep + "build" + os.sep + "Makefile"
        error, error_message = set_test_timeout(timeout, make_file)
        #check_exit_with_error(error, error_message)
    print("build_codebase_in_WebAssembly returned successfully!")

def check_test_availability(file_content):
 
    lines = file_content.split("\n")
    
    no_test_message = "No tests were found!!!"
    if no_test_message in lines:
        return (1, no_test_message)
    else: return (0, None)

def add_test_for_executables(branch_dir):
    print(os.getcwd())
    error, files = find_file("CMakeLists.txt", branch_dir)
    check_exit_with_error(error, files)
    print("akshdjahda")
    for file in files:
        check_tests(file)
    print("add_test_for_executables returned successfully!")

def is_number(s):

    try: float(s); return True
    except ValueError: return False

def find_blocking_tests(log_file):
    error, file_content = read_file(log_file)
    check_exit_with_error(error, file_content)

    blocks = file_content.split('\n----------------------------------------------------------\n')
    data_frame = pandas.DataFrame(columns=['test_name', 'command', 'directory', 'start_time',
                                        'end_time', 'time_elapsed', 'status', 'output'])
    test_name="";command="";directory=""
    start_time="";time_elapsed="";status="";end_time=""
    for block in range(len(blocks)//3):
        lines = blocks[block*3+1].strip().splitlines()
        for line in lines:
            if 'Testing:' in line: test_name = line.split('Testing: ')[1]
            if 'Command:' in line: command = line[9:]
            if 'Directory:' in line: directory = line[11:]
            if 'start time:' in line: start_time = line.split('start time: ')[1]
            if 'time elapsed: ' in line: time_elapsed = line.split('time elapsed: ')[1]
            if 'Test ' in line: status = line.split('Test ')[1].split(' ')[0]
            if 'end time: ' in line: end_time = line.split('end time: ')[1]

        output = blocks[block*3+2]
        status = status.translate(str.maketrans("", "", string.punctuation))
        data_frame.loc[block] = [test_name, command, directory, start_time,
                            end_time, time_elapsed, status, output]
    data_frame.to_csv('log.csv', sep=',', encoding='utf-8')
    return data_frame

def extract_failure_line(text):
    # Regular expression to match the pattern "X tests failed out of Y"
    pattern = r"\d+ tests failed out of \d+"
    # Search for the pattern in the given text
    match = re.search(pattern, text)
    # If a match is found, print the matching string
    if match:
        print(match.group())
    else:
        print("No matching line found.")

def copy_blocking_files_into_correct_path(data_files, destination_paths, search_dir):

    for indx in range(len(data_files)):
        data_file_name = data_files[indx]
        destination_path = destination_paths[indx]
        error, files = find_file(data_file_name, search_dir)
        check_exit_with_error(error, files)
        
        for file in files:
            shutil.copy(file, destination_path)
            print("I'm copying ", file, " into ", destination_path)

def get_cmake_lists(branch_dir):
    cmake_lists = branch_dir + os.sep + "CMakeLists.txt"
    if os.path.exists(cmake_lists):
        return (0, os.path.abspath(cmake_lists))
    else: return (1, f"No CMakeLists.txt is in {branch_dir}!")
    
emsdk_node = os.environ.get("EMSDK_NODE")

logs_path = os.getcwd() + os.sep + "llooggs"
cmake_log = logs_path + os.sep + "cmake.log"
build_log = logs_path + os.sep + "build.log"
tests_log = logs_path + os.sep + "tests.log"
header_map = os.getcwd() + os.sep + "map.csv"

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    pgroup = parser.add_mutually_exclusive_group(required=True)
    pgroup.add_argument("-p", "--path", help="path to the codebase", required=False)
    parser.add_argument("-o", "--timeout", help="tests timeout", required=False)
    parser.add_argument("-t", "--test", help="tests flag", required=False)
    args = parser.parse_args()

    if args.timeout:
        timeout = args.timeout
    else: timeout = None

    if args.test: test_flag = args.test
    else: test_flag = None

    with alive_bar(5, title='Processing', length=20, bar='blocks', spinner='twirls') as bar:
        
        project_dir = os.path.abspath(args.path)
        wasm_branch = project_dir
        error, wasm_branch_cmake_lists = get_cmake_lists(wasm_branch)
        check_exit_with_error(error, wasm_branch_cmake_lists)
        
        print("[bold green]Building Codebase in WebAssembly[/bold green]")
        build_codebase_in_WebAssembly(wasm_branch, timeout)
        bar()
        os.chdir(project_dir + os.sep + "build")
        print("[bold red]Running Tests in WebAssembly[/bold red]")
        loop_flag = False
        while (not loop_flag):
            print("Hello")
            error, log_file = run_tests(WASM=True)
            if error: # an error happened when running tests
                if log_file: # tests are available and at least one test failed
                    error, file_content = read_file(log_file)
                    check_exit_with_error(error, file_content)
                    #print(file_content)
                    data_frame = find_blocking_tests(log_file)
                    pattern = r"open '([^']*)'"
                    filtered = data_frame[data_frame["output"].str.contains("Error: ENOENT", case=False, na=False)]
                    if filtered.empty: loop_flag = True
                    else:
                        filtered["file_name"] = filtered["output"].str.extract(pattern, expand=False)
                        copy_blocking_files_into_correct_path(filtered["file_name"].tolist(), filtered["directory"].tolist(), project_dir)
                        loop_flag = False
                        print("I made flag true since tests are available and some tests failed")
                else: # no target for test, should enable testing
                    enable_testing(wasm_branch_cmake_lists, test_flag)
                    build_codebase_in_WebAssembly(wasm_branch, timeout)
                    print("I enabled testing option and built the codebase again")
            else: # no error happened when running tests
                error, file_content = read_file("command.txt")
                check_exit_with_error(error, file_content)
                error, error_message = check_test_availability(file_content)
                if error == 1: # tests are not available, need to be added
                    add_test_for_executables(wasm_branch)
                    build_codebase_in_WebAssembly(wasm_branch, timeout)
                    print("I added tests and built the codebase again")
                else:
                    print("Here")
                    log_file = "Testing/Temporary/LastTest.log"
                    error, file_content = read_file(log_file)
                    check_exit_with_error(error, file_content)
                    data_frame = find_blocking_tests(log_file)
                    pattern = r"open '([^']*)'"
                    filtered = data_frame[data_frame["output"].str.contains("Error: ENOENT", case=False, na=False)]
                    if filtered.empty:
                        loop_flag = True
                        print("I made flag true since all the tests passed and everything is done!")
                    else:
                        filtered["file_name"] = filtered["output"].str.extract(pattern, expand=False)
                        copy_blocking_files_into_correct_path(filtered["file_name"].tolist(), filtered["directory"].tolist(), wasm_branch)
                        loop_flag = False
                    # print("I made flag true since all the tests passed and everything is done!")
        error, wasm_test_result = read_file("test_command.txt")
        check_exit_with_error(error, wasm_test_result)
        extract_failure_line(wasm_test_result)
        bar()
