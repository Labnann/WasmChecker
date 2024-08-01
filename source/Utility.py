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
from source import FileHandler

def check_exit_with_error(error, error_message):
    if error:
        print("exit with error!")
        print(error_message)
        exit(0)
    else: pass

def find_file(file_name, search_dir):
    #file_name = file_name.encode().decode('unicode_escape')
    find_command = f'find {search_dir} -name "{file_name}"'
    try: # find the path to a file and return it
        fd = open("file_paths.txt", "w")
        subprocess.run(find_command, shell=True, check=True, stdout=fd, stderr=subprocess.PIPE)
        fd.close()
    except subprocess.CalledProcessError as error:
        error_message = error
        #os.remove("file_paths.txt")
        return (1, error_message)

    error, file_content = read_file("file_paths.txt")
    check_exit_with_error(error, file_content)

    files = file_content.splitlines()
    files = [os.path.abspath(file) for file in files]
    #os.remove("file_paths.txt")
    return (0, files)

def find_keywords_by_grep(keyword, search_dir):
    find_command = f'grep "{keyword}" -rl {search_dir}'
    try: # find files containing a given keyword
        fd = open("grep_result.txt", "w")
        subprocess.run(find_command, shell=True, check=True, stdout=fd, stderr=subprocess.PIPE)
        fd.close()
    except subprocess.CalledProcessError as error:
        error_message = error
        #os.remove("grep_result.txt")
        return (0, [])
        return (1, error_message)

    error, file_content = read_file("grep_result.txt")
    check_exit_with_error(error, file_content)

    files = file_content.splitlines()
    files = [os.path.abspath(file) for file in files]
    #os.remove("grep_result.txt")
    return (0, files)

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

def copy_blocking_files_into_correct_path(data_files, destination_paths, search_dir):
    for indx in range(len(data_files)):
        data_file_name = data_files[indx]
        destination_path = destination_paths[indx]
        error, files = find_file(data_file_name, search_dir)
        check_exit_with_error(error, files)

        for file in files:
            print(file)
            try: 
                shutil.copy(file, destination_path)
            except Exception as error:
                pass
    print("copy_blocking_files_into_correct_path")

def is_number(s):
    try: float(s); return True
    except ValueError: return False

def get_cmake_lists(branch_dir):
    cmake_lists = branch_dir + os.sep + "CMakeLists.txt"
    if os.path.exists(cmake_lists):
        return (0, cmake_lists)
    else: return (1, f"No CMakeLists.txt is in {branch_dir}!")

def check_csv_columns(file_path):
    data_frame = pandas.read_csv(file_path)
    if data_frame.empty: return 0
    else: return 1

def clone_repository(url):
    error_message = None
    try: # clone the repository of the given url
        clone_command = f"git clone --recursive {url}"
        subprocess.run(clone_command, shell=True, check=True,
                stderr=subprocess.PIPE, stdout=subprocess.PIPE)
    except subprocess.CalledProcessError as error:
        error_message = error
        return (1, error_message)
    return (0, error_message)

def create_branches(project_dir):
    wasm_branch = project_dir + "-wasm"
    x86_branch = project_dir + "-x86"
    analysis_branch = project_dir + "-analysis"
    if os.path.isdir(wasm_branch):
        shutil.rmtree(wasm_branch)
    if os.path.isdir(x86_branch):
        shutil.rmtree(x86_branch)
    if os.path.isdir(analysis_branch):
        shutil.rmtree(analysis_branch)
    shutil.copytree(project_dir, x86_branch)
    shutil.copytree(project_dir, wasm_branch)
    shutil.copytree(project_dir, analysis_branch)
    return (wasm_branch, x86_branch, analysis_branch)
