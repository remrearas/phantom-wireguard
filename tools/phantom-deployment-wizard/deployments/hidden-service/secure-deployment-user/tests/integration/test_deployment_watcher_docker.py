"""
██████╗ ██╗  ██╗ █████╗ ███╗   ██╗████████╗ ██████╗ ███╗   ███╗
██╔══██╗██║  ██║██╔══██╗████╗  ██║╚══██╔══╝██╔═══██╗████╗ ████║
██████╔╝███████║███████║██╔██╗ ██║   ██║   ██║   ██║██╔████╔██║
██╔═══╝ ██╔══██║██╔══██║██║╚██╗██║   ██║   ██║   ██║██║╚██╔╝██║
██║     ██║  ██║██║  ██║██║ ╚████║   ██║   ╚██████╔╝██║ ╚═╝ ██║
╚═╝     ╚═╝  ╚═╝╚═╝  ╚═╝╚═╝  ╚═══╝   ╚═╝    ╚═════╝ ╚═╝     ╚═╝

Deployment Watcher Docker Integration Tests

Copyright (c) 2025 Rıza Emre ARAS <r.emrearas@proton.me>
"""

import pytest
import logging
from pathlib import Path

logger = logging.getLogger(__name__)


@pytest.mark.docker
@pytest.mark.integration
@pytest.mark.dependency()
def test_docker_container_starts(shared_docker_container, docker_available):
    """Test that Docker container starts successfully with systemd."""
    if not docker_available:
        pytest.skip("Docker not available")

    assert shared_docker_container is not None, "Docker container should be initialized"
    assert shared_docker_container.container is not None, "Container should be running"

    # Verify systemd is running
    result = shared_docker_container.exec_command("systemctl --version")
    assert result['success'], "systemd should be available"
    assert 'systemd' in result['output'].lower(), "systemd version should be displayed"

    logger.info("Docker container with systemd is ready")


@pytest.mark.docker
@pytest.mark.integration
@pytest.mark.dependency(depends=["test_docker_container_starts"])
def test_docker_container_directories(shared_docker_container):
    """Test that required directories exist in container."""
    # Check quarantine directory
    result = shared_docker_container.exec_command("sh -c 'test -d /securepath/incoming && echo exists'")
    assert 'exists' in result['output'], "/securepath/incoming should exist"

    # Check deployment directory
    result = shared_docker_container.exec_command("sh -c 'test -d /tmp/deployment && echo exists'")
    assert 'exists' in result['output'], "/tmp/deployment should exist"

    # Check secrets directory
    result = shared_docker_container.exec_command("sh -c 'test -d /opt/deployment-secrets && echo exists'")
    assert 'exists' in result['output'], "/opt/deployment-secrets should exist"

    logger.info("All required directories exist in container")


@pytest.mark.docker
@pytest.mark.integration
@pytest.mark.dependency(depends=["test_docker_container_directories"])
def test_docker_container_python_available(shared_docker_container):
    """Test that Python3 and python-gnupg are available in container."""
    # Check Python3
    result = shared_docker_container.exec_command("python3 --version")
    assert result['success'], "Python3 should be installed"
    assert 'Python 3' in result['output'], "Should show Python 3.x version"

    # Check python-gnupg module
    result = shared_docker_container.exec_command("python3 -c 'import gnupg; print(gnupg.__version__)'")
    assert result['success'], "python-gnupg should be importable"

    logger.info("Python3 and python-gnupg are available in container")


@pytest.mark.docker
@pytest.mark.integration
@pytest.mark.dependency(depends=["test_docker_container_python_available"])
def test_docker_container_gpg_available(shared_docker_container):
    """Test that GPG is installed and working in container."""
    # Check GPG availability
    result = shared_docker_container.exec_command("which gpg")
    assert result['success'], "GPG should be installed"
    assert '/gpg' in result['output'], "GPG binary path should be shown"

    # Check GPG version
    result = shared_docker_container.exec_command("gpg --version")
    assert result['success'], "GPG version should be displayed"
    assert 'GnuPG' in result['output'], "Should show GnuPG version"

    logger.info("GPG is available and working in container")


