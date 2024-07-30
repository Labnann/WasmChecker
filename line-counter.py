import os
import pandas as pd

suffix = set()
def count_lines_of_code(directory):
    total_lines = 0
    for root, dirs, files in os.walk(directory):
        for file in files: # If the file has intended extensions
            if (file.endswith('.c') or file.endswith('.cpp') or file.endswith('.h') or file.endswith('.hpp') 
            or file.endswith('.t') or file.endswith('.tt') or file.endswith('.tpp') or file.endswith('.cc') or file.endswith('.hh') or file.endswith('.cxx') or file.endswith('.hxx')):
                file_path = os.path.join(root, file)
                try: # Read file and count its lines
                    f = open(file_path, 'r')
                    lines = [line for line in f if line.strip()]
                    total_lines += len(lines)
                except UnicodeDecodeError: pass
            else: # If the file is additional materials in the repo
                fname, extension = os.path.splitext(file)
                suffix.add(extension)
    return total_lines

# Read the CSV file into a DataFrame
df = pd.read_csv("codebases.csv", header=None)
df.columns = ['project','test-flag']

# Iterate through each project name in the 'project' column
for index, row in df.iterrows():
    url = row['project']
    flag = row['test-flag']
    project = url.split('/')[-1]
    directory = "./codebases" + os.sep + project
    df.loc[index, 'loc'] = count_lines_of_code(directory)

df.to_csv("codebases-with-loc.csv")
