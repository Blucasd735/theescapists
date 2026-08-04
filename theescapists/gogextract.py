#!/usr/bin/env python3
"""Extrai com segurança o payload noarch de um instalador Linux GOG/Makeself."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import time
import zipfile


VERSION = "1.0.3"


class ExtractError(RuntimeError):
    pass


class Progress:
    def __init__(self, game_dir: Path):
        self.workspace = Path(tempfile.mkdtemp(prefix="gogextract-", dir=str(game_dir)))
        self.progress = self.workspace / "progress.txt"
        self.stop = self.workspace / "ui.stop"
        self.process: subprocess.Popen[bytes] | None = None

    def update(self, overall: int, message: str, detail: str = "", state: int = 1) -> None:
        overall = max(0, min(1000, int(overall)))
        message = " ".join(message.replace("\n", " ").split())
        detail = " ".join(detail.replace("\n", " ").split())
        payload = (
            f"{state} {overall} 1000\n{message}\n"
            f"NXEXTRACT_V1 4 {overall} {overall} 0 0\n{detail}\n"
        )
        temporary = self.progress.with_suffix(".tmp")
        temporary.write_text(payload, encoding="utf-8")
        os.replace(temporary, self.progress)

    def start(self, binary: Path) -> None:
        self.update(0, "PREPARANDO INSTALADOR GOG")
        if not os.access(binary, os.X_OK):
            return
        try:
            self.process = subprocess.Popen(
                [str(binary), str(self.progress), str(self.stop), "PREPARANDO JOGO", VERSION],
                stdin=subprocess.DEVNULL,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                cwd=self.workspace,
            )
        except OSError:
            self.process = None

    def finish(self, success: bool, message: str, delay: int) -> None:
        self.update(1000 if success else 0, message, state=3 if success else 2)
        time.sleep(delay)
        self.stop.touch()
        if self.process is not None:
            try:
                self.process.wait(timeout=3)
            except subprocess.TimeoutExpired:
                self.process.terminate()
        shutil.rmtree(self.workspace, ignore_errors=True)


def human_size(value: int) -> str:
    units = ("B", "KB", "MB", "GB")
    number = float(value)
    for unit in units:
        if number < 1024 or unit == units[-1]:
            return f"{number:.1f} {unit}"
        number /= 1024
    return f"{value} B"


def directory_size(root: Path) -> int:
    total = 0
    for base, _, names in os.walk(root):
        for name in names:
            try:
                total += (Path(base) / name).stat().st_size
            except OSError:
                pass
    return total


def installer_digest(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        while block := stream.read(4 * 1024 * 1024):
            digest.update(block)
    return digest.hexdigest()


def validate_installer(path: Path) -> None:
    with path.open("rb") as stream:
        header = stream.read(256 * 1024)
    if not header.startswith((b"#!/bin/sh", b"#!/bin/bash")):
        raise ExtractError("O ARQUIVO .SH NAO POSSUI CABECALHO DE INSTALADOR LINUX")
    markers = (b"Makeself", b"makeself", b"MS_dd", b"offset=", b"filesizes=", b"CRCsum")
    if not any(marker in header for marker in markers):
        raise ExtractError("O .SH NAO PARECE SER UM INSTALADOR GOG/MAKESELF COMPATIVEL")


def find_payload(stage: Path) -> Path:
    candidates = [p for p in stage.rglob("noarch") if p.is_dir() and p.parent.name == "data"]
    if len(candidates) == 1:
        return candidates[0]
    if not candidates:
        raise ExtractError("A PASTA DATA/NOARCH NAO FOI ENCONTRADA NO INSTALADOR")
    raise ExtractError("O INSTALADOR POSSUI MAIS DE UMA PASTA DATA/NOARCH")


def copy_tree(source: Path, destination: Path, progress: Progress) -> None:
    files = [p for p in source.rglob("*") if p.is_file() and not p.is_symlink()]
    total = sum(p.stat().st_size for p in files)
    done = 0
    destination.mkdir(parents=True)
    for item in files:
        relative = item.relative_to(source)
        target = destination / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(item, target)
        done += item.stat().st_size
        overall = 700 + (done * 250 // max(total, 1))
        progress.update(overall, "INSTALANDO DADOS DO JOGO", f"{human_size(done)} / {human_size(total)}")
    for item in source.rglob("*"):
        if item.is_dir():
            (destination / item.relative_to(source)).mkdir(parents=True, exist_ok=True)


def zip_noarch_members(installer: Path) -> list[tuple[zipfile.ZipInfo, Path]]:
    selected: list[tuple[zipfile.ZipInfo, Path]] = []
    with zipfile.ZipFile(installer) as archive:
        for info in archive.infolist():
            clean = info.filename.replace("\\", "/").lstrip("./")
            parts = [part for part in clean.split("/") if part]
            lowered = [part.lower() for part in parts]
            prefix = next(
                (index for index in range(len(parts) - 1)
                 if lowered[index:index + 2] == ["data", "noarch"]),
                None,
            )
            if prefix is None or len(parts) <= prefix + 2 or info.is_dir():
                continue
            relative_parts = parts[prefix + 2:]
            if any(part in (".", "..") for part in relative_parts):
                raise ExtractError("CAMINHO INSEGURO ENCONTRADO NO ZIP INTERNO")
            unix_mode = (info.external_attr >> 16) & 0xFFFF
            if (unix_mode & 0o170000) == 0o120000:
                continue
            selected.append((info, Path(*relative_parts)))
    if not selected:
        raise ExtractError("DATA/NOARCH NAO FOI ENCONTRADO NO ZIP INTERNO DO INSTALADOR")
    return selected


def extract_embedded_noarch(installer: Path, destination: Path, progress: Progress) -> None:
    members = zip_noarch_members(installer)
    total = sum(info.file_size for info, _ in members)
    done = 0
    destination.mkdir(parents=True)
    with zipfile.ZipFile(installer) as archive:
        for info, relative in members:
            target = destination / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            with archive.open(info) as source, target.open("wb") as output:
                while True:
                    block = source.read(1024 * 1024)
                    if not block:
                        break
                    output.write(block)
                    done += len(block)
                    overall = 150 + done * 800 // max(total, 1)
                    progress.update(
                        overall,
                        "EXTRAINDO DADOS DO JOGO",
                        f"{human_size(done)} / {human_size(total)}",
                    )
            unix_mode = (info.external_attr >> 16) & 0o777
            if unix_mode:
                target.chmod(unix_mode)


def migrate_v102_layout(gamedata: Path, final: Path, marker: Path, log) -> bool:
    nested_game = final / "game"
    if not marker.is_file() or not nested_game.is_dir():
        return False
    migration_game = gamedata / ".game-migration"
    if migration_game.exists():
        raise ExtractError("A PASTA TEMPORARIA .GAME-MIGRATION JA EXISTE")
    siblings = [item for item in final.iterdir() if item.name != "game"]
    collisions = [item.name for item in siblings if (gamedata / item.name).exists()]
    if collisions:
        raise ExtractError("NAO POSSO MIGRAR; ARQUIVOS JA EXISTEM EM GAMEDATA: " + ", ".join(collisions))
    os.replace(nested_game, migration_game)
    for item in siblings:
        os.replace(item, gamedata / item.name)
    final.rmdir()
    os.replace(migration_game, final)
    data = json.loads(marker.read_text(encoding="utf-8"))
    data["extractor"] = VERSION
    data["layout_migrated"] = "noarch-direct"
    marker.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    log("layout 1.0.2 migrated: gamedata/game/game -> gamedata/game")
    return True


def commit_noarch(staged: Path, gamedata: Path) -> None:
    if not (staged / "game").is_dir():
        raise ExtractError("O CONTEUDO EXTRAIDO NAO POSSUI A PASTA GAME ESPERADA")
    entries = list(staged.iterdir())
    collisions = [item.name for item in entries if (gamedata / item.name).exists()]
    if collisions:
        raise ExtractError("ARQUIVOS DE DESTINO JA EXISTEM EM GAMEDATA: " + ", ".join(collisions))
    for item in entries:
        os.replace(item, gamedata / item.name)
    staged.rmdir()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--game-dir", required=True, type=Path)
    args = parser.parse_args()
    game_dir = args.game_dir.resolve()
    gamedata = game_dir / "gamedata"
    final = gamedata / "game"
    marker = gamedata / ".gog-sh-installed.json"
    log_path = game_dir / "gogextract.log"
    progress = Progress(game_dir)
    progress.start(game_dir / "nxextract-ui")

    def log(message: str) -> None:
        with log_path.open("a", encoding="utf-8") as stream:
            stream.write(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] {message}\n")

    try:
        if migrate_v102_layout(gamedata, final, marker, log):
            progress.finish(True, "ESTRUTURA DO JOGO CORRIGIDA", 1)
            return 0
        if marker.is_file() and final.is_dir():
            progress.finish(True, "DADOS DO JOGO JA ESTAO PRONTOS", 1)
            return 0
        installers = sorted(p for p in gamedata.glob("*.sh") if p.is_file() and not p.is_symlink())
        if len(installers) != 1:
            raise ExtractError("COLOQUE EXATAMENTE UM INSTALADOR .SH DENTRO DE GAMEDATA")
        installer = installers[0]
        log(f"installer: {installer.name} ({installer.stat().st_size} bytes)")
        progress.update(40, "VERIFICANDO INSTALADOR GOG", installer.name)
        validate_installer(installer)
        digest = installer_digest(installer)
        progress.update(100, "PROCURANDO DADOS DO JOGO", installer.name)
        temporary_final = gamedata / ".game-new"
        if temporary_final.exists():
            shutil.rmtree(temporary_final)
        stage_parent: Path | None = None
        try:
            log("Procurando ZIP de dados MojoSetup anexado ao instalador.")
            extract_embedded_noarch(installer, temporary_final, progress)
            extraction_method = "embedded-mojosetup-zip"
        except (ExtractError, zipfile.BadZipFile):
            if temporary_final.exists():
                shutil.rmtree(temporary_final)
            stage_parent = Path(tempfile.mkdtemp(prefix=".gog-stage-", dir=str(gamedata)))
            unpacked = stage_parent / "unpacked"
            unpacked.mkdir()
            command_log = stage_parent / "installer-output.log"
            with command_log.open("wb") as command_output:
                process = subprocess.Popen(
                    ["bash", str(installer), "--noexec", "--target", str(unpacked)],
                    stdin=subprocess.DEVNULL,
                    stdout=command_output,
                    stderr=subprocess.STDOUT,
                )
                while process.poll() is None:
                    extracted = directory_size(unpacked)
                    estimate = min(680, 120 + extracted * 500 // max(installer.stat().st_size, 1))
                    progress.update(estimate, "EXTRAINDO INSTALADOR GOG", human_size(extracted))
                    time.sleep(0.3)
            if process.returncode != 0:
                installer_output = command_log.read_text(encoding="utf-8", errors="replace")
                log("\n".join(installer_output.splitlines()[-80:]))
                raise ExtractError(f"O INSTALADOR RETORNOU O ERRO {process.returncode}")
            payload = find_payload(unpacked)
            copy_tree(payload, temporary_final, progress)
            extraction_method = "makeself-noarch"
        commit_noarch(temporary_final, gamedata)
        marker.write_text(
            json.dumps(
                {
                    "format": 1,
                    "extractor": VERSION,
                    "installer": installer.name,
                    "sha256": digest,
                    "method": extraction_method,
                },
                indent=2,
            ) + "\n",
            encoding="utf-8",
        )
        if stage_parent is not None:
            shutil.rmtree(stage_parent, ignore_errors=True)
        for stale_stage in gamedata.glob(".gog-stage-*"):
            if stale_stage.is_dir() and not stale_stage.is_symlink():
                shutil.rmtree(stale_stage, ignore_errors=True)
        log(f"success: {installer.name} -> {final}")
        progress.finish(True, "JOGO PREPARADO COM SUCESSO", 1)
        return 0
    except (OSError, subprocess.SubprocessError, ExtractError) as error:
        log(f"error: {error}")
        progress.finish(False, str(error).upper(), 8)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
