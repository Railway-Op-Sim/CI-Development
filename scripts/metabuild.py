#!/usr/bin/env python3

import argparse
import datetime
import toml
import semver
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

metadata = toml.load(data_file) if os.path.exists(data_file) else {}
if 'rly_file' not in metadata:
    metadata['rly_file'] = f'{rly_name}.rly'

if 'ttb_files' not in metadata:
    ttb_files = glob.glob(os.path.join(proj_dir, 'Program_Timetables', '*.ttb'))
    if not ttb_files:
        logger.info("No timetable files were found.")
        metadata['ttb_files'] = []
    elif 'ttb_files' not in metadata or not metadata['ttb_files']:
        metadata['ttb_files'] = [os.path.basename(t) for t in ttb_files]
        logger.info(f"Found timetable files {metadata['ttb_files']}")

if 'ssn_files' not in metadata:
    ssn_files = glob.glob(os.path.join(proj_dir, 'Sessions', '*.ssn'))
    if not ssn_files:
        logger.info("No session files were found.")
        metadata['ssn_files'] = []
    elif 'ssn_files' not in metadata or not metadata['ssn_files']:
        metadata['ssn_files'] = [os.path.basename(s) for s in ssn_files]
        logger.info(f"Found session files {metadata['ssn_files']}")

if 'graphic_files' not in metadata:
    graphic_files = glob.glob(os.path.join(proj_dir, 'Graphics', '*'))
    if not graphic_files:
        logger.info("No graphic files were found.")
        metadata['graphic_files'] = []
    elif 'graphic_files' not in metadata or not metadata['graphic_files']:
        metadata['graphic_files'] = [os.path.basename(s) for s in graphic_files]
        logger.info(f"Found graphic files {metadata['graphic_files']}")
        if 'minimum_required' not in metadata:
            metadata['minimum_required'] = '2.4.0'

if 'img_files' not in metadata:
    img_files = glob.glob(os.path.join(proj_dir, 'Images', '*'))
    if not img_files:
        logger.info("No image files were found.")
        metadata['img_files'] = []
    elif 'img_files' not in metadata or not metadata['img_files']:
        metadata['img_files'] = [os.path.basename(s) for s in img_files]
        logger.info(f"Found image files {metadata['img_files']}")

if 'doc_files' not in metadata:
    doc_files = glob.glob(os.path.join(proj_dir, 'Documentation', '*'))
    if not doc_files:
        logger.info("No doc files were found.")
        metadata['doc_files'] = []
    elif 'doc_files' not in metadata or not metadata['doc_files']:
        metadata['doc_files'] = [os.path.basename(s) for s in doc_files]
        logger.info(f"Found doc files {metadata['doc_files']}")

if 'release_date' not in metadata:
    release = datetime.datetime.now().strftime("%Y-%m-%d")
    logger.info("Setting release date to '{release}'")
    metadata['release_date'] = release

if 'factual' not in metadata:
    metadata['factual'] = metadata['country_code'] not in ('FN', 'UN')


def get_version():
    p = subprocess.Popen(['git', 'describe', '--abbrev=0', '--tags'], cwd=proj_dir,
                         stdout=subprocess.PIPE, encoding='UTF-8')
    p.wait()
    if p.returncode != 0:
        retrieved = None
    else:
        version = p.communicate()
        retrieved, _ = version
        retrieved = retrieved.strip()

    version_current = metadata.get("version", None)

    if version_current:
        try:
            semver_current = semver.VersionInfo(version_current)
        except ValueError:
            logger.error("Current version tag is not a valid semantic version, setting to 1.0.0")
            metadata["version"] = "1.0.0"
            return
    if retrieved:
        try:
            semver_retr = semver.VersionInfo(retrieved)
        except ValueError:
            logger.error("Retrieved version tag is not a valid semantic version, using current")
            metadata["version"] = version_current
            return

    if version_current and retrieved:
        if semver_retr > semver_current:
            metadata["version"] = retrieved
        else:
            metadata["version"] = version_current
        return
    else:
        logger.error("No version tag set, using 1.0.0")
        metadata["version"] = "1.0.0"

get_version()


if re.findall(r'^(\w{2})\-', repo_name) and 'country_code' not in metadata:
    metadata['country_code'] = re.findall(r'^(\w{2})\-', repo_name)[0].upper()
    logger.info(f"Found country code '{metadata['country_code']}'")


if 'description' not in metadata:
    metadata['description'] = ""

if 'display_name' not in metadata:
    metadata['display_name'] = repo_name.split('-', 1)[1].replace('-', ' ').title()
    logger.info(f"Set display name '{metadata['display_name']}'")

if 'name' not in metadata:
    metadata['name'] = metadata['display_name']

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

if "contributors" not in metadata:
    metadata["contributors"] = []


with open(data_file, 'w', encoding="utf-8") as out_f:
    toml.dump(metadata, out_f)

logger.info(f"Metadata written to '{os.path.join('$REPO_ROOT', 'Metadata', os.path.basename(data_file))}'")
