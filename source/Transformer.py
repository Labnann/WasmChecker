from source.Config import *
from source.Utility import *

def modify_troublesome_flags(file_path):
    error, file_content = read_file(file_path)
    if error: return
    check_exit_with_error(error, file_content)

    file_content = file_content.replace("-fstack-protector", "-fno-stack-protector")
    file_content = file_content.replace("-Werror", "-Wno-error")
    file_content = file_content.replace("-fno-exceptions", "-fexceptions")
    file_content = file_content.replace("-Ofast", "-Oz")
    file_content = file_content.replace("-march", "-mtune")
    file_content = file_content.replace("-mavx2", "-mavx")
    file_content = file_content.replace("-mfma", "-mtune=native")
    file_content = file_content.replace("-mf16c", "-mtune=native")
    file_content = file_content.replace("-save-temps", "-Wno-error")

    pattern = r'(-msse[0-9]+(?:\.[0-9]+)?)'
    replacement = r'\1 -msimd128'
    file_content = re.sub(pattern, replacement, file_content)

    error, error_message = write_file(file_path, file_content)
    check_exit_with_error(error, error_message)

def transform(wasm_branch):
    error, files = find_file("CMakeLists.txt", wasm_branch)
    check_exit_with_error(error, files)
    
    for file in files:
        modify_troublesome_flags(file)
        set_comiple_flag(file, "-sSTACK_SIZE=1MB")
    
    error, files = find_keywords_by_grep("Werror", wasm_branch)
    check_exit_with_error(error, files)
    
    for file in files:
        modify_troublesome_flags(file)
    # print("transform returned successfully!")

def remove_cmake_option(cmake_file, option, flag):
    # remove flags and compiler options
    error, file_content = read_file(cmake_file)
    check_exit_with_error(error, file_content)

    #flag_setting = f'set({option} "${{{option}}} {flag}")'
    #file_content = file_content.replace(flag_setting, "")
    
    flag_setting = re.compile(rf'set\({option} "\${{{option}}} {flag}[^\n]*"\)')
    # print(flag_setting)
    file_content = re.sub(flag_setting, "", file_content)

    error, error_message = write_file(cmake_file, file_content)
    check_exit_with_error(error, error_message)

def add_cmake_option(cmake_file, option, flag):
    # insert flags and compiler options
    error, file_content = read_file(cmake_file)
    check_exit_with_error(error, file_content)

    flag_setting = f'set({option} "${{{option}}} {flag}")'
    
    #file_content = flag_setting + os.linesep + os.linesep + file_content
    lines = file_content.split('\n')
    cmake_minimum = False
    pattern = re.compile(r'cmake_minimum_required', re.IGNORECASE)
    
    # find the line starting with 'cmake_minimum_required' and add the settings after it
    for i, line in enumerate(lines):
        if pattern.search(line.strip()):    
            lines.insert(i + 1, flag_setting)
            cmake_minimum = True; break
    if cmake_minimum:
        file_content = '\n'.join(lines)
    else: file_content = flag_setting + os.linesep + file_content
    
    error, error_message = write_file(cmake_file, file_content)
    check_exit_with_error(error, error_message)

def set_comiple_flag(cmake_file, flag):
    add_cmake_option(cmake_file, "CMAKE_CXX_FLAGS", flag)
    add_cmake_option(cmake_file, "CMAKE_C_FLAGS", flag)

def disable_comiple_flag(cmake_file, flag):
    remove_cmake_option(cmake_file, "CMAKE_CXX_FLAGS", flag)
    remove_cmake_option(cmake_file, "CMAKE_C_FLAGS", flag)

def add_necessary_flags(cmake_lists, flags_map):
    if flags_map['include-pthread']:
        set_comiple_flag(cmake_lists, "-DGTEST_HAS_PTHREAD=1")
    if flags_map['threading'] or flags_map['include-pthread']:
        set_comiple_flag(cmake_lists, "-pthread")
    if flags_map['exception-catching'] or flags_map['include-exception']:
        set_comiple_flag(cmake_lists, "-sNO_DISABLE_EXCEPTION_CATCHING")
    if flags_map['function-pointer']:
        set_comiple_flag(cmake_lists, "-sEMULATE_FUNCTION_POINTER_CASTS=1")
    if flags_map['long-double']:
        set_comiple_flag(cmake_lists, "-sPRINTF_LONG_DOUBLE=1")

    set_comiple_flag(cmake_lists, "-sALLOW_MEMORY_GROWTH")
    set_comiple_flag(cmake_lists, "-Wno-unused-command-line-argument")
    set_comiple_flag(cmake_lists, "-sSTACK_SIZE=1MB -Oz -sINITIAL_MEMORY=1GB")

def add_supporting_headers(library):
    dataframe = pandas.read_csv(header_map, header=None)
    result_map = dataframe.set_index(dataframe.columns[1]).to_dict()[dataframe.columns[0]]
    if library in result_map.keys():
        return result_map[library]
    else: return "_empty_"
