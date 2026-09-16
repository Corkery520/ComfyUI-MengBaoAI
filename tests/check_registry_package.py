import ast
import importlib.util
import json
import os
import re
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path

try:
    import tomllib
except ImportError:
    import tomli as tomllib


ROOT = Path(__file__).resolve().parents[1]
EXPECTED_IDS = {
    "WANGImageAPI", "ImageGridSplit", "ImageFreeCrop", "ImageGridTilePicker",
    "WANGPromptOrganizer", "WANGPromptReader", "MengBaoEcommerceSettings",
    "MengBaoLoadImage", "MengBaoMaterialLibrary", "MengBaoSaveImage",
    "MengBaoPreviewImage", "MengBaoSmartCollage", "MengBaoImageConstraint",
    "MengBaoGlobalAPIKey", "MengBaoImageReverse", "MengBaoImageReplicaSettings",
    "MengBaoReplicaAudit",
}
SECRET_PATTERN = re.compile(
    r"sk-[A-Za-z0-9_-]{20,}|AIza[A-Za-z0-9_-]{30,}|"
    r"gh[pousr]_[A-Za-z0-9]{20,}|github_pat_[A-Za-z0-9_]{30,}|"
    r"BEGIN [A-Z ]*PRIVATE KEY"
)


def git_files(*options):
    result = subprocess.check_output(
        ["git", "ls-files", "--cached", "-z", *options], cwd=ROOT
    )
    return {path for path in result.decode("utf-8").split("\0") if path}


def check_metadata(root):
    metadata = tomllib.loads((root / "pyproject.toml").read_text(encoding="utf-8"))
    project, comfy = metadata["project"], metadata["tool"]["comfy"]
    assert project["name"] == "mengbaoai", "Registry ID must remain mengbaoai"
    assert re.fullmatch(r"\d+\.\d+\.\d+", project["version"]), "Invalid Registry version"
    assert comfy["PublisherId"] == "corkery520", "Unexpected Registry publisher"
    for text in (project["description"], comfy["DisplayName"]):
        assert "MengBaoAI" in text and "萌宝AI" in text, "Missing bilingual package search names"
    assert project["urls"]["Repository"] == "https://github.com/Corkery520/ComfyUI-MengBaoAI"
    assert metadata["tool"]["setuptools"]["dynamic"]["dependencies"]["file"] == ["requirements.txt"]
    for name in ("README.md", "LICENSE", "requirements.txt", "__init__.py"):
        assert (root / name).is_file(), f"Missing package file: {name}"
    default = json.loads((root / "data/default_prompts.json").read_text(encoding="utf-8"))
    assert not default.get("prompts"), "Default template must not contain user prompts"
    return project["version"]


def check_nodes(root):
    name = "mengbao_registry_archive_check"
    spec = importlib.util.spec_from_file_location(
        name, root / "__init__.py", submodule_search_locations=[str(root)]
    )
    package = importlib.util.module_from_spec(spec)
    sys.modules[name] = package
    spec.loader.exec_module(package)
    classes = package.NODE_CLASS_MAPPINGS
    assert set(classes) == EXPECTED_IDS, "Registry archive has missing or unexpected node IDs"
    assert set(classes) == set(package.NODE_DISPLAY_NAME_MAPPINGS), "Incomplete display mappings"
    assert package.WEB_DIRECTORY == "./web", "Invalid frontend directory"
    for language in ("en", "zh"):
        definitions = json.loads((root / "locales" / language / "nodeDefs.json").read_text(encoding="utf-8"))
        assert set(definitions) == set(classes), f"Incomplete locale node IDs: {language}"
        for node_id, node in classes.items():
            schema = node.INPUT_TYPES()
            inputs = set(schema.get("required", {})) | set(schema.get("optional", {}))
            definition = definitions[node_id]
            assert inputs <= definition["inputs"].keys(), f"Missing locale inputs: {language}/{node_id}"
            outputs = {str(index) for index in range(len(node.RETURN_TYPES))}
            assert outputs <= definition.get("outputs", {}).keys(), f"Missing locale outputs: {language}/{node_id}"
            assert node.CATEGORY.startswith("萌宝AI/"), f"Invalid category: {node_id}"
            for alias in ("MengBaoAI", "萌宝"):
                assert alias in node.SEARCH_ALIASES, f"Missing search alias: {node_id}/{alias}"


def check_archive():
    tracked = git_files()
    excluded = git_files("--ignored", "--exclude-from=.comfyignore")
    files = tracked - excluded
    assert files, "Registry archive is empty"
    # 直接使用 Git 的忽略规则解析器，与 .comfyignore 的 gitignore 语义保持一致。
    for directory in ("api", "nodes", "utils", "web", "locales", "data"):
        for path in (ROOT / directory).rglob("*"):
            if path.is_file() and "__pycache__" not in path.parts and path.suffix != ".pyc":
                assert path.relative_to(ROOT).as_posix() in files, f"Runtime file missing from archive: {path}"
    for relative in files:
        path = Path(relative)
        assert not set(path.parts) & {"tests", ".github", ".git", "node_modules", "build", "dist"}, f"Development file in archive: {relative}"
        assert not path.name.startswith(".env") and path.suffix not in {".key", ".pem", ".log", ".pyc"}, f"Unsafe package file: {relative}"
        text = (ROOT / relative).read_text(encoding="utf-8")
        assert not SECRET_PATTERN.search(text), f"Possible credential in package: {relative}"
        if path.suffix == ".py":
            for node in ast.walk(ast.parse(text, filename=relative)):
                assert not (isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id in {"eval", "exec"}), f"Registry-prohibited eval/exec: {relative}"
            assert not re.search(r"(subprocess|os\.system).*pip3?\s+install", text), f"Runtime package installation: {relative}"
    # 在临时用户目录加载构建包，不接触真实密钥，也不调用付费 API。
    with tempfile.TemporaryDirectory(prefix="mengbao-registry-check-") as directory:
        temporary = Path(directory)
        archive = temporary / "mengbaoai.zip"
        with zipfile.ZipFile(archive, "w", zipfile.ZIP_DEFLATED) as output:
            for relative in sorted(files):
                output.write(ROOT / relative, relative)
        extracted = temporary / "package"
        with zipfile.ZipFile(archive) as output:
            output.extractall(extracted)
        previous = os.environ.get("MENGBAOAI_USER_DIRECTORY")
        os.environ["MENGBAOAI_USER_DIRECTORY"] = str(temporary / "user")
        try:
            version = check_metadata(extracted)
            check_nodes(extracted)
        finally:
            if previous is None:
                os.environ.pop("MENGBAOAI_USER_DIRECTORY", None)
            else:
                os.environ["MENGBAOAI_USER_DIRECTORY"] = previous
        print(f"Registry archive passed: mengbaoai {version}, {len(EXPECTED_IDS)} nodes, {len(files)} files, {archive.stat().st_size} bytes.")


if __name__ == "__main__":
    check_archive()
