#!/usr/bin/python
# gi from nu11secur1ty (patched with modes)

import requests
import re
import os
import sys
import signal
from colorama import init, Fore, Style

init(autoreset=True)

EMAIL_RE = re.compile(r"[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}")
TOKEN_FILE = "token.txt"

def load_token():
    if os.path.isfile(TOKEN_FILE):
        with open(TOKEN_FILE, "r", encoding="utf-8") as f:
            token = f.read().strip()
            if token:
                print(Fore.GREEN + "[*] Loaded token from token.txt")
                return token
    token = input(Fore.CYAN + "GitHub Personal Access Token (optional, press Enter to skip): ").strip()
    if token:
        with open(TOKEN_FILE, "w", encoding="utf-8") as f:
            f.write(token)
        print(Fore.GREEN + "[*] Token saved to token.txt")
    else:
        print(Fore.YELLOW + "[!] No token provided; unauthenticated requests have stricter rate limits.")
    return token

def get_headers(token):
    headers = {
        "Accept": "application/vnd.github.v3+json",
        "User-Agent": "gi-github-email-finder"
    }
    if token:
        headers["Authorization"] = f"token {token}"
    return headers

def get_commits(owner, repo, token, max_commits=100):
    commits = []
    page = 1
    while len(commits) < max_commits:
        per_page = min(100, max_commits - len(commits))
        url = f"https://api.github.com/repos/{owner}/{repo}/commits"
        params = {"per_page": per_page, "page": page}
        r = requests.get(url, headers=get_headers(token), params=params)
        if r.status_code == 403:
            print(Fore.RED + "[!] Rate limit exceeded or forbidden. Try using a token or wait a bit.")
            break
        if r.status_code == 404:
            print(Fore.RED + f"[!] Repository {owner}/{repo} not found.")
            break
        r.raise_for_status()
        data = r.json()
        if not data:
            break
        commits.extend(data)
        if len(data) < per_page:
            break
        page += 1
    return commits[:max_commits]

def extract_user_emails_from_commits(commits, username):
    emails = set()
    for commit in commits:
        author = commit.get("author")
        committer = commit.get("committer")
        if author and author.get("login", "").lower() == username.lower():
            email = commit.get("commit", {}).get("author", {}).get("email")
            if email and "noreply" not in email.lower():
                emails.add(email)
        elif committer and committer.get("login", "").lower() == username.lower():
            email = commit.get("commit", {}).get("committer", {}).get("email")
            if email and "noreply" not in email.lower():
                emails.add(email)
    return emails

def extract_all_emails_from_commits(commits):
    emails = set()
    for commit in commits:
        email = commit.get("commit", {}).get("author", {}).get("email")
        if email and "noreply" not in email.lower():
            emails.add(email)
        email2 = commit.get("commit", {}).get("committer", {}).get("email")
        if email2 and "noreply" not in email2.lower():
            emails.add(email2)
    return emails

def save_emails(emails, filename="emails.txt"):
    with open(filename, "w", encoding="utf-8") as f:
        for email in sorted(emails):
            f.write(email + "\n")
    print(Fore.GREEN + f"[+] Saved {len(emails)} emails to {filename}")

def signal_handler(sig, frame):
    print(Fore.YELLOW + "\n[!] Interrupted by user. Exiting cleanly.")
    sys.exit(0)

def main():
    signal.signal(signal.SIGINT, signal_handler)
    print(Fore.MAGENTA + Style.BRIGHT + "=== gi: GitHub Repo Email Finder ===")
    print(Fore.WHITE + "Enter details in the following format:")
    print(Fore.YELLOW + "  user/repo  (e.g., user/repo-code)")
    print(Fore.YELLOW + "  repo-code  (GitHub username, e.g., username)\n")

    token = load_token()

    repo_full = input(Fore.CYAN + "Enter user/repo: ").strip()
    if repo_full.startswith("http"):
        parts = repo_full.rstrip("/").split("/")
        if len(parts) >= 2:
            repo_full = "/".join(parts[-2:])
            print(Fore.YELLOW + f"[!] Extracted repository '{repo_full}' from URL input.")

    if "/" not in repo_full:
        print(Fore.RED + "[!] Invalid repository format. Please use 'user/repo'. Exiting.")
        return
    owner, repo = repo_full.split("/", 1)

    mode = input(Fore.CYAN + "Mode: [1] All emails  [2] Only from owner username: ").strip()

    username = None
    if mode == "2":
        username = input(Fore.CYAN + "Enter repo-code (GitHub username): ").strip()
        if not username:
            print(Fore.RED + "[!] No username entered. Exiting.")
            return

    print(Fore.WHITE + f"\n[*] Fetching commits from {owner}/{repo} ...")
    commits = get_commits(owner, repo, token, max_commits=100)
    if not commits:
        print(Fore.RED + "[!] No commits found or rate limited.")
        return

    if mode == "2":
        emails = extract_user_emails_from_commits(commits, username)
    else:
        emails = extract_all_emails_from_commits(commits)

    if emails:
        save_emails(emails)
    else:
        print(Fore.YELLOW + "[!] No emails found.")

if __name__ == "__main__":
    main()
