from source import Utility
from source import StaticAnalysis
from source import Transformer
from source import BuildCodebase
from source import Testing
import argparse

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    pgroup = parser.add_mutually_exclusive_group(required=True)
    pgroup.add_argument("-u", "--url", help="url to download the codebase", required=False)
    pgroup.add_argument("-p", "--path", help="path to the codebase", required=False)
    parser.add_argument("-t", "--test", help="tests flag", required=False)
    parser.add_argument("-d", "--data", nargs="+", help="preload data", required=False)
    parser.add_argument("-o", "--timeout", help="tests timeout", required=False)
    parser.add_argument("-i", "--inputfile", help="additional build commands", required=False)
    args = parser.parse_args()

    if args.url: 
        if validators.url(args.url):
            project_dir = os.getcwd() + os.sep + args.url.split("/")[-1]
        else: print(f"{args.url} is not a valid url for codebase!"); exit(0)

    if args.path: 
        if os.path.exists(args.path):
            project_dir = os.path.abspath(args.path)
        else: print(f"{args.path} is not a valid path for codebase!"); exit(0)

    if args.test: test_flag = args.test
    else: test_flag = None

    if args.data: user_defined_vfs_data = args.data
    else: user_defined_vfs_data = []

    if args.inputfile and os.path.exists(args.inputfile): 
        build_instruction_file = os.path.abspath(args.inputfile)
    else: build_instruction_file = None

    if args.timeout:
        timeout = args.timeout
    else: timeout = None
    
    with alive_bar(6, title='Processing', length=20, bar='blocks', spinner='twirls') as bar:

        if args.url:
            print("[bold magenta]Cloning Codebase[/bold magenta]")
            if os.path.isdir(project_dir): shutil.rmtree(project_dir)
            error, error_message = clone_repository(args.url)
            check_exit_with_error(error, error_message)
        else: print("[bold magenta]Codebase Is Ready[/bold magenta]")
        bar() # the given codebase is ready for differential testing
        
        # create two branches: one for WebAssembly and the other for native x86-64 binary
        wasm_branch, x86_branch, analysis_branch = create_branches(project_dir)
        
        # locate the CMakeLists.txt file for building the codebase in two binaries
        error, wasm_branch_cmake_lists = get_cmake_lists(wasm_branch)
        check_exit_with_error(error, wasm_branch_cmake_lists)

        error, x86_branch_cmake_lists = get_cmake_lists(x86_branch)
        check_exit_with_error(error, x86_branch_cmake_lists)
        
        print("[bold magenta]Analyzing Codebase[/bold magenta]")

        # run predefined CodeQL queries to extract code construcsts
        error, flags_map = run_codeql(analysis_branch, 
                "/home/sara/WasmChecker/TESTFILE/queries", test_flag)

        if error: # set default settings if CodeQL cannot analyze the codebase
            flags_map = {}
            flags_map['include-pthread'] = 0
            flags_map['threading'] = 1
            flags_map['exception-catching'] = 1
            flags_map['function-pointer'] = 0
            flags_map['long-double'] = 1
         
        # automatically extract files and directories needed to be preloaded in the VFS
        vfs_data = extract_strings_from_files(wasm_branch)
        
        # transformer add settings for preloading files and directories
        for data in vfs_data:
            set_comiple_flag(wasm_branch_cmake_lists, "--preload-file " + data)
        
        for data in user_defined_vfs_data:
            set_comiple_flag(wasm_branch_cmake_lists, "--preload-file " + data)

        # transformer sets required flags based on the CodeQL table outputs
        add_necessary_flags(wasm_branch_cmake_lists, flags_map)
        
        # transformer applies general alterations 
        # (e.g., setting memory size, removing incompatible flags, removing Werror, etc) 
        transform(wasm_branch)

        bar() # static analysis and transformation are done!

        print("[bold green]Building Codebase in WebAssembly[/bold green]")

        # build the codebase in WebAsembly using Emscripten compiler toolchain
        build_codebase_in_WebAssembly(wasm_branch, test_flag, build_instruction_file, timeout)

        bar() # the build process in WebAssembly was successful
        
        print("[bold red]Running Tests in WebAssembly[/bold red]")

        loop_flag = False
        previous_list = list()
        while (not loop_flag):
            error, log_file = run_tests(WASM=True)
            if error: # an error happened when running tests
                if log_file: # tests are available and at least one test failed
                    error, file_content = read_file(log_file)
                    check_exit_with_error(error, file_content)
                    data_frame = find_blocking_tests(log_file)
                    pattern = r"open '([^']*)'"
                    filtered = data_frame[data_frame["output"].str.contains("Error: ENOENT", case=False, na=False)]
                    if filtered.empty: # check if the log file has any problem regarding input files access
                        loop_flag = True
                        print("I made flag true and there is at least one failing test case!")
                    else: # it needs to copy the input files in the correct path where tests are getting executed
                        filtered["file_name"] = filtered["output"].str.extract(pattern, expand=False)
                        if filtered["file_name"].tolist() == previous_list:
                            loop_flag = True
                            print("I made flag true and there is at least one failing test case!")
                        else: # it needs to copy the input files in the correct path where tests are getting executed
                            copy_blocking_files_into_correct_path(
                                    filtered["file_name"].tolist(), filtered["directory"].tolist(), wasm_branch)
                            lst_list = filtered["file_name"].tolist()
                            # the tests need to be executed again to have correct tests outcomes
                else: # no target for test, should enable testing
                    enable_testing(wasm_branch_cmake_lists, test_flag)
                    enable_testing(x86_branch_cmake_lists, test_flag)
                    build_codebase_in_WebAssembly(wasm_branch, test_flag, build_instruction_file, timeout)
                    print("I enabled testing option and built the codebase again")
            else: # no error happened when running tests
                error, file_content = read_file("command.txt")
                check_exit_with_error(error, file_content)
                error, error_message = check_test_availability(file_content)
                if error == 1: # tests are not available, need to be added
                    add_test_for_executables(wasm_branch)
                    add_test_for_executables(x86_branch)
                    build_codebase_in_WebAssembly(wasm_branch, test_flag, build_instruction_file, timeout)
                    print("I added tests and built the codebase again")
                else: # tests passed successfully
                    log_file = "Testing/Temporary/LastTest.log"
                    error, file_content = read_file(log_file)
                    check_exit_with_error(error, file_content)
                    data_frame = find_blocking_tests(log_file)
                    pattern = r"open '([^']*)'"
                    filtered = data_frame[data_frame["output"].str.contains("Error: ENOENT", case=False, na=False)]
                    if filtered.empty: # check if the log file has any problem regarding input files access
                        loop_flag = True
                        print("I made flag true since all the tests passed and everything is done!")
                    else: # it needs to copy the input files in the correct path where tests are getting executed
                        filtered["file_name"] = filtered["output"].str.extract(pattern, expand=False)
                        copy_blocking_files_into_correct_path(
                                filtered["file_name"].tolist(), filtered["directory"].tolist(), wasm_branch)
                        # the tests need to be executed again to have correct tests outcomes
        
        # get the tests outcomes for WebAsembly binary
        error, wasm_test_result = read_file("test_command.txt")
        check_exit_with_error(error, wasm_test_result)
        bar() # the tests outcomes in WebAssembly is ready!
        
        print("[bold green]Building Codebase in x86[/bold green]")
        build_project(x86_branch, test_flag, build_instruction_file, WASM=False)
        bar() # the build process in native x86-64 binary was successful

        print("[bold red]Running Tests in x86[/bold red]")
        error, log_file = run_tests(WASM=False)

        # get the tests outcome for native x86-64 binary
        error, x86_test_result = read_file("test_command.txt")
        check_exit_with_error(error, x86_test_result)
        bar() # the tests outcomes in native x86-64 is ready!
        
        # extract failed tests for each binary
        wasm_failed_tests = extract_failed_tests(wasm_test_result)
        x86_filed_tests = extract_failed_tests(x86_test_result)
        
        print(wasm_test_result)
        print(x86_test_result)
        
        # get differential results
        diff = differentiate(wasm_failed_tests, x86_filed_tests)
        num = len(diff)
        print(f"[bold blue] Tests with Different Results {num} [/bold blue]")
        print(diff)
