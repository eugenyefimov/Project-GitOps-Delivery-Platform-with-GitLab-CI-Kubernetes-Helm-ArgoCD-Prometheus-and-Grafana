#!/usr/bin/env python3
"""
Update deployment metadata in an external GitOps repository.

Workflow:
1. Clone external GitOps repo using token-based auth from CI variables.
2. Update a target values file (repository + digest keys).
3. Commit with traceable metadata.
4. Push back to target branch.
"""

import os
import shutil
import stat
import subprocess
import tempfile
from pathlib import Path

import yaml


def require_env(name: str) -> str:
    value = os.getenv(name, "").strip()
    if not value:
        raise RuntimeError(f"Missing required environment variable: {name}")
    return value


def run(command: list[str], cwd: Path | None = None, env: dict[str, str] | None = None) -> None:
    subprocess.run(command, cwd=cwd, env=env, check=True)


def set_nested_key(payload: dict, dotted_key: str, value: str, strict: bool = False) -> None:
    parts = dotted_key.split(".")
    node = payload
    for key in parts[:-1]:
        if key not in node or not isinstance(node[key], dict):
            if strict:
                raise RuntimeError(f"Missing required key path segment '{key}' in '{dotted_key}'")
            node[key] = {}
        node = node[key]
    if strict and parts[-1] not in node:
        raise RuntimeError(f"Missing required leaf key '{parts[-1]}' in '{dotted_key}'")
    node[parts[-1]] = value


def create_askpass_script(script_path: Path) -> None:
    # GIT_ASKPASS avoids embedding credentials into clone URLs.
    script_path.write_text(
        "#!/bin/sh\n"
        "case \"$1\" in\n"
        "  *Username*) echo \"oauth2\" ;;\n"
        "  *Password*) echo \"$GITOPS_PUSH_TOKEN\" ;;\n"
        "  *) echo \"\" ;;\n"
        "esac\n",
        encoding="utf-8",
    )
    script_path.chmod(script_path.stat().st_mode | stat.S_IXUSR)


def build_git_env(askpass_path: Path, push_token: str) -> dict[str, str]:
    env = os.environ.copy()
    env["GIT_ASKPASS"] = str(askpass_path)
    env["GIT_TERMINAL_PROMPT"] = "0"
    env["GITOPS_PUSH_TOKEN"] = push_token
    return env


def clone_and_checkout(repo_url: str, target_branch: str, clone_dir: Path, git_env: dict[str, str]) -> None:
    run(["git", "clone", repo_url, str(clone_dir)], env=git_env)
    run(["git", "checkout", target_branch], cwd=clone_dir, env=git_env)


def update_values_file(
    file_path: Path,
    repository_key: str,
    image_repository: str,
    digest_key: str,
    image_digest: str,
    strict_keys: bool,
) -> None:
    with file_path.open("r", encoding="utf-8") as infile:
        payload = yaml.safe_load(infile) or {}
    if not isinstance(payload, dict):
        raise RuntimeError(f"Expected top-level YAML object in: {file_path}")

    set_nested_key(payload, repository_key, image_repository, strict=strict_keys)
    set_nested_key(payload, digest_key, image_digest, strict=strict_keys)

    with file_path.open("w", encoding="utf-8") as outfile:
        yaml.safe_dump(payload, outfile, sort_keys=False)


def commit_and_push(
    clone_dir: Path,
    values_file: str,
    commit_user_name: str,
    commit_user_email: str,
    commit_message: str,
    target_branch: str,
    git_env: dict[str, str],
) -> bool:
    run(["git", "config", "user.name", commit_user_name], cwd=clone_dir, env=git_env)
    run(["git", "config", "user.email", commit_user_email], cwd=clone_dir, env=git_env)

    diff_result = subprocess.run(
        ["git", "status", "--porcelain"],
        cwd=clone_dir,
        env=git_env,
        capture_output=True,
        text=True,
        check=True,
    )
    if not diff_result.stdout.strip():
        print("No GitOps changes detected. Skipping commit.")
        return False

    run(["git", "add", values_file], cwd=clone_dir, env=git_env)
    run(["git", "commit", "-m", commit_message], cwd=clone_dir, env=git_env)
    run(["git", "push", "origin", target_branch], cwd=clone_dir, env=git_env)
    return True


def main() -> None:
    # CI/job context
    app_name = os.getenv("APP_NAME", "platform-app")
    target_env = os.getenv("GITOPS_TARGET_ENV", "dev")
    target_branch = os.getenv("GITOPS_TARGET_BRANCH", "main")
    digest_key = os.getenv("GITOPS_IMAGE_DIGEST_KEY", "image.digest")
    repository_key = os.getenv("GITOPS_IMAGE_REPOSITORY_KEY", "image.repository")
    strict_keys = os.getenv("GITOPS_STRICT_KEYS", "false").lower() == "true"
    commit_user_name = os.getenv("GITOPS_COMMIT_USER_NAME", "gitlab-ci-bot")
    commit_user_email = os.getenv("GITOPS_COMMIT_USER_EMAIL", "gitlab-ci-bot@example.com")

    # Required external inputs
    repo_url = require_env("GITOPS_REPO_URL")
    push_token = require_env("GITOPS_PUSH_TOKEN")
    values_file = require_env("GITOPS_VALUES_FILE")
    image_tag = require_env("IMAGE_TAG")
    image_digest = require_env("IMAGE_DIGEST")
    image_repository = require_env("IMAGE_REPO")

    # Traceability metadata for commit body
    source_project = os.getenv("CI_PROJECT_PATH", "unknown-project")
    source_sha = os.getenv("CI_COMMIT_SHA", "unknown-sha")[:8]
    pipeline_url = os.getenv("CI_PIPELINE_URL", "")

    temp_dir = Path(tempfile.mkdtemp(prefix="gitops-update-"))
    try:
        askpass_path = temp_dir / "git_askpass.sh"
        create_askpass_script(askpass_path)
        git_env = build_git_env(askpass_path, push_token)

        clone_dir = temp_dir / "gitops-repo"
        clone_and_checkout(repo_url, target_branch, clone_dir, git_env)

        target_file = clone_dir / values_file
        if not target_file.exists():
            raise RuntimeError(f"Target values file does not exist: {values_file}")

        update_values_file(
            file_path=target_file,
            repository_key=repository_key,
            image_repository=image_repository,
            digest_key=digest_key,
            image_digest=image_digest,
            strict_keys=strict_keys,
        )

        commit_message = (
            f"chore(gitops/{target_env}): deploy {app_name}:{image_tag}@{image_digest[:12]}\n\n"
            f"source: {source_project}@{source_sha}\n"
            + (f"pipeline: {pipeline_url}\n" if pipeline_url else "")
        )
        changed = commit_and_push(
            clone_dir=clone_dir,
            values_file=values_file,
            commit_user_name=commit_user_name,
            commit_user_email=commit_user_email,
            commit_message=commit_message,
            target_branch=target_branch,
            git_env=git_env,
        )
        if changed:
            print(f"Updated {values_file} with {repository_key}={image_repository} and {digest_key}={image_digest}")
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


if __name__ == "__main__":
    main()
