#!/usr/bin/env python3
import platform
import shutil
import subprocess
import sys
from pathlib import Path
from shutil import which

ROOT = Path(__file__).resolve().parent
RESULTS_DIR = ROOT / "test-results"


def log(msg: str) -> None:
    print(msg, flush=True)


def is_windows() -> bool:
    return platform.system().lower().startswith("win")


def cmd_name(base: str) -> str:
    if is_windows() and which(f"{base}.cmd"):
        return f"{base}.cmd"
    return base


def run(cmd: list[str], cwd: Path) -> int:
    log(f"> {' '.join(cmd)}  (cwd={cwd})")
    return subprocess.run(cmd, cwd=str(cwd)).returncode


def ensure_cmd(cmd: str, hint: str) -> bool:
    candidates = [cmd]
    if is_windows():
        candidates += [f"{cmd}.cmd", f"{cmd}.exe", f"{cmd}.bat"]

    if not any(which(c) for c in candidates):
        log(f"ERREUR: '{cmd}' introuvable. {hint}")
        return False
    return True

def clean_results_dir() -> None:
    if RESULTS_DIR.exists():
        shutil.rmtree(RESULTS_DIR)
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)


def copy_xml(src_dir: Path, pattern: str, dest_dir: Path) -> int:
    dest_dir.mkdir(parents=True, exist_ok=True)
    if not src_dir.exists():
        return 0
    copied = 0
    for f in src_dir.glob(pattern):
        if f.is_file() and f.suffix.lower() == ".xml":
            shutil.copy2(f, dest_dir / f.name)
            copied += 1
    return copied


def is_angular_project(root: Path) -> bool:
    return (root / "package.json").exists() and (root / "karma.conf.js").exists()


def is_gradle_project(root: Path) -> bool:
    has_wrapper = (root / "gradlew").exists() or (root / "gradlew.bat").exists()
    has_build = (root / "build.gradle").exists() or (root / "build.gradle.kts").exists()
    return has_wrapper and has_build


def run_angular() -> int:
    log("\n=== Détection: projet Angular (npm/Karma) ===")

    if not ensure_cmd("node", "Installer Node.js (LTS)."):
        return 1
    if not ensure_cmd("npm", "npm est fourni avec Node.js."):
        return 1

    npm = cmd_name("npm")

    # Dépendances
    if (ROOT / "package-lock.json").exists():
        if run([npm, "ci"], cwd=ROOT) != 0:
            log("ERREUR: npm ci en échec.")
            return 1
    else:
        if run([npm, "install"], cwd=ROOT) != 0:
            log("ERREUR: npm install en échec.")
            return 1

    # Tests unitaires
    test_code = run([npm, "test"], cwd=ROOT)

    # JUnit XML attendu (ton projet OC Angular): reports/*.xml
    copied = copy_xml(ROOT / "reports", "*.xml", RESULTS_DIR)
    if copied == 0:
        log("ERREUR: aucun rapport JUnit XML trouvé (attendu: reports/*.xml).")
        log("Vérifier karma.conf.js (karma-junit-reporter + outputDir).")
        return 1

    log(f"OK: {copied} rapport(s) JUnit -> {RESULTS_DIR}")
    return 0 if test_code == 0 else 1


def run_gradle() -> int:
    log("\n=== Détection: projet Java Gradle ===")

    if not ensure_cmd("java", "Installer un JDK (Temurin 17/21 selon le projet)."):
        return 1

    if is_windows():
        gradlew = ROOT / "gradlew.bat"
        if not gradlew.exists():
            log("ERREUR: gradlew.bat introuvable.")
            return 1
        gradle_cmd = [str(gradlew)]
    else:
        gradlew = ROOT / "gradlew"
        if not gradlew.exists():
            log("ERREUR: gradlew introuvable.")
            return 1
        try:
            gradlew.chmod(gradlew.stat().st_mode | 0o111)
        except Exception:
            pass
        gradle_cmd = [str(gradlew)]

    test_code = run(gradle_cmd + ["clean", "test"], cwd=ROOT)

    copied = copy_xml(ROOT / "build" / "test-results" / "test", "*.xml", RESULTS_DIR)
    if copied == 0:
        log("ERREUR: aucun rapport JUnit XML trouvé (attendu: build/test-results/test/*.xml).")
        return 1

    log(f"OK: {copied} rapport(s) JUnit -> {RESULTS_DIR}")
    return 0 if test_code == 0 else 1


def main() -> int:
    clean_results_dir()

    if is_angular_project(ROOT):
        return run_angular()

    if is_gradle_project(ROOT):
        return run_gradle()

    log("ERREUR: type de projet non détecté.")
    log("Attendu: Angular (package.json + karma.conf.js) OU Gradle (gradlew(.bat) + build.gradle/.kts).")
    return 1


if __name__ == "__main__":
    sys.exit(main())