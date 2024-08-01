from source.Config import *
from source.Utility import *

def run_codeql(branch_dir, query_dir, test_flag):
    curr_dir = os.getcwd()
    os.chdir(branch_dir)

    if test_flag: cmake_command = f"cmake -D{test_flag}=ON ."
    else: cmake_command = f"cmake ."

    try: # run cmake to configure the build with the TEST_FLAG
        fd = open("command.txt", "w")
        subprocess.run(cmake_command, shell=True, check=True, stderr=fd, stdout=subprocess.PIPE)
        fd.close()
    except subprocess.CalledProcessError as error:
        log_file = cmake_log
        print(f"build error: {error}")
        matched_error_line = get_first_error("error", "command.txt")
        log_text = "Error: " + matched_error_line + " happend when running " + cmake_command
        error, error_message = modify_file(log_file, log_text)
        check_exit_with_error(error, error_message)
        # print("running cmake failed!***")
        return (1, matched_error_line)

    create_database_command = "codeql database create qldb --language=c-cpp --source-root . --command=make"

    try: # create database from the codebase
        fd = open("command.txt", "w")
        subprocess.run(create_database_command, shell=True, check=True, stderr=fd, stdout=subprocess.PIPE)
        fd.close()
    except subprocess.CalledProcessError as error:
        log_file = build_log
        print(f"build error: {error}")
        matched_error_line = get_first_error("error:", "command.txt")
        # print(matched_error_line)
        log_text = "Error: " + matched_error_line + " happend when running " + create_database_command
        error, error_message = modify_file(log_file, log_text)
        check_exit_with_error(error, error_message)
        return (1, matched_error_line)

    os.makedirs("qlcsv", exist_ok=True)
    # print("I'm going to run codeQL queries!")
    query_files = get_query_files(query_dir)
    flags_map = {}
    for query in query_files:
        query_path = query_dir + os.sep + query
        outcome_path = branch_dir + os.sep + "qlcsv" + os.sep + query[:-3] + ".bqrs"
        query_command = f"codeql query run {query_path} --output={outcome_path} --database=qldb"
        
        try: # run CodeQL query
            fd = open("command.txt", "w")
            subprocess.run(query_command, shell=True, check=True, stderr=fd, stdout=subprocess.PIPE)
            fd.close()
        except subprocess.CalledProcessError as error:
            print(query, "could not be executed!")
        
        csv_path = branch_dir + os.sep + "qlcsv" + os.sep + query[:-3] + ".csv"
        decode_command = f"codeql bqrs decode --output={csv_path} --format=csv {outcome_path}"
        
        try: # decode CodeQL query
            fd = open("command.txt", "w")
            subprocess.run(decode_command, shell=True, check=True, stderr=fd, stdout=subprocess.PIPE)
            fd.close()
            flags_map[query[:-3]] = check_csv_columns(csv_path)
        except subprocess.CalledProcessError as error:
            print(query, "could not be decoded!")
    
    os.chdir(curr_dir)
    return (0, flags_map)

def extract_strings_from_files(branch_dir):
    file_names = []; dir_names = []
    for root, dirs, files in os.walk(branch_dir):
        for file in files:
            # only extract strings from source or test files
            if file.endswith(('.c', '.cpp', '.h', '.hpp', '.cc', '.tpp', '.t', '.hh', 'tt')):
                full_path = os.path.join(root, file)
                file_names.extend(extract_file_paths(full_path))
                dir_names.extend(extract_dir_paths(full_path))

    # exclude strings representing numbers and headers/sources included.
    files = [fname for fname in file_names if (
        not fname.endswith(('.c', '.cpp', '.h', '.hpp', '.cc', '.tpp', '.t', '.hh', '.tt')) 
        and not is_number(fname))]
    
    dirs = [dname for dname in dir_names if (not is_number(dname))]

    preload_data = set()
    for fname in files:
        postfix = fname.split(os.sep)[-1]
        error, paths = find_file(postfix, branch_dir)
        check_exit_with_error(error, paths)
        for full_path in paths:
            preload_str = full_path + "@" + fname
            preload_data.add(preload_str)
            preload_str = full_path + "@" + full_path
            preload_data.add(preload_str)

    grouped_paths = classify_paths(files)
    for prefix, paths in grouped_paths.items():
        if prefix == '': pass
        else: 
            directory = prefix.split(os.sep)[-1]
            if directory == "UsageTests": continue
            error, paths = find_file(directory, branch_dir)
            check_exit_with_error(error, paths)
            for full_path in paths:
                preload_str = full_path + "@" + prefix
                preload_data.add(preload_str)
                preload_str = full_path + "@" + full_path
                preload_data.add(preload_str)
    
    for _dir in dirs:
        postfix = _dir.strip(os.sep).split(os.sep)[-1]
        if postfix == '': pass
        error, paths = find_file(postfix, branch_dir)
        check_exit_with_error(error, paths)
        for full_path in paths:
            preload_str = full_path + "@" + postfix
            preload_data.add(preload_str)

    return preload_data

def get_query_files(directory):
    files = os.listdir(directory)
    files = [f for f in files if f.endswith(".ql")]
    return files

def extract_file_paths(file_path):
    file_path_regex = r'"([a-zA-Z0-9_./\\-]+\.[a-zA-Z0-9]+)"'
    try: # read from a file and return the content
        file = open(file_path, 'r', encoding='utf-8', errors='ignore')
        content = file.read()
        matches = re.findall(file_path_regex, content)
        file.close()
        if matches: return matches
        else: return []
    except Exception as error:
        print(f"error: could not read {file_path}!")
    return []

def extract_dir_paths(file_path):
    dir_path_regex = r'"([a-zA-Z0-9_/-]+)"'
    try: # read from a file and return the content
        file = open(file_path, 'r', encoding='utf-8', errors='ignore')
        content = file.read()
        matches = re.findall(dir_path_regex, content)
        file.close()
        if matches: return matches
        else: return []
    except Exception as error:
        print(f"error: could not read {file_path}!")
    return []

def classify_paths(file_paths):
    # function to extract the directory prefix
    def get_directory_prefix(path):
        parts = path.split('/')
        return '/'.join(parts[:-1])
    path_groups = defaultdict(list)
    # group the file paths by their directory prefix
    for path in file_paths:
        normalized_path = os.path.normpath(path)
        prefix = get_directory_prefix(normalized_path)
        path_groups[prefix].append(normalized_path)
    return dict(path_groups)
