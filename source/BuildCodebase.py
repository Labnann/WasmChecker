from Testing import*
from Transformer import*
from Config import*
from Utility import*

def build_project(project_dir, test_flag, build_instruction_file=None, WASM=False):    
    curr_dir = os.getcwd()
    os.chdir(project_dir)
    os.makedirs("build", exist_ok=True)
    os.chdir("build")
    
    if test_flag: cmake_command = f"cmake -D{test_flag}=ON .."
    else: cmake_command = f"cmake .."

    if WASM: cmake_command = "emcmake " + cmake_command

    try: # run cmake to configure the build with the TEST_FLAG
        fd = open("command.txt", "w")
        subprocess.run(cmake_command, shell=True, check=True, stderr=fd, stdout=subprocess.PIPE)
        fd.close()
    except subprocess.CalledProcessError as error:
        log_file = cmake_log
        print(f"cmake error: {error}")
        matched_error_line = get_first_error("Could NOT find", "command.txt")
        library = matched_error_line.split(' ')[0].upper()
        print("could not find ", library)
        os.remove("CMakeCache.txt")
        log_text = "Error: " + matched_error_line + " happend when running " + cmake_command
        error, error_message = modify_file(log_file, log_text)
        check_exit_with_error(error, error_message)
        print("running cmake failed!***")
        return (1, library)

    if WASM:
        error, files = find_keywords_by_grep("Werror", project_dir)
        for file in files:
            modify_troublesome_flags(file)

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
        log_file = build_log
        print(f"build error: {error}")
        matched_error_line = get_first_error("error:", "command.txt")
        print(matched_error_line)
        log_text = "Error: " + matched_error_line + " happend when running " + make_command
        error, error_message = modify_file(log_file, log_text)
        check_exit_with_error(error, error_message)
        print("running make check failed!***")

    if build_instruction_file == None: return (0, None)

    error, file_content = read_file(build_instruction_file)
    check_exit_with_error(error, file_content)

    commands = file_content.splitlines()

    for command in commands:
        print(f"I'm going to execute {command}")
        if command.startswith("make") and WASM:
            command = "emmake " + command
        print("I'm running " + command)
        try: # run additional commands to completely build the project and tests
            fd = open("command.txt", "w")
            subprocess.run(command, shell=True, check=True, stderr=fd, stdout=subprocess.PIPE)
            fd.close()
        except subprocess.CalledProcessError as error:
            log_file = build_log
            print(f"build error: {error}")
            matched_error_line = get_first_error("error:", "command.txt")
            log_text = "Error: " + matched_error_line + " happend when running " + command
            error, error_message = modify_file(log_file, log_text)
            check_exit_with_error(error, error_message)

    # change to the initial directory
    # os.chdir(curr_dir)
    return (0, None)

def build_codebase_in_WebAssembly(wasm_branch, test_flag, build_instruction_file, timeout=None):
    loop_flag = False
    while (not loop_flag):
        error, library = build_project(wasm_branch, test_flag, build_instruction_file, WASM=True)
        if error:
            flag = add_supporting_headers(library)
            if flag != "_empty_":
                error, wasm_branch_cmake_lists = get_cmake_lists(wasm_branch)
                check_exit_with_error(error, wasm_branch_cmake_lists)
                set_comiple_flag(wasm_branch_cmake_lists, "-s" + flag)
            elif library.startswith("max-func-params needs to be at least"):
                error, wasm_branch_cmake_lists = get_cmake_lists(wasm_branch)
                check_exit_with_error(error, wasm_branch_cmake_lists)
                disable_comiple_flag(wasm_branch_cmake_lists, "-sEMULATE_FUNCTION_POINTER_CASTS=1")
            elif library.startswith("--preload-file and --embed-file cannot be used"):
                error, wasm_branch_cmake_lists = get_cmake_lists(wasm_branch)
                check_exit_with_error(error, wasm_branch_cmake_lists)
                print("I'm going to remove --preload-file")
                disable_comiple_flag(wasm_branch_cmake_lists, "--preload-file")
            else: exit(0)
        else: loop_flag = True

    error, files = find_file("CTestTestfile.cmake", wasm_branch)
    check_exit_with_error(error, files)

    for file in files:
        modify_CTestTestfile(file, wasm_branch)

    if timeout and timeout.isdigit(): # check if timeout is a number
        make_file = wasm_branch + os.sep + "build" + os.sep + "Makefile"
        error, error_message = set_test_timeout(timeout, make_file)
        #check_exit_with_error(error, error_message)
    print("build_codebase_in_WebAssembly returned successfully!")

def modify_CTestTestfile(file_path, project_path):
    pattern = r"add_test\(\s*(.*)\s*\)"
    error, file_content = read_file(file_path)
    check_exit_with_error(error, file_content)

    matched = re.findall(pattern, file_content)
    for match_str in matched:
        test_matches = re.findall(r'"([^"]+)"|\S+', match_str)
        test_name = re.findall(r'^([^"\s]+)', match_str)
        if len(test_name) > 0:
            test_name = test_name[0]
        else:
            test_name = '"' + test_matches[0] + '"'
        test_args = test_matches[1:]
        end_parts = [os.path.basename(s) for s in test_args]
        
        if "node" in end_parts and any(s.endswith(".js") for s in end_parts): continue
        elif "node" in end_parts:
            index = end_parts.index("node")
            new_str = test_name
            for s in test_args:
                if test_args.index(s) == index + 1:
                    if not os.path.exists(s + ".js"):
                        error, f = find_file(end_parts[test_args.index(s)] + ".js", project_path)
                        check_exit_with_error(error, f)
                        if (len(f) > 0): s = f[0][:-3]
                    new_str += " " + '"' + s + ".js" + '"'
                else: new_str += " " + '"' + s + '"'

            file_content = file_content.replace(match_str, new_str)
            error, error_message = write_file(file_path, file_content)
            check_exit_with_error(error, error_message)

        elif any(s.endswith(".js") for s in end_parts):
            new_str = test_name
            for s in test_args:
                if s.endswith(".js"):
                    if not os.path.exists(s):
                        error, f = find_file(end_parts[test_args.index(s)], project_path)
                        check_exit_with_error(error, f)
                        if (len(f) > 0): s = f[0]
                    new_str += " " + '"' + emsdk_node + '"' + " " + '"' + s + '"'
                else: new_str += " " + '"' + s + '"'

            file_content = file_content.replace(match_str, new_str)
            error, error_message = write_file(file_path, file_content)
            check_exit_with_error(error, error_message)

        elif len(end_parts) == 1:
            if not os.path.exists(test_args[0] + ".js"):
                error, f = find_file(end_parts[0] + ".js", project_path)
                check_exit_with_error(error, f)
                if (len(f) > 0): test_args[0] = f[0][:-3]
            new_str = test_name + " " + '"' + emsdk_node + '"' + " " + '"' + test_args[0] + ".js" + '"'
            file_content = file_content.replace(match_str, new_str)
            error, error_message = write_file(file_path, file_content)
            check_exit_with_error(error, error_message)

        else: # test arguments are more than one
            new_str = test_name
            for s in test_args:
                if os.path.exists(s + ".js"):
                    new_str += " " + '"' + emsdk_node + '"' + " " + '"' + s + ".js" + '"'
                else: new_str += " " + '"' + s + '"'
            file_content = file_content.replace(match_str, new_str)
            error, error_message = write_file(file_path, file_content)
            check_exit_with_error(error, error_message)
