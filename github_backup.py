#!/usr/bin/env python3
import argparse
import json
import logging
import os
import subprocess
import sys

try:
    import urllib.request, urllib.error, urllib.parse
except ImportError:
    import urllib.request as urllib2

def setup_logger():
    logger = logging.getLogger('github_backup')
    logger.setLevel(logging.DEBUG)
    
    stream_handler = logging.StreamHandler()
    stream_formatter = logging.Formatter('%(message)s')
    stream_handler.setFormatter(stream_formatter)
    logger.addHandler(stream_handler)
    
    file_handler = logging.FileHandler('github_backup.log')
    file_formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    file_handler.setFormatter(file_formatter)
    logger.addHandler(file_handler)
    
    return logger

def git_installed():
    try:
        subprocess.check_call(['git', '--version'],
                              stdout=subprocess.PIPE,
                              stderr=subprocess.PIPE)
    except:
        return False
    return True

def user_organizations(user):
    url = 'https://api.github.com/users/' + user + '/orgs'
    response = urllib.request.urlopen(url).read().decode('utf-8')
    repositories = json.loads(response)
    return [repository['login'] for repository in repositories]

def user_repositories(user):
    url = 'https://api.github.com/users/' + user + '/repos?per_page=100'
    response = urllib.request.urlopen(url).read().decode('utf-8')
    repositories = json.loads(response)
    for repository in repositories:
        yield (repository['name'], repository['git_url'])
    if args.stars:
        for repo in json.loads(urllib.request.urlopen('https://api.github.com/users/'+user+'/starred?per_page=100').read().decode('utf-8')):
            yield (repo['name'], repo['git_url'])
 
def clone_repository(url, directory):
    subprocess.call(['git', 'clone', url, directory],
                    stdout=subprocess.PIPE, stderr=subprocess.PIPE)

def update_repository(directory):
    cwd = os.getcwd()
    os.chdir(directory)
    subprocess.call(['git', 'pull'],
                    stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    os.chdir(cwd)

def is_tracking_repository(directory, url):
    cwd = os.getcwd()
    os.chdir(directory)
    process = subprocess.Popen(['git', 'config', 'remote.origin.url'],
                               stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    output, errors = process.communicate()
    os.chdir(cwd)
    return output.decode('utf-8').strip() == url

logger = setup_logger()

if not git_installed():
    logger.error('The git executable is missing.')
    sys.exit(1)

parser = argparse.ArgumentParser(description='Backs up all your public GitHub repositories.')
parser.add_argument('user', type=str, help='your GitHub user name')
parser.add_argument('root', type=str, help='the target directory')
parser.add_argument('--stars', help='backup starred repos?', default=False, action='store_true')
parser.add_argument('--dry_run', help='simulate run? (no git)', default=False, action='store_true')
args = parser.parse_args()
args.root = os.path.realpath(os.path.expanduser(args.root))

logger.info('Backing up to {0}...'.format(args.root))

if not os.path.exists(args.root):
    os.makedirs(args.root)

updates, clones = 0, 0

for user in user_organizations(args.user) + [args.user]:
    print(user)
    for name, url in user_repositories(user):

        directory = os.path.realpath(os.path.join(args.root, name))   
        if args.dry_run:
            logger.info('Not cloning / updating {0}...'.format(name))
        else:
            if os.path.exists(directory):
                logger.info('Updating {0}...'.format(name))
                update_repository(directory)
                updates += 1
            else:
                logger.info('Cloning {0}...'.format(name))
                clone_repository(url, directory)
                clones += 1
        
logger.info('{0} new repositories, {1} updated.'.format(clones, updates))
