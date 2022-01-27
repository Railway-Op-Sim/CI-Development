FROM ubuntu:latest
RUN apt update -y
RUN apt upgrade -y
RUN apt install python3 python3-pip git -y
RUN python3 -m pip install gitpython tabulate typing toml semver
COPY scripts/git_merge_ttb.py /etc/git_merge_ttb
COPY scripts/metabuild.py /etc/metabuild
RUN chmod +x /etc/git_merge_ttb
RUN chmod +x /etc/metabuild
RUN ln -s /etc/git_merge_ttb /usr/bin/git_merge_ttb
RUN ln -s /etc/metabuild /usr/bin/metabuild
