"""
Jenkins API client for fetching jobs and downloading build logs.
"""

import datetime as _dt
import urllib.parse as _url
from pathlib import Path
from typing import Dict, List
import sys

import requests
from requests.auth import HTTPBasicAuth


class JenkinsClient:
    """Client for interacting with Jenkins API."""
    
    def __init__(self, base_url: str, user: str, token: str):
        self.base_url = base_url.rstrip('/')
        self.auth = HTTPBasicAuth(user, token)
    
    def _json_get(self, url: str, *, params: Dict[str, str] | None = None):
        """Wrapper around requests.get that returns JSON and throws for non‑200."""
        try:
            r = requests.get(url, auth=self.auth, params=params, timeout=60)
            r.raise_for_status()
            return r.json()
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 502:
                # Bad Gateway - Jenkins server issue, not our fault
                raise requests.exceptions.HTTPError(f"Jenkins server error (502 Bad Gateway) for URL: {url}") from e
            else:
                raise
    
    def get_jobs(self) -> List[Dict[str, str]]:
        """Return a list of {name,url} dicts for every job (recursive into folders)."""
        return self._get_jobs_recursive(self.base_url)
    
    def _get_jobs_recursive(self, url: str) -> List[Dict[str, str]]:
        """Recursively fetch jobs, descending into folders."""
        api = url.rstrip('/') + '/api/json'
        data = self._json_get(api, params={'tree': 'jobs[name,url,_class]'})
        
        result = []
        for job in data.get('jobs', []):
            job_class = job.get('_class', '')
            # Check if this is a folder (Cloudbees or native folder)
            if 'folder' in job_class.lower():
                result.extend(self._get_jobs_recursive(job['url']))
            else:
                result.append({'name': job['name'], 'url': job['url']})
        return result
    
    def get_failed_builds(self, job_url: str, cutoff_ms: int, limit: int):
        """Get up to *limit* failure builds for *job_url* newer than *cutoff_ms*."""
        failures = []
        offset = 0
        batch_size = 1000  # Use larger batches for allBuilds
        
        while len(failures) < limit:
            # Fetch builds in batches using allBuilds
            api = _url.urljoin(job_url, 'api/json')
            params = {
                'tree': f'allBuilds[number,result,timestamp,url]{{{offset},{offset + batch_size - 1}}}'
            }
            
            try:
                data = self._json_get(api, params=params)
                builds = data.get('allBuilds', [])
                
                if not builds:
                    # No more builds available
                    break
                
                # Process this batch
                found_old_build = False
                for b in builds:
                    if b['timestamp'] < cutoff_ms:
                        # Reached builds older than our time window
                        found_old_build = True
                        break
                    
                    if b['result'] == 'FAILURE':
                        failures.append(b)
                        if len(failures) >= limit:
                            return failures
                
                # If we found builds older than cutoff, stop pagination
                if found_old_build:
                    break
                
                # Move to next batch
                offset += batch_size
                
                # Safety limit: don't fetch more than 10k builds total
                if offset >= 10000:
                    break
                    
            except Exception as e:
                # If allBuilds fails, try fallback to regular builds (limited scope)
                if offset == 0:  # Only try fallback on first attempt
                    try:
                        params = {
                            'tree': f'builds[number,result,timestamp,url]{{0,100}}'
                        }
                        data = self._json_get(api, params=params)
                        builds = data.get('builds', [])
                        
                        for b in builds:
                            if b['timestamp'] < cutoff_ms:
                                break
                            if b['result'] == 'FAILURE':
                                failures.append(b)
                                if len(failures) >= limit:
                                    break
                        break
                    except Exception:
                        pass
                
                print(f"[WARN] Error fetching allBuilds batch {offset}-{offset + batch_size - 1} for {job_url}: {e}", file=sys.stderr)
                break
        
        return failures
    
    def download_build_log(self, build_url: str, output_path: Path) -> bool:
        """Download the console log for a build and save it to output_path."""
        log_url = _url.urljoin(build_url, 'consoleText')
        try:
            r = requests.get(log_url, auth=self.auth, timeout=60)
            r.raise_for_status()
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(r.text)
            return True
        except Exception as exc:
            print(f"[WARN] Failed to download log for {build_url}: {exc}", file=sys.stderr)
            return False
