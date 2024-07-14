from Config import*
from Utility import*

def run_tests(WASM=False):
    test_command = "make test"
    if WASM: test_command = "emmake " + test_command
    try: # run make test to get tests outputs
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

def enable_testing(file_path, test_flag):
    error, file_content = read_file(file_path)
    check_exit_with_error(error, file_content)

    pattern = r"add_subdirectory\(test(.*)"
    matched = re.search(pattern, file_content, re.IGNORECASE)
    if matched:
        str_match = matched.group()
        new_file_content = file_content.replace(str_match,
                os.linesep + "enable_testing()" + os.linesep + str_match)
        error, error_message = write_file(file_path, new_file_content)
        check_exit_with_error(error, error_message)
        return

    pattern = f"if\s*\(\s*{test_flag}\s*\)(.*)"
    matched = re.search(pattern, file_content, re.IGNORECASE)
    if matched:
        str_match = matched.group()
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

    if matched: # add --timeout to tests
        str_match = matched.group(1)
        new_str_match = "--timeout " + timeout + " " + str_match
        new_file_content = file_content.replace(str_match, new_str_match)
        error, error_message = write_file(make_file, new_file_content)
        check_exit_with_error(error, error_message)
    else: return (1, "could not set timeout")
    return (0, None)

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
            executable_file = executable_body[1].split()[0]
            add_test = f"add_test(NAME {executable_file} COMMAND {executable_file})"
            new_file_content = new_file_content.replace(executable_body[0], 
                    executable_body[0] + os.linesep + add_test)
            error, error_message = write_file(file_path, new_file_content)
            check_exit_with_error(error, error_message)
    print("check tests returned successfully!")

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

def check_test_availability(file_content):
    lines = file_content.split("\n")

    no_test_message = "No tests were found!!!"
    if no_test_message in lines:
        return (1, no_test_message)
    else: return (0, None)

def add_test_for_executables(branch_dir):
    error, files = find_file("CMakeLists.txt", branch_dir)
    check_exit_with_error(error, files)

    for file in files:
        check_tests(file)
    print("add_test_for_executables returned successfully!")

def extract_failed_tests(text):
    lines = text.split('\n')
    in_failed_section = False
    failed_tests = []
    for line in lines:
        if "The following tests FAILED:" in line:
            in_failed_section = True
            continue
        if in_failed_section:
            if line.strip() == '': break
            test_name = line.split(" - ")
            test_name = " - ".join(test_name[1:])
            test_name = test_name.split(" (")
            test_name = " ( ".join(test_name[:-1])
            failed_tests.append(test_name)
    return failed_tests

def differentiate(failed_tests1, failed_tests2):
    set1 = set(failed_tests1)
    set2 = set(failed_tests2)
    # find elements that are only in one of the sets using symmetric difference
    unique_elements = set1.symmetric_difference(set2)
    return list(unique_elements)


