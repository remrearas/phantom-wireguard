"""
██████╗ ██╗  ██╗ █████╗ ███╗   ██╗████████╗ ██████╗ ███╗   ███╗
██╔══██╗██║  ██║██╔══██╗████╗  ██║╚══██╔══╝██╔═══██╗████╗ ████║
██████╔╝███████║███████║██╔██╗ ██║   ██║   ██║   ██║██╔████╔██║
██╔═══╝ ██╔══██║██╔══██║██║╚██╗██║   ██║   ██║   ██║██║╚██╔╝██║
██║     ██║  ██║██║  ██║██║ ╚████║   ██║   ╚██████╔╝██║ ╚═╝ ██║
╚═╝     ╚═╝  ╚═╝╚═╝  ╚═╝╚═╝  ╚═══╝   ╚═╝    ╚═════╝ ╚═╝     ╚═╝

Deployment Watcher Integration Tests

Copyright (c) 2025 Rıza Emre ARAS <r.emrearas@proton.me>
"""

import zipfile
from textwrap import dedent


def test_validate_wrapper_structure_valid(watcher, deployment_package):
    """Test wrapper validation with valid structure"""
    deployment_signed = deployment_package['deployment_signed']

    result = watcher.validate_wrapper_structure(deployment_signed)

    assert result is True


def test_validate_wrapper_structure_invalid_missing_file(watcher, temp_dirs):
    """Test wrapper validation with missing deployment.zip.asc"""
    deployment_zip = temp_dirs['base'] / 'deployment.zip'
    deployment_zip.write_text('fake content')

    # Create wrapper with only deployment.zip (missing .asc)
    invalid_wrapper = temp_dirs['quarantine'] / 'invalid.zip'
    with zipfile.ZipFile(invalid_wrapper, 'w') as zf:
        zf.write(deployment_zip, 'deployment.zip')

    result = watcher.validate_wrapper_structure(invalid_wrapper)

    assert result is False


def test_validate_wrapper_structure_invalid_extra_file(watcher, temp_dirs, deployment_package):
    """Test wrapper validation with extra unauthorized file"""
    deployment_zip = deployment_package['deployment_zip']
    deployment_sig = deployment_package['deployment_sig']

    # Create wrapper with extra file
    invalid_wrapper = temp_dirs['quarantine'] / 'invalid.zip'
    extra_file = temp_dirs['base'] / 'extra.txt'
    extra_file.write_text('unauthorized')

    with zipfile.ZipFile(invalid_wrapper, 'w') as zf:
        zf.write(deployment_zip, 'deployment.zip')
        zf.write(deployment_sig, 'deployment.zip.asc')
        zf.write(extra_file, 'extra.txt')  # Unauthorized!

    result = watcher.validate_wrapper_structure(invalid_wrapper)

    assert result is False


def test_validate_wrapper_structure_path_traversal(watcher, temp_dirs, deployment_package):
    """Test wrapper validation rejects path traversal"""
    deployment_zip = deployment_package['deployment_zip']
    deployment_sig = deployment_package['deployment_sig']

    # Create wrapper with path traversal
    evil_wrapper = temp_dirs['quarantine'] / 'evil.zip'
    with zipfile.ZipFile(evil_wrapper, 'w') as zf:
        zf.write(deployment_zip, '../deployment.zip')  # Path traversal!
        zf.write(deployment_sig, 'deployment.zip.asc')

    result = watcher.validate_wrapper_structure(evil_wrapper)

    assert result is False


def test_extract_wrapper(watcher, deployment_package):
    """Test wrapper extraction to temp directory"""
    deployment_signed = deployment_package['deployment_signed']

    verify_dir = watcher.extract_wrapper(deployment_signed)

    assert verify_dir is not None
    assert verify_dir.exists()
    assert (verify_dir / 'deployment.zip').exists()
    assert (verify_dir / 'deployment.zip.asc').exists()

    # Cleanup
    import shutil
    shutil.rmtree(verify_dir, ignore_errors=True)


def test_verify_gpg_signature_valid(watcher, deployment_package):
    """Test GPG signature verification with valid signature"""
    deployment_zip = deployment_package['deployment_zip']
    deployment_sig = deployment_package['deployment_sig']

    result = watcher.verify_gpg_signature(deployment_zip, deployment_sig)

    assert result is True


def test_verify_gpg_signature_invalid(watcher, deployment_package, temp_dirs):
    """Test GPG signature verification with invalid signature"""
    deployment_zip = deployment_package['deployment_zip']

    # Create fake signature
    fake_sig = temp_dirs['base'] / 'fake.asc'
    fake_sig.write_text(dedent("""
        -----BEGIN PGP SIGNATURE-----
        FAKE SIGNATURE DATA
        -----END PGP SIGNATURE-----
    """).strip())

    result = watcher.verify_gpg_signature(deployment_zip, fake_sig)

    assert result is False