@pytest.mark.docker
@pytest.mark.integration
@pytest.mark.dependency(depends=["test_docker_container_gpg_available"])
def test_setup_gpg_environment(shared_docker_container, shared_gpg_key):
    """
    Setup GPG environment for deployment-watcher.py

    Uses session-wide shared_gpg_key to:
    1. Import public key to container at /opt/deployment-secrets/gpg
    2. Keep private key available on host for signing test packages
    """
    logger.info("Setting up GPG environment for deployment-watcher...")

    # Get public key from shared session fixture
    pubkey = shared_gpg_key['pubkey']
    logger.info(f"✓ Using session GPG key: {shared_gpg_key['key_id']}")

    # Import to container using python-gnupg
    gpg_home = "/opt/deployment-secrets/gpg"

    # Create GPG home in container
    result = shared_docker_container.exec_command(f"mkdir -p {gpg_home} && chmod 700 {gpg_home}")
    assert result['success'], f"Failed to create GPG home: {result['output']}"

    # Import using python-gnupg in container
    import_cmd = (
        f'python3 -c "import gnupg; '
        f'gpg = gnupg.GPG(gnupghome=\\"{gpg_home}\\"); '
        f'result = gpg.import_keys(\\"\\"\\"'
        f'{pubkey}'
        f'\\"\\"\\"); '
        f'print(\\"OK\\" if result.count else \\"FAILED\\")"'
    )

    result = shared_docker_container.exec_command(import_cmd)
    assert result['success'] and 'OK' in result['output'], f"Failed to import key: {result['output']}"

    logger.info(f"✓ Key imported to container: {gpg_home}")
    logger.info("✓ GPG ready for deployment-watcher.py")


@pytest.mark.docker
@pytest.mark.integration
@pytest.mark.dependency(depends=["test_setup_gpg_environment"])
def test_install_deployment_watcher_service(shared_docker_container):
    """
    Install deployment-watcher.py and systemd services in container

    Following create.sh install_watcher_service and install_remover_service functions:
    1. Copy deployment-watcher.py to /usr/local/bin/
    2. Copy watcher systemd units to /etc/systemd/system/
    3. Copy remover systemd units to /etc/systemd/system/
    4. Enable and start both services
    """
    logger.info("Installing deployment-watcher and deployment-remover systemd services...")

    # Get paths
    tests_dir = Path(__file__).parent.parent  # tests/
    root_dir = tests_dir.parent  # secure-deployment-user/
    scripts_dir = root_dir / 'scripts'
    systemd_dir = root_dir / 'systemd'
    watcher_script = scripts_dir / 'deployment-watcher.py'

    # Verify files exist
    assert watcher_script.exists(), f"deployment-watcher.py not found: {watcher_script}"
    assert systemd_dir.exists(), f"systemd directory not found: {systemd_dir}"

    # ========================================================================
    # WATCHER SERVICE
    # ========================================================================
    logger.info("Installing deployment-watcher service...")

    # Step 1: Copy deployment-watcher.py using Docker API
    success = shared_docker_container.copy_file_to_container(
        watcher_script,
        "/usr/local/bin/deployment-watcher.py"
    )
    assert success, "Failed to copy deployment-watcher.py"

    result = shared_docker_container.exec_command("chmod 755 /usr/local/bin/deployment-watcher.py")
    assert result['success'], f"Failed to set permissions: {result['output']}"

    # Step 2: Copy watcher systemd units using Docker API
    watcher_path_unit = systemd_dir / 'deployment-watcher.path'
    watcher_service_unit = systemd_dir / 'deployment-watcher.service'

    assert watcher_path_unit.exists(), f"deployment-watcher.path not found: {watcher_path_unit}"
    assert watcher_service_unit.exists(), f"deployment-watcher.service not found: {watcher_service_unit}"

    # Copy watcher .path unit
    success = shared_docker_container.copy_file_to_container(
        watcher_path_unit,
        "/etc/systemd/system/deployment-watcher.path"
    )
    assert success, "Failed to copy deployment-watcher.path"

    # Copy watcher .service unit
    success = shared_docker_container.copy_file_to_container(
        watcher_service_unit,
        "/etc/systemd/system/deployment-watcher.service"
    )
    assert success, "Failed to copy deployment-watcher.service"
    logger.info("✓ Watcher systemd units copied")

    # ========================================================================
    # REMOVER SERVICE
    # ========================================================================
    logger.info("Installing deployment-remover service...")

    # Step 3: Copy remover systemd units using Docker API
    remover_path_unit = systemd_dir / 'deployment-remover.path'
    remover_service_unit = systemd_dir / 'deployment-remover.service'

    assert remover_path_unit.exists(), f"deployment-remover.path not found: {remover_path_unit}"
    assert remover_service_unit.exists(), f"deployment-remover.service not found: {remover_service_unit}"

    # Copy remover .path unit
    success = shared_docker_container.copy_file_to_container(
        remover_path_unit,
        "/etc/systemd/system/deployment-remover.path"
    )
    assert success, "Failed to copy deployment-remover.path"

    # Copy remover .service unit
    success = shared_docker_container.copy_file_to_container(
        remover_service_unit,
        "/etc/systemd/system/deployment-remover.service"
    )
    assert success, "Failed to copy deployment-remover.service"
    logger.info("✓ Remover systemd units copied")

    # ========================================================================
    # ENABLE AND START SERVICES
    # ========================================================================
    logger.info("Enabling and starting services...")

    # Reload systemd daemon
    result = shared_docker_container.exec_command("systemctl daemon-reload")
    assert result['success'], f"Failed to reload systemd: {result['output']}"
    logger.info("✓ Reloaded systemd")

    # Enable and start watcher
    result = shared_docker_container.exec_command("systemctl enable deployment-watcher.path")
    assert result['success'], f"Failed to enable deployment-watcher.path: {result['output']}"
    logger.info("✓ Enabled deployment-watcher.path")

    result = shared_docker_container.exec_command("systemctl start deployment-watcher.path")
    assert result['success'], f"Failed to start deployment-watcher.path: {result['output']}"
    logger.info("✓ Started deployment-watcher.path")

    # Enable and start remover
    result = shared_docker_container.exec_command("systemctl enable deployment-remover.path")
    assert result['success'], f"Failed to enable deployment-remover.path: {result['output']}"
    logger.info("✓ Enabled deployment-remover.path")

    result = shared_docker_container.exec_command("systemctl start deployment-remover.path")
    assert result['success'], f"Failed to start deployment-remover.path: {result['output']}"
    logger.info("✓ Started deployment-remover.path")

    # ========================================================================
    # VERIFY SERVICES ARE ACTIVE
    # ========================================================================
    logger.info("Verifying services are active...")

    # Verify watcher is active
    result = shared_docker_container.exec_command("systemctl is-active deployment-watcher.path")
    assert 'active' in result['output'], f"deployment-watcher.path is not active: {result['output']}"
    logger.info("✓ deployment-watcher.path is ACTIVE")

    # Verify remover is active
    result = shared_docker_container.exec_command("systemctl is-active deployment-remover.path")
    assert 'active' in result['output'], f"deployment-remover.path is not active: {result['output']}"
    logger.info("✓ deployment-remover.path is ACTIVE")

    logger.info("✓ Both deployment-watcher and deployment-remover services installed and running")


