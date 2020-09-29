import argparse

parser = argparse.ArgumentParser()

parser.add_argument('input_file')

validation_result = parser.parse_args().input_file

with open(validation_result) as f:
    lines = f.readlines()
    if not lines:
        print("Output of Validation was empty, cannot deduce result.")
        exit(1)
    _exit_code = int(lines[0])
    _msg = '' if len(lines) == 1 else lines[1]

if _exit_code == 0:
    print("Timetable Validation Passed Successfully")
    exit(0)
else:
    print("Timetable Validation Failed.")
    if _msg:
        print("Validation returned: {}".format(_msg))
    exit(1)
