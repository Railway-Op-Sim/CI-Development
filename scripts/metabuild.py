#!/usr/bin/env python3

import argparse
import toml
import glob
import sys
import logging
import subprocess
import os
import re

logging.basicConfig()
logger = logging.getLogger('Metadata Assembler')
logger.setLevel(logging.INFO)

parser = argparse.ArgumentParser()

parser.add_argument('project_directory')
parser.add_argument('--repo-name', help="Name of repository (if not same as folder)", default=None)
parser.add_argument('--debug', help='Run in debug mode', default=False, action='store_true')

args = parser.parse_args()

proj_dir = args.project_directory
repo_name = args.repo_name or os.path.basename(os.path.abspath(proj_dir))

if args.debug:
    logger.setLevel(logging.DEBUG)

if '/' in repo_name:
    repo_name = repo_name.split('/')[-1]

logger.debug(f"Processing: repo_name={repo_name}, proj_dir={proj_dir}")

if not os.path.exists(proj_dir):
    raise FileNotFoundError(f"Cannot create metadata file, directory '{proj_dir}' does not exists")

if not os.path.exists(os.path.join(proj_dir, 'Metadata')):
    os.makedirs(os.path.join(proj_dir, 'Metadata'))
 
rly_files = glob.glob(os.path.join(proj_dir, 'Railway', '*.rly'))
rly_files += glob.glob(os.path.join(proj_dir, 'Railway', '*.dev'))

if not rly_files:
    logger.info("No railway file found aborting.")
    sys.exit(0)
    
rly_name = os.path.splitext(os.path.basename(rly_files[0]))[0]

logger.info(f"Using railway name '{rly_name}'")
 
data_file = os.path.join(proj_dir, 'Metadata', f'{rly_name}.toml')
 
if os.path.exists(data_file):
    metadata = toml.load(data_file)
else:
    metadata = {}
    

if 'rly_file' not in metadata:
    metadata['rly_file'] = f'{rly_name}.rly'
    
if 'ttb_files' not in metadata:
    ttb_files = glob.glob(os.path.join(proj_dir, 'Program_Timetables', '*.ttb'))
    if not ttb_files:
        logger.info("No timetable files were found.")
        metadata['ttb_files'] = []
    elif 'ttb_files' not in metadata or not metadata['ttb_files']:
        metadata['ttb_files'] = [os.path.basename(t) for t in ttb_files]
        logger.info(f"Found timetable files '{metadata['ttb_files']}'")
        
if 'ssn_files' not in metadata:
    ssn_files = glob.glob(os.path.join(proj_dir, 'Sessions', '*.ssn'))
    if not ssn_files:
        logger.info("No session files were found.")
        metadata['ssn_files'] = []
    elif 'ssn_files' not in metadata or not metadata['ssn_files']:
        metadata['ssn_files'] = [os.path.basename(s) for s in ssn_files]
        logger.info("Found session files '{metadata['ssn_files']}'")
        
if re.findall(r'^(\w{2})\-', repo_name) and not 'country_code' in metadata:
    metadata['country_code'] = re.findall(r'^(\w{2})\-', repo_name)[0].upper()
    logger.info(f"Found country code '{metadata['country_code']}'")

if 'name' not in metadata:
    metadata['name'] = ""

if 'description' not in metadata:
    metadata['description'] = ""
    
if 'display_name' not in metadata:
    metadata['display_name'] = repo_name.split('-', 1)[1].replace('-', ' ').title()
    logger.info(f"Set display name '{metadata['display_name']}'")
        
p = subprocess.Popen(['git', 'rev-list', '--max-parents=0', 'HEAD'], cwd=proj_dir, stdout=subprocess.PIPE,
                     encoding='UTF-8')
p.wait()

if p.returncode == 0:
    first_sha, _ = p.communicate()
    p = subprocess.Popen(['git', '--no-pager' ,'show', '-s', '--format="%an"', first_sha.strip()], cwd=proj_dir,
                         stdout=subprocess.PIPE, encoding='UTF-8')
    p.wait()

    if p.returncode == 0:
        author, _ = p.communicate()
        author = author.replace('"', '').strip()

        if 'author' not in metadata:
            metadata['author'] = author

p = subprocess.Popen(['git', 'log', '-1', "--pretty=format:'%an'"], stdout=subprocess.PIPE, cwd=proj_dir,
                     encoding='UTF-8')
p.wait()

if p.returncode == 0:
    latest, _ = p.communicate()
    latest = latest.replace("'", "").strip()

    if latest != author:
        if 'contributors' not in metadata:
            metadata['contributors'] = []
        metadata['contributors'].append(latest)


with open(data_file, 'w', encoding="utf-8") as out_f:
    toml.dump(metadata, out_f)
    
logger.info(f"Metadata written to '{os.path.join('$REPO_ROOT', 'Metadata', os.path.basename(data_file))}'")
