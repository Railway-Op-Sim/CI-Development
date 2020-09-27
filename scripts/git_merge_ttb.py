#!/usr/bin/env python3
import os
import subprocess
import tabulate
import logging
import git
import sys

import glob
from typing import List, Optional, Dict


logging.basicConfig()

class GitTTBException(Exception):
    def __init__(self, message):
        Exception.__init__(self, message)


class GitRepo(object):
    def __init__(self, ttb_file: str = 'temp.ttb',
                 directory_name: str = 'temp_git',
                 temp_user: str = "github-actions",
                 temp_email: str = "github-actions@github.com"):
        self._root = os.getcwd()
        self._user = temp_user
        self._email = temp_email
        self._ttb_file = ttb_file
        self._dir_name = directory_name
        self._logger = logging.getLogger('TempGitRepo')
        self._logger.setLevel('INFO')

    def __enter__(self):
        self._logger.info("Initialising temporary Git repository '%s'", self._dir_name)
        os.mkdir(self._dir_name)
        os.chdir(self._dir_name)
        subprocess.call(['git', 'init'],
                         stdout=open(os.devnull, 'wb'))
        subprocess.call(['git', 'config', 'user.name', self._user],
                        stdout=open(os.devnull, 'wb'))
        subprocess.call(['git', 'config', 'user.email', self._email],
                        stdout=open(os.devnull, 'wb'))
        return self

    def __exit__(self, *args, **kwargs):
        self._logger.info("Closing Git repository and deleting.")
        os.chdir(self._root)
        subprocess.call(['rm', '-rf', self._dir_name],
                         stdout=open(os.devnull, 'wb'))

    def switch_branch(self, branch_name, new=False):
        self._logger.info("Switching to branch '%s'", branch_name)
        _args = ['git', 'checkout']
        if new:
            _args += ['-b']
        _args += [branch_name]
        subprocess.call(_args, stdout=open(os.devnull, 'wb'))

    def merge(self, branch_to_merge):
        self._logger.info("Merging chnges into '%s'", branch_to_merge)
        subprocess.call(['git', 'merge', branch_to_merge])

    def get_conflicts(self, branch_name) -> bool:
        self._logger.info("Finding conflicts after attempted merge")
        with open(self._ttb_file) as F:
            _lines = F.readlines()
            if '<<<<' not in ''.join(_lines):
                self._logger.info("No Conflicts Found")
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
        self._logger.info("Retrieving combined TTB file")
        with open(self._ttb_file) as F:
            return '\n'.join(F.readlines())

    def commit(self, message, include='*.ttb'):
        self._logger.info("Committing changes to local repository")
        subprocess.call(['git', 'add', include],
                         stdout=open(os.devnull, 'wb'))
        subprocess.call(['git', 'commit', '-m', message],
                         stdout=open(os.devnull, 'wb'))

class GitTTBMerge(object):
    def __init__(self, ttb_file: str, branch_name: Optional[str] = None,
                do_not_overwrite: Optional[bool] = False):
        self._no_overwrite = do_not_overwrite
        self._repository = git.Repo(os.getcwd())
        if self._repository.head.is_detached:
            self._checkout_temp()
        self._current_branch = branch_name if branch_name else self._repository.active_branch.name
        if self._current_branch == 'master':
            print("Current branch is 'master', no tests will be run")
            exit(0)
        self._ttb_file = ttb_file
        self._check_latest_commit_automated()
        # self._fetch_master_locally()

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

    def _fetch_master_locally(self, master_branch: Optional[str] = 'master') -> None:
        subprocess.call(['git', 'fetch', 'origin', '{m}:{m}'.format(m=master_branch)])

    def _check_latest_commit_automated(self):
        _user = subprocess.check_output(["git log", "-1 --pretty=format:'%an'"],
                                        text=True, shell=True)
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
                                              self._current_branch], text=True
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

    def _rebuild(self, output_str: str) -> str:
        output_str = output_str.replace('NULL', '\x00').replace('COMMA', ',')
        output_str = output_str.replace('\n','')
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

            _return_status = g.get_conflicts(self._current_branch)

            if _return_status == 0:
                _output = g.get_result()[0]

        subprocess.call(['git', 'branch', '-D', 'temp_branch'],
                        stdout=open(os.devnull, 'wb'))

        if _return_status == 0 and not self._no_overwrite:
            with open(self._ttb_file, 'w') as f:
                f.write(self._rebuild(_output))
                subprocess.call(['git', 'config', 'user.name',
                                 '"github-actions"'])
                subprocess.call(['git', 'config', 'user.email',
                                 'github-actions@github.com'])
                subprocess.call(['git', 'add', '-u'], stdout=open(os.devnull, 'wb'))
                subprocess.call(['git', 'commit', '-m',
                                 '"Automated Commit: Merge of file ' +
                                 '\'{}\' from branch \'{}\'"'.format(self._ttb_file,
                                                     self._current_branch)])
                subprocess.check_output(['git log', '-1'], shell=True)
                subprocess.call(['git', 'push', 'origin', self._current_branch],
                                stdout=open(os.devnull, 'wb'))

        sys.exit(_return_status)
         

if __name__ in "__main__":
    import argparse

    parser = argparse.ArgumentParser()

    parser.add_argument('originbranch', help='Current branch name')
    parser.add_argument('--ttb-path', help='Location of ttb files',
                        default = '*')
    parser.add_argument('--soft', help='Test merge but do not overwrite',
                        action='store_true')

    args = parser.parse_args()

    _branch = args.originbranch
    _loc = args.ttb_path
    _soft = args.soft

    for f in glob.glob(os.path.join(_loc, '*.ttb')):
        print("Processing file '{}':".format(f))
        GitTTBMerge(f, _branch, _soft).attempt_merge()