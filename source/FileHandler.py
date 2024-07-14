import os

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

