"""The CLI — argument handling for the one thing this package does: compute a version."""
import subprocess

from papeete_version import cli, version


def _git(*args, cwd):
    subprocess.run(["git", *args], cwd=cwd, check=True, capture_output=True)


def _init_actor_repo(folder, name, tag):
    folder.mkdir(parents=True, exist_ok=True)
    (folder / "marker.txt").write_text(f"{name}\n")
    _git("init", "-q", cwd=folder)
    _git("-c", "user.email=t@t", "-c", "user.name=t", "add", ".", cwd=folder)
    _git("-c", "user.email=t@t", "-c", "user.name=t", "commit", "-q", "-m", "init", cwd=folder)
    _git("tag", f"{version.normalize_name(name)}/v{tag}", cwd=folder)


def test_compute_prints_the_computed_version(tmp_path, capsys):
    folder = tmp_path / "archivist"
    _init_actor_repo(folder, "Archivist", "2.2.0")

    assert cli.main(["compute", str(folder), "--name", "Archivist", "--label", "dev"]) == 0
    assert capsys.readouterr().out.strip() == version.compute(folder, "Archivist", "dev")


def test_compute_fails_clearly_with_no_matching_tag(tmp_path, capsys):
    folder = tmp_path / "archivist"
    folder.mkdir()
    (folder / "marker.txt").write_text("x\n")
    _git("init", "-q", cwd=folder)
    _git("-c", "user.email=t@t", "-c", "user.name=t", "add", ".", cwd=folder)
    _git("-c", "user.email=t@t", "-c", "user.name=t", "commit", "-q", "-m", "init", cwd=folder)

    assert cli.main(["compute", str(folder), "--name", "Archivist", "--label", "dev"]) == 2
    assert "no tag matching 'archivist/v*'" in capsys.readouterr().err
