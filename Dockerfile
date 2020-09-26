FROM ubuntu:latest
RUN apt update -y
RUN apt upgrade -y
RUN apt install python3 python3-pip git -y
RUN python3 -m pip install gitpython tabulate typing
COPY scripts/git_merge_ttb.py /usr/bin/git_merge_ttb