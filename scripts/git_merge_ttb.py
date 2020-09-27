#!/usr/bin/env python3
import os
import subprocess
import tabulate
import git
import sys

import glob
from typing import List, Optional, Dict


class GitTTBException(Exception):
    def __init__(self, message):
        Exception.__init__(self, message)


class GitRepo(object):
    def __init__(self, files_list: List[str] = ['test.ttb'],
                 directory_name: str = 'temp_git'):
        self._root = os.getcwd()
        self._files = files_list
        self._dir_name = directory_name

    def __enter__(self):
        os.mkdir(self._dir_name)
        os.chdir(self._dir_name)
        subprocess.call(['git', 'init'],
                         stdout=open(os.devnull, 'wb'))
        return self

    def __exit__(self, *args, **kwargs):
        os.chdir(self._root)
        subprocess.call(['rm', '-rf', self._dir_name],
                         stdout=open(os.devnull, 'wb'))

    def switch_branch(self, branch_name, new=False):
        _args = ['git', 'checkout']
        if new:
            _args += ['-b']
        _args += [branch_name]
        subprocess.call(_args, stdout=open(os.devnull, 'wb'))

    def merge(self, branch_to_merge):
        subprocess.call(['git', 'merge', branch_to_merge])

    def get_conflicts(self, branch_name) -> bool:
        for f in self._files:
            with open(f) as F:
                _lines = F.readlines()
                if '<<<<' not in ''.join(_lines):
                    return False
                _sections = []
                _part = []
                _lines_str = []
                for line in _lines:
                    if '<<<' in line:
                        continue
                    elif '====' in line:
                        _part.append('\n'.join(_lines_str))
                        _lines_str = []
                    elif '>>>' in line:
                        _part.append('\n'.join(_lines_str))
                        _sections.append(_part)
                    else:
                        _lines_str.append(line)
                print(tabulate.tabulate(_sections,
                                        headers = ['master', branch_name],
                                        tablefmt='fancy_grid'))
                return True

    def get_result(self) -> List[str]:
        _results = []

        for f in self._files:
            with open(f) as F:
                _results.append(F.readlines())
        return _results

    def commit(self, message, include='*.ttb'):
        subprocess.call(['git', 'add', include],
                         stdout=open(os.devnull, 'wb'))
        subprocess.call(['git', 'commit', '-m', message],
                         stdout=open(os.devnull, 'wb'))

class GitTTBMerge(object):
    def __init__(self, ttb_file: str):
        self._repository = git.Repo(os.getcwd())
        self._current_branch = self._repository.active_branch.name
        self._ttb_file = ttb_file
        self._check_latest_commit_automated()

    def _count_ttb_commits(self, branch_name: Optional[str] = None):
        if branch_name:
            subprocess.call(['git', 'checkout', branch_name])
        count = subprocess.check_output(['git log', '--follow -- ' +
                                        self._ttb_file],
                                        text=True, shell=True)
        count = sum('Date: ' in i for i in count.split('\n'))
        if branch_name:
            subprocess.call(['git', 'checkout', self._current_branch],
                            stdout=open(os.devnull, 'wb'))
        return int(count)

    def _check_latest_commit_automated(self):
        _user = subprocess.check_output("git log -1 --pretty=format:'%an'",
                                        text=True)
        if _user == "Automated Commit: ROS CI":
            print("Latest commit is automated, cancelling run.")
            exit(0)

    def _unpack_ttb(self) -> str:
        if not os.path.exists(self._ttb_file):
            raise FileNotFoundError("Could not find file '" +
                                    self._ttb_file + "' on branch '" +
                                    self._current_branch + "'.")

        with open(self._ttb_file) as f:
            _line = f.readlines()[0]

        _lines = '\n'.join([i+'NULL' for i in _line.split('\x00')])

        return '\n'.join([i+'COMMA' for i in _lines.split(',')])

    def _get_source_node_commit(self,
                                master_branch: Optional[str] = 'master') -> str:
        _commit_id = subprocess.check_output(['git',
                                              'merge-base',
                                              master_branch,
                                              self._current_branch], text=True,
                                              )
        return _commit_id.replace('\n', '')

    def _checkout_commit_to_branch(self,
                                   commit_sha_id: str,
                                   branch_name: Optional[str] = 'temp_branch'
                                   ) -> None:
        print("Checking out diverging point commit with id: " +
                          commit_sha_id)
        self._repository.git.checkout(commit_sha_id, b=branch_name)
        subprocess.call(['git', 'checkout', self._current_branch],
                        stdout=open(os.devnull, 'wb'))

    def _get_version(self, branch_name: Optional[str] = None) -> List[str]:
        if branch_name:
            subprocess.call(['git', 'checkout', branch_name],
                            stdout=open(os.devnull, 'wb'))
        _version = self._unpack_ttb()
        if branch_name:
            subprocess.call(['git', 'checkout', self._current_branch],
                            stdout=open(os.devnull, 'wb'))
        return _version

    def _rebuild(self, output_str: str):
        output_str = output_str.replace('NULL', '\x00').replace('COMMA', ',')
        return output_str

    def attempt_merge(self):
        self._checkout_commit_to_branch(self._get_source_node_commit())
        _versions = {
            "master": self._get_version('master'),
            "dev": self._get_version(),
            "fork": self._get_version('temp_branch')
        }

        _return_status = 0

        with GitRepo() as g:
            with open('temp.ttb', 'w') as f:
                f.write(_versions['fork'])
                
            g.commit('Initial version before divergence')

            g.switch_branch('dev', new=True)

            with open('temp.ttb', 'w') as f:
                f.write(_versions['dev'])
            
            g.commit('Development updates applied')

            g.switch_branch('master')

            with open('temp.ttb', 'w') as f:
                f.write(_versions['master'])

            g.commit('Master branch updates applied')

            g.merge('dev')

            _output = g.get_result()[0]

            _return_status = g.get_conflicts(self._current_branch)

        subprocess.call(['git', 'branch', '-D', 'temp_branch'],
                        stdout=open(os.devnull, 'wb'))


        if _return_status == 0:
            with open(self._ttb_file, 'w') as f:
                print("Writing new file: ")
                f.write(self._rebuild(_output))
                print("Setting Git Name: ")
                subprocess.call(['git', 'config', '--global', 'user.name',
                                 '"Automated Commit: ROS CI"'])
                subprocess.call(['git', 'config', '--global', 'user.email',
                                 'noreply@unreal-email.com'])
                subprocess.call(['git', 'add', '-u'], stdout=open(os.devnull, 'wb'))
                print("Committing: ")
                subprocess.call(['git', 'commit', '-m',
                                 '"Automated Commit: Merge of file ' +
                                 '\'{}\' from branch \'{}\'"'.format(self._ttb_file,
                                                     self._current_branch)])
                subprocess.call(['git', 'log', '-1'])
                subprocess.call(['git', 'push', 'origin', self._current_branch],
                                stdout=open(os.devnull, 'wb'))

        sys.exit(_return_status)
         

if __name__ in "__main__":
    import argparse

    parser = argparse.ArgumentParser()

    parser.add_argument('--ttb-path', help='Location of ttb files',
                        default = '*')

    _loc = parser.parse_args().ttb_path

    for f in glob.glob(os.path.join(_loc, '*.ttb')):
        print("Processing file '{}':".format(f))
        GitTTBMerge(f).attempt_merge()