def test_validate_deployment_zip_valid(watcher, deployment_package):
    """Test deployment.zip validation with valid structure"""
    deployment_zip = deployment_package['deployment_zip']

    result = watcher.validate_deployment_zip(deployment_zip)

    assert result is True


def test_validate_deployment_zip_missing_deployment_script(watcher, temp_dirs):
    """Test deployment.zip validation when run.sh is missing"""
    files_dir = temp_dirs['base'] / 'files'
    files_dir.mkdir()
    (files_dir / 'test.txt').write_text('test')

    # Create zip without run.sh
    invalid_zip = temp_dirs['base'] / 'invalid.zip'
    with zipfile.ZipFile(invalid_zip, 'w') as zf:
        zf.write(files_dir / 'test.txt', 'files/test.txt')

    result = watcher.validate_deployment_zip(invalid_zip)

    assert result is False


def test_validate_deployment_zip_missing_files_dir(watcher, temp_dirs):
    """Test deployment.zip validation when files/ directory is missing"""
    deployment_script = temp_dirs['base'] / 'run.sh'
    deployment_script.write_text('#!/bin/bash\n')

    # Create zip without files/ directory
    invalid_zip = temp_dirs['base'] / 'invalid.zip'
    with zipfile.ZipFile(invalid_zip, 'w') as zf:
        zf.write(deployment_script, 'run.sh')

    result = watcher.validate_deployment_zip(invalid_zip)

    assert result is False


def test_validate_deployment_zip_unauthorized_file(watcher, temp_dirs, valid_deployment_script):
    """Test deployment.zip validation rejects unauthorized files"""
    deployment_script = temp_dirs['base'] / 'run.sh'
    deployment_script.write_text(valid_deployment_script)

    files_dir = temp_dirs['base'] / 'files'
    files_dir.mkdir()
    (files_dir / 'test.txt').write_text('test')

    malicious = temp_dirs['base'] / 'malicious.sh'
    malicious.write_text('#!/bin/bash\necho evil')

    # Create zip with unauthorized file
    invalid_zip = temp_dirs['base'] / 'invalid.zip'
    with zipfile.ZipFile(invalid_zip, 'w') as zf:
        zf.write(deployment_script, 'run.sh')
        zf.write(files_dir / 'test.txt', 'files/test.txt')
        zf.write(malicious, 'malicious.sh')  # Unauthorized!

    result = watcher.validate_deployment_zip(invalid_zip)

    assert result is False


def test_extract_deployment(watcher, deployment_package, temp_dirs):
    """Test deployment extraction"""
    deployment_zip = deployment_package['deployment_zip']
    destination = temp_dirs['deployment']

    result = watcher.extract_deployment(deployment_zip, destination)

    assert result is True
    assert (destination / 'run.sh').exists()
    assert (destination / 'files').exists()
    assert (destination / 'files' / 'test1.txt').exists()
    assert (destination / 'files' / 'test2.txt').exists()
    assert (destination / 'files' / 'subdir' / 'nested.txt').exists()


def test_deployment_lock_acquire_release(watcher, temp_dirs):
    """Test deployment lock acquire and release"""
    lock_file = temp_dirs['locks'] / 'test.lock'

    lock = watcher.DeploymentLock(lock_file)

    # Acquire lock
    assert lock.acquire() is True
    assert lock_file.exists()

    # Release lock
    lock.release()
    assert not lock_file.exists()


def test_deployment_lock_already_locked(watcher, temp_dirs):
    """Test deployment lock rejects when already locked"""
    lock_file = temp_dirs['locks'] / 'test.lock'

    lock1 = watcher.DeploymentLock(lock_file)
    lock2 = watcher.DeploymentLock(lock_file)

    # First lock succeeds
    assert lock1.acquire() is True

    # Second lock fails
    assert lock2.acquire() is False

    # Cleanup
    lock1.release()


def test_full_deployment_flow(watcher, deployment_package, temp_dirs):
    """Test complete deployment flow (up to run.sh execution)"""
    deployment_dir = temp_dirs['deployment']

    # Clean deployment dir (simulating fresh start)
    if deployment_dir.exists():
        import shutil
        shutil.rmtree(deployment_dir)

    # Run the full process
    watcher.process_deployment()

    # Verify deployment completed
    assert deployment_dir.exists()
    assert (deployment_dir / 'run.sh').exists()
    assert (deployment_dir / 'files').exists()
    assert (deployment_dir / 'files' / 'test1.txt').exists()

    # Verify quarantine is cleaned
    quarantine_files = list(temp_dirs['quarantine'].iterdir())
    assert len(quarantine_files) == 0  # deployment_signed.zip should be removed

    # Verify lock is released
    assert not (temp_dirs['locks'] / 'deployment.lock').exists()


