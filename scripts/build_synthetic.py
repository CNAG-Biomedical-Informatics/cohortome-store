"""Build local-preview packages from committed COHORTome synthetic fixtures."""
import argparse
import hashlib
import json
from pathlib import Path, PurePosixPath
import re
import shutil
import subprocess
import sys
import tempfile
import zipfile


DATASETS = {"default": "default_dataset", "synthetic-autoimmune-demo": "synthetic_autoimmune_demo"}


def git(repo, *args):
    return subprocess.check_output(["git", "-C", str(repo), *args])


def write_json(path, payload):
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def snapshot(repo, commit, dataset, destination, *, worktree=False):
    """Export only regular, committed files from a fixed synthetic source root."""
    source = DATASETS[dataset]
    entries = git(repo, "ls-tree", "-rz", commit, "--", source).split(b"\0")
    hashes = {}
    for entry in filter(None, entries):
        header, name = entry.split(b"\t", 1)
        mode, kind, blob = header.decode().split()
        relative = PurePosixPath(name.decode()).relative_to(source)
        if mode != "100644" or kind != "blob" or ".." in relative.parts:
            raise ValueError("Only regular, non-executable synthetic source files are allowed")
        allowed_root = relative.as_posix() in {"manifest.json", "README.md", "provenance.json", "simulation_truth.json"}
        allowed_data = (len(relative.parts) > 1 and relative.parts[0] in {"clinical", "assays", "identifiers"}
                        and relative.suffix in {".json", ".csv", ".tsv", ".md", ".dcm"})
        if not (allowed_root or allowed_data):
            raise ValueError("Unexpected file in synthetic source; review the package allowlist")
        if worktree:
            path = repo.joinpath(source, *relative.parts)
            if path.is_symlink() or path.resolve() != path.absolute() or not path.is_file():
                raise ValueError("Working source must be a regular file without symlink parents")
            data = path.read_bytes()
        else:
            data = git(repo, "cat-file", "blob", blob)
        target = destination.joinpath(*relative.parts)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(data)
        hashes[relative.as_posix()] = hashlib.sha256(data).hexdigest()
    if "manifest.json" not in hashes:
        raise ValueError("Source revision does not contain the dataset manifest")
    return hashes


def archive(root, target):
    """Stable ordering, timestamps and permissions; no host paths in the ZIP."""
    with zipfile.ZipFile(target, "x", compression=zipfile.ZIP_STORED) as output:
        for path in sorted(root.rglob("*")):
            if path.is_symlink():
                raise ValueError("Symlinks are not allowed in resource packages")
            if not path.is_file():
                continue
            name = root.name + "/" + path.relative_to(root).as_posix()
            info = zipfile.ZipInfo(name, date_time=(1980, 1, 1, 0, 0, 0))
            info.create_system = 3
            info.external_attr = 0o100644 << 16
            output.writestr(info, path.read_bytes())


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cohortome", required=True, type=Path)
    parser.add_argument("--revision", default="HEAD", help="Optional fixture source revision (default HEAD); not a compatibility requirement")
    parser.add_argument("--worktree", action="store_true", help="Use current contents of allowlisted files tracked at the revision; exclude untracked files")
    parser.add_argument("--dataset", required=True, choices=DATASETS)
    parser.add_argument("--version", required=True, help="Local preview version, e.g. 0.1.0-preview")
    parser.add_argument("--output", type=Path, default=Path(__file__).resolve().parents[1] / "dist")
    args = parser.parse_args()
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]*", args.version):
        parser.error("Version must be a safe filename component")
    repo = args.cohortome.resolve()
    commit = git(repo, "rev-parse", "--verify", args.revision + "^{commit}").decode().strip()
    sys.path.insert(0, str(repo))
    from app.dataset_validation import validate_package

    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=True)
    release_name = f"{args.dataset}-{args.version}"
    destination = output / release_name
    if destination.exists():
        parser.error("Output release already exists; choose a new version or output directory")
    with tempfile.TemporaryDirectory(prefix="resource-build-", dir=output) as temporary:
        work = Path(temporary)
        package = work / args.dataset
        hashes = snapshot(repo, commit, args.dataset, package, worktree=args.worktree)
        validation = validate_package(package)
        metadata = dict(manifest_version=1, dataset_id=args.dataset, version=args.version, schema_version=1,
                        synthetic=True,
                        source_mode="tracked-worktree" if args.worktree else "committed",
                        distribution_status="local-preview", redistribution_review="pending",
                        files_sha256=hashes, validation=validation)
        write_json(package / "resource.json", metadata)
        release = work / "release"
        release.mkdir()
        filename = release_name + ".zip"
        archive(package, release / filename)
        digest = hashlib.sha256((release / filename).read_bytes()).hexdigest()
        (release / (filename + ".sha256")).write_text(f"{digest}  {filename}\n", encoding="ascii")
        write_json(release / "release.json", {**metadata, "archive": filename,
                   "archive_sha256": digest, "archive_bytes": (release / filename).stat().st_size})
        # No source registration, store preparation or publication occurs here.
        shutil.move(str(release), destination)
    print(json.dumps({"dataset": args.dataset, "source_commit": commit,
                      "sha256": digest, "validation": validation, "output": str(destination)}, indent=2))


if __name__ == "__main__":
    main()
