"""Create a source-only kit; never include local state, caches, SDKs or signing keys."""
import hashlib
import pathlib
import re
import zipfile

root = pathlib.Path(__file__).resolve().parents[1]
version = re.search(r"versionName '([^']+)'", (root / 'app/build.gradle').read_text()).group(1)
output = root.parent / 'deliverables' / f'Inventory-Android-v{version}-Source-Build-Kit.zip'
output.parent.mkdir(exist_ok=True)
exclude = {'.git', '.gradle', 'build', '__pycache__'}
with zipfile.ZipFile(output, 'w', zipfile.ZIP_DEFLATED) as archive:
    for path in sorted(root.rglob('*')):
        if not path.is_file():
            continue
        rel = path.relative_to(root)
        if any(part in exclude for part in rel.parts) or path.name == 'local.properties':
            continue
        if path.suffix in {'.jks', '.keystore', '.p12', '.pfx', '.key', '.pass', '.enc', '.dlinv', '.apk'}:
            raise RuntimeError(f'Unexpected sensitive/binary artifact in source: {rel}')
        archive.write(path, pathlib.Path('Inventory-Android') / rel)
with zipfile.ZipFile(output) as archive:
    assert archive.testzip() is None
    names = archive.namelist()
    assert any(n.endswith('/gradle-wrapper.jar') for n in names)
    assert any(n.endswith('/MainActivity.java') for n in names)
print(f'{output.name}: {output.stat().st_size} bytes')
print(hashlib.sha256(output.read_bytes()).hexdigest())