def test_process_deployment_with_valid_package(watcher, deployment_package, temp_dirs):
    """Test process_deployment() with valid package in quarantine (simulating systemd trigger)"""
    deployment_dir = temp_dirs['deployment']
    quarantine = temp_dirs['quarantine']

    # Verify deployment_signed.zip is in quarantine (created by deployment_package fixture)
    assert (quarantine / 'deployment_signed.zip').exists()

    # Run process_deployment (simulating systemd trigger)
    watcher.process_deployment()

    # Verify SUCCESS criteria:
    # 1. Deployment directory exists with extracted files
    assert deployment_dir.exists()
    assert (deployment_dir / 'run.sh').exists()
    assert (deployment_dir / 'files').exists()
    assert (deployment_dir / 'files' / 'test1.txt').exists()
    assert (deployment_dir / 'files' / 'test2.txt').exists()
    assert (deployment_dir / 'files' / 'subdir' / 'nested.txt').exists()

    # 2. Quarantine is cleaned (deployment_signed.zip removed)
    remaining = list(quarantine.iterdir())
    assert len(remaining) == 0

    # 3. Lock is released
    assert not (temp_dirs['locks'] / 'deployment.lock').exists()

    # 4. Log file contains success messages
    log_content = (temp_dirs['logs'] / 'deployment.log').read_text()
    assert '✓ Deployment completed successfully' in log_content


def test_process_deployment_with_invalid_package(watcher, temp_dirs, gpg_key):
    """Test process_deployment() rejects invalid package (missing signature)"""
    quarantine = temp_dirs['quarantine']
    deployment_dir = temp_dirs['deployment']

    # Create INVALID deployment_signed.zip (missing .asc file)
    invalid_deployment_zip = temp_dirs['base'] / 'deployment.zip'
    invalid_deployment_zip.write_text('fake content')

    invalid_wrapper = quarantine / 'deployment_signed.zip'
    with zipfile.ZipFile(invalid_wrapper, 'w') as zf:
        zf.write(invalid_deployment_zip, 'deployment.zip')
        # Missing deployment.zip.asc - INVALID!

    # Run process_deployment (simulating systemd trigger)
    watcher.process_deployment()

    # Verify REJECTION criteria:
    # 1. Deployment directory should NOT exist (or be empty if created)
    if deployment_dir.exists():
        # No run.sh should exist
        assert not (deployment_dir / 'run.sh').exists()

    # 2. Quarantine is cleaned (invalid package removed)
    remaining = list(quarantine.iterdir())
    assert len(remaining) == 0

    # 3. Lock is released
    assert not (temp_dirs['locks'] / 'deployment.lock').exists()

    # 4. Log file contains rejection messages
    log_content = (temp_dirs['logs'] / 'deployment.log').read_text()
    assert '✗ Invalid wrapper structure' in log_content


def test_process_deployment_with_invalid_gpg_signature(watcher, temp_dirs, valid_deployment_script):
    """Test process_deployment() rejects package with invalid GPG signature"""
    quarantine = temp_dirs['quarantine']
    deployment_dir = temp_dirs['deployment']

    # Create a valid-looking deployment.zip
    pkg_dir = temp_dirs['base'] / 'package'
    pkg_dir.mkdir()
    files_dir = pkg_dir / 'files'
    files_dir.mkdir()

    deployment_script = pkg_dir / 'run.sh'
    deployment_script.write_text(valid_deployment_script)
    (files_dir / 'test.txt').write_text('test')

    deployment_zip = temp_dirs['base'] / 'deployment.zip'
    with zipfile.ZipFile(deployment_zip, 'w', zipfile.ZIP_DEFLATED) as zf:
        zf.write(deployment_script, 'run.sh')
        zf.write(files_dir / 'test.txt', 'files/test.txt')

    # Create FAKE signature
    fake_sig = temp_dirs['base'] / 'deployment.zip.asc'
    fake_sig.write_text(dedent("""
        -----BEGIN PGP SIGNATURE-----
        FAKE SIGNATURE DATA
        -----END PGP SIGNATURE-----
    """).strip())

    # Create wrapper with fake signature
    invalid_wrapper = quarantine / 'deployment_signed.zip'
    with zipfile.ZipFile(invalid_wrapper, 'w') as zf:
        zf.write(deployment_zip, 'deployment.zip')
        zf.write(fake_sig, 'deployment.zip.asc')

    # Run process_deployment (simulating systemd trigger)
    watcher.process_deployment()

    # Verify REJECTION criteria:
    # 1. Deployment directory should NOT contain deployed files
    if deployment_dir.exists():
        assert not (deployment_dir / 'run.sh').exists()

    # 2. Quarantine is cleaned (invalid package removed)
    remaining = list(quarantine.iterdir())
    assert len(remaining) == 0

    # 3. Lock is released
    assert not (temp_dirs['locks'] / 'deployment.lock').exists()

    # 4. Log file contains GPG rejection messages
    log_content = (temp_dirs['logs'] / 'deployment.log').read_text()
    assert '✗ GPG signature INVALID' in log_content
    assert 'SECURITY ALERT' in log_content