@pytest.mark.docker
@pytest.mark.integration
@pytest.mark.dependency(depends=["test_setup_gpg_environment"])
def test_invalid_deployment_package_handling(shared_docker_container):
    """
    Test deployment-remover and deployment-watcher handling of invalid packages

    Scenario 1: Wrong filename → deployment-remover should delete it
    Scenario 2: Correct filename but invalid GPG signature → deployment-watcher should reject and log GPG error
    """
    import tempfile
    import time
    import zipfile
    from textwrap import dedent

    logger.info("Testing invalid deployment package handling...")

    quarantine_dir = Path(shared_docker_container.host_quarantine_dir)

    # ========================================================================
    # SCENARIO 1: Wrong filename - remover should delete it
    # ========================================================================
    logger.info("Scenario 1: Testing wrong filename (remover service)...")

    # Create file with wrong name
    wrong_filename_file = quarantine_dir / 'invalid_file.zip'
    wrong_filename_file.write_text("This file has wrong name - should be deleted by remover\n")
    logger.info(f"✓ Created file with wrong name: {wrong_filename_file.name}")

    # Wait for deployment-remover.path to detect and delete
    time.sleep(3)

    # Verify file was deleted by remover
    assert not wrong_filename_file.exists(), "Wrong filename should be deleted by deployment-remover"
    logger.info("✓ File with wrong name successfully deleted by remover service")

    # Verify remover service still active
    result = shared_docker_container.exec_command("systemctl is-active deployment-remover.path")
    assert 'active' in result['output'], "deployment-remover.path should still be active"
    logger.info("✓ deployment-remover.path still active after cleanup")

    # ========================================================================
    # SCENARIO 2: Correct filename but invalid GPG signature - watcher should reject
    # ========================================================================
    logger.info("Scenario 2: Testing invalid GPG signature (watcher service)...")

    # Create a valid-looking deployment.zip structure
    pkg_dir = Path(tempfile.mkdtemp(prefix='invalid-gpg-'))

    try:
        # Create minimal deployment.zip
        deployment_script = dedent("""\
            #!/bin/bash
            echo "Test deployment"
            exit 0
        """).strip()

        deployment_script_file = pkg_dir / 'run.sh'
        deployment_script_file.write_text(deployment_script)

        files_dir = pkg_dir / 'files'
        files_dir.mkdir()
        (files_dir / 'test.txt').write_text('test content\n')

        deployment_zip = pkg_dir / 'deployment.zip'
        with zipfile.ZipFile(deployment_zip, 'w', zipfile.ZIP_DEFLATED) as zf:
            zf.write(deployment_script_file, 'run.sh')
            zf.write(files_dir / 'test.txt', 'files/test.txt')
        logger.info("✓ Created deployment.zip")

        # Create FAKE signature
        fake_sig = pkg_dir / 'deployment.zip.asc'
        fake_sig.write_text(dedent("""\
            -----BEGIN PGP SIGNATURE-----
            FAKE SIGNATURE DATA - THIS IS INVALID
            -----END PGP SIGNATURE-----
        """).strip())
        logger.info("✓ Created fake GPG signature")

        # Create wrapper with correct name but invalid signature
        deployment_signed = quarantine_dir / 'deployment_signed.zip'
        with zipfile.ZipFile(deployment_signed, 'w', zipfile.ZIP_DEFLATED) as zf:
            zf.write(deployment_zip, 'deployment.zip')
            zf.write(fake_sig, 'deployment.zip.asc')
        logger.info(f"✓ Created {deployment_signed.name} with invalid signature")

        # Wait for deployment-watcher.path to detect and process
        logger.info("Waiting for watcher to process package with invalid signature...")
        time.sleep(5)

        # Verify watcher service still active
        result = shared_docker_container.exec_command("systemctl is-active deployment-watcher.path")
        assert 'active' in result['output'], "deployment-watcher.path should still be active"
        logger.info("✓ deployment-watcher.path still active after rejection")

        # Check journalctl for GPG rejection
        result = shared_docker_container.exec_command(
            "journalctl -u deployment-watcher.service --no-pager -n 100"
        )
        assert result['success'], "Failed to read journalctl logs"

        log_output = result['output']

        # Verify GPG verification was attempted
        assert 'deployment_signed.zip' in log_output, "Watcher should detect the package"

        # Verify GPG error was logged
        gpg_error_indicators = [
            'GPG signature INVALID',
            'SECURITY ALERT',
            'signature',
            'invalid'
        ]
        found_gpg_error = any(indicator in log_output for indicator in gpg_error_indicators)
        assert found_gpg_error, "Should log GPG signature rejection"
        logger.info("✓ Invalid GPG signature properly rejected and logged")

        # Verify package was removed (cleanup in process_deployment)
        assert not deployment_signed.exists(), "Invalid package should be removed after rejection"
        logger.info("✓ Invalid package removed after rejection")

        logger.info(
            "✓ Both scenarios handled correctly: remover deletes wrong names, watcher rejects invalid signatures")

    finally:
        # Cleanup
        import shutil
        if pkg_dir.exists():
            shutil.rmtree(pkg_dir, ignore_errors=True)
        if (quarantine_dir / 'deployment_signed.zip').exists():
            (quarantine_dir / 'deployment_signed.zip').unlink(missing_ok=True)


