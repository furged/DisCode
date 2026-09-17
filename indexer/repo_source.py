import json
import os
import re
import tempfile
import urllib.error
import urllib.request
import zipfile

# Matches https://github.com/owner/repo, .../repo.git, and .../repo/tree/branch
# (people pasting a URL from their browser often have the /tree/branch suffix
# from browsing a non-default branch — worth handling since that's exactly
# the "just saw a repo online" flow this is for).
GITHUB_URL_RE = re.compile(
    r"^https?://github\.com/(?P<owner>[^/]+)/(?P<repo>[^/]+?)(?:\.git)?"
    r"(?:/tree/(?P<branch>[^/]+))?/?$"
)


class RepoFetchError(Exception):
    """Raised when a GitHub URL can't be resolved to actual repo contents."""


def is_github_url(source):
    return GITHUB_URL_RE.match(source.strip()) is not None


def _get_default_branch(owner, repo):
    api_url = f"https://api.github.com/repos/{owner}/{repo}"
    req = urllib.request.Request(api_url, headers={"User-Agent": "DisCode"})
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        if e.code == 404:
            raise RepoFetchError(f"Repo not found (is it public? private repos aren't supported): {owner}/{repo}")
        raise RepoFetchError(f"GitHub API error looking up {owner}/{repo}: {e}")
    except urllib.error.URLError as e:
        raise RepoFetchError(f"Couldn't reach GitHub API: {e}")
    return data["default_branch"]


def _download_zip(owner, repo, branch, tmp_dir):
    """Returns the path to the downloaded zip, or None on a 404 (caller tries the next branch guess)."""
    zip_url = f"https://codeload.github.com/{owner}/{repo}/zip/refs/heads/{branch}"
    zip_path = os.path.join(tmp_dir, "repo.zip")
    req = urllib.request.Request(zip_url, headers={"User-Agent": "DisCode"})
    try:
        with urllib.request.urlopen(req, timeout=120) as resp, open(zip_path, "wb") as f:
            f.write(resp.read())
        return zip_path
    except urllib.error.HTTPError as e:
        if e.code == 404:
            return None
        raise RepoFetchError(f"Failed to download {owner}/{repo}: {e}")
    except urllib.error.URLError as e:
        raise RepoFetchError(f"Couldn't reach GitHub: {e}")


def resolve_repo_source(source):
    """
    Accepts either a local directory path or a GitHub repo URL. If it's a
    GitHub URL, downloads the repo as a zip (no git install or auth needed -
    public repos only, matching "someone pastes a link they just found")
    and extracts it to a fresh temp dir, returning that local path instead.
    Local paths pass through unchanged.

    Deliberately avoids the GitHub REST API where possible - it's tightly
    rate-limited for unauthenticated requests (60/hr per IP), whereas
    codeload.github.com (the plain zip-download endpoint) isn't. So instead
    of asking the API "what's the default branch", this just tries "main"
    then "master" directly against codeload, and only falls back to the API
    for repos using some other default branch name.
    """
    source = source.strip()
    match = GITHUB_URL_RE.match(source)
    if not match:
        return source

    owner, repo, branch = match.group("owner"), match.group("repo"), match.group("branch")
    tmp_dir = tempfile.mkdtemp(prefix=f"discode_{owner}_{repo}_")

    if branch:
        zip_path = _download_zip(owner, repo, branch, tmp_dir)
        if zip_path is None:
            raise RepoFetchError(f"Couldn't find branch '{branch}' on {owner}/{repo} (or the repo doesn't exist)")
    else:
        zip_path = _download_zip(owner, repo, "main", tmp_dir)
        if zip_path is not None:
            branch = "main"
        else:
            zip_path = _download_zip(owner, repo, "master", tmp_dir)
            if zip_path is not None:
                branch = "master"
            else:
                # Neither common default worked - fall back to actually
                # asking the API, which costs a rate-limited call but
                # covers repos using something unusual (e.g. "develop").
                branch = _get_default_branch(owner, repo)
                zip_path = _download_zip(owner, repo, branch, tmp_dir)
                if zip_path is None:
                    raise RepoFetchError(f"Couldn't download {owner}/{repo} (branch: {branch})")

    try:
        with zipfile.ZipFile(zip_path) as zf:
            zf.extractall(tmp_dir)
    except zipfile.BadZipFile:
        raise RepoFetchError(f"Downloaded file from {owner}/{repo} wasn't a valid zip")

    # GitHub's zip always extracts into one subfolder named "{repo}-{branch}",
    # but branch names with slashes (e.g. "feature/x") get sanitized by
    # GitHub differently than we'd guess, so fall back to "whatever single
    # folder actually got extracted" instead of assuming the exact name.
    expected_path = os.path.join(tmp_dir, f"{repo}-{branch}")
    if os.path.isdir(expected_path):
        return expected_path

    subdirs = [d for d in os.listdir(tmp_dir)
               if os.path.isdir(os.path.join(tmp_dir, d))]
    if len(subdirs) == 1:
        return os.path.join(tmp_dir, subdirs[0])

    raise RepoFetchError(f"Downloaded {owner}/{repo} but couldn't locate its extracted contents")