@pytest.mark.docker
@pytest.mark.integration
@pytest.mark.dependency(depends=["test_invalid_deployment_package_handling"])
def test_valid_deployment_package_handling(shared_docker_container, shared_gpg_key):
    """
    Test deployment-watcher.py handling of valid signed packages

    This tests the complete deployment flow:
    1. Create valid deployment package (run.sh + files)
    2. Sign with shared_gpg_key
    3. Create wrapper (deployment_signed.zip)
    4. Copy to /securepath/incoming (triggers systemd.path)
    5. Verify successful deployment in journalctl logs
    """
    import tempfile
    import time
    import zipfile
    from textwrap import dedent

    logger.info("Testing valid deployment package handling...")

    # Create temporary package directory
    pkg_dir = Path(tempfile.mkdtemp(prefix='valid-package-'))

    # Initialize target_file - MUST be exactly "deployment_signed.zip"
    quarantine_dir = Path(shared_docker_container.host_quarantine_dir)
    target_file = quarantine_dir / 'deployment_signed.zip'

    try:
        # Step 1: Create run.sh
        deployment_script = dedent("""\
            #!/bin/bash
            # Test deployment script
            echo "Deployment script started"
            exit 0
        """).strip()

        deployment_script_file = pkg_dir / 'run.sh'
        deployment_script_file.write_text(deployment_script)
        logger.info("✓ Created run.sh")

        # Step 2: Create test files directory
        files_dir = pkg_dir / 'files'
        files_dir.mkdir()
        (files_dir / 'test1.txt').write_text('Test file 1\n')
        (files_dir / 'test2.txt').write_text('Test file 2\n')
        (files_dir / 'config.json').write_text('{"test": true}\n')

        # Create subdirectory with nested file
        subdir = files_dir / 'subdir'
        subdir.mkdir()
        (subdir / 'nested.txt').write_text('Nested file content\n')
        logger.info("✓ Created test files")

        # Step 3: Create deployment.zip
        deployment_zip = pkg_dir / 'deployment.zip'
        with zipfile.ZipFile(deployment_zip, 'w', zipfile.ZIP_DEFLATED) as zf:
            zf.write(deployment_script_file, 'run.sh')
            for file in files_dir.rglob('*'):
                if file.is_file():
                    arcname = f"files/{file.relative_to(files_dir)}"
                    zf.write(file, arcname)
        logger.info("✓ Created deployment.zip")

        # Step 4: Sign deployment.zip with shared_gpg_key
        deployment_sig = pkg_dir / 'deployment.zip.asc'
        gpg = shared_gpg_key['gpg']

        with open(deployment_zip, 'rb') as f:
            signed = gpg.sign_file(
                f,
                keyid=shared_gpg_key['key_id'],
                detach=True,
                output=str(deployment_sig)
            )

        assert signed, f"GPG signing failed"
        logger.info(f"✓ Signed deployment.zip with key {shared_gpg_key['key_id']}")

        # Step 5: Create wrapper (deployment_signed.zip)
        deployment_signed = pkg_dir / 'deployment_signed.zip'
        with zipfile.ZipFile(deployment_signed, 'w', zipfile.ZIP_DEFLATED) as zf:
            zf.write(deployment_zip, 'deployment.zip')
            zf.write(deployment_sig, 'deployment.zip.asc')
        logger.info("✓ Created deployment_signed.zip wrapper")

        # Step 6: Copy to quarantine directory (triggers systemd)
        deployment_signed.rename(target_file)
        logger.info(f"✓ Placed valid package in quarantine: {target_file.name}")

        # Step 7: Wait for systemd to process
        logger.info("Waiting for systemd to process valid package...")
        time.sleep(5)  # Longer wait for full deployment

        # Step 8: Check service status
        result = shared_docker_container.exec_command("systemctl is-active deployment-watcher.path")
        assert 'active' in result['output'], "Service should still be active after valid package"
        logger.info("✓ deployment-watcher.path still active after valid package")

        # Step 9: Check journalctl for successful deployment
        result = shared_docker_container.exec_command(
            "journalctl -u deployment-watcher.service --no-pager -n 100"
        )
        assert result['success'], "Failed to read journalctl logs"

        log_output = result['output']
        logger.info("Checking journalctl logs for successful deployment...")

        # Verify watcher detected the package
        assert 'deployment_signed.zip' in log_output, "Watcher should detect the deployment package"

        # Verify successful processing indicators
        success_indicators = [
            'signature verified',
            'deployment successful',
            'extracted',
            'completed'
        ]
        found_success = any(indicator in log_output.lower() for indicator in success_indicators)
        assert found_success, "Should log successful deployment"

        # Verify no errors for this package
        if 'deployment_signed.zip' in log_output:
            # Get lines related to this specific package
            package_lines = [line for line in log_output.split('\n')
                             if 'deployment_signed.zip' in line.lower()]
            for line in package_lines:
                # Should not have error keywords in lines about valid package
                assert not any(err in line.lower() for err in ['error', 'failed']), \
                    f"Valid package should not have errors: {line}"

        logger.info("✓ Valid package processed successfully")
        logger.info("✓ Deployment completed without errors")

    finally:
        # Cleanup
        import shutil
        if pkg_dir.exists():
            shutil.rmtree(pkg_dir, ignore_errors=True)
        if target_file.exists():
            target_file.unlink(missing_ok=True)
