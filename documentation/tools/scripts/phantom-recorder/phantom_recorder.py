"""
██████╗ ██╗  ██╗ █████╗ ███╗   ██╗████████╗ ██████╗ ███╗   ███╗
██╔══██╗██║  ██║██╔══██╗████╗  ██║╚══██╔══╝██╔═══██╗████╗ ████║
██████╔╝███████║███████║██╔██╗ ██║   ██║   ██║   ██║██╔████╔██║
██╔═══╝ ██╔══██║██╔══██║██║╚██╗██║   ██║   ██║   ██║██║╚██╔╝██║
██║     ██║  ██║██║  ██║██║ ╚████║   ██║   ╚██████╔╝██║ ╚═╝ ██║
╚═╝     ╚═╝  ╚═╝╚═╝  ╚═╝╚═╝  ╚═══╝   ╚═╝    ╚═════╝ ╚═╝     ╚═╝

Phantom Recorder - Simple Asciinema Recording Automation
Automatically types commands from YAML workflow with typewriter effect

Copyright (c) 2025 Rıza Emre ARAS <r.emrearas@proton.me>
"""

import yaml
import pexpect
import time
import sys
import os
import random
import logging
from pathlib import Path
from datetime import datetime

# End marker for post-processing
END_MARKER = "___PHANTOM_END___"

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%H:%M:%S'
)
logger = logging.getLogger(__name__)


class PhantomRecorder:
    """Main recorder class for automated asciinema recordings"""

    def __init__(self, workflow_file):
        """Initialize recorder with workflow file"""
        self.workflow_file = workflow_file

        # Create recordings directory if not exists
        Path("recordings").mkdir(exist_ok=True)

        # Load workflow
        with open(workflow_file, 'r', encoding='utf-8') as f:
            self.workflow = yaml.safe_load(f)

        # Extract settings
        self.settings = self.workflow.get('settings', {})
        self.name = self.workflow.get('name', 'recording')
        self.typing_speed = self.settings.get('typing_speed', 0.05)
        self.command_delay = self.settings.get('command_delay', 1.0)
        self.initial_delay = self.settings.get('initial_delay', 2.0)
        self.clear_screen = self.settings.get('clear_screen', False)

        # Generate output filename from YAML filename
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        yaml_filename = Path(workflow_file).stem
        self.output_file = f"recordings/{yaml_filename}_{timestamp}.cast"

    def typewriter_effect(self, shell, text, speed=None):
        """Type text character by character for realistic effect"""
        if speed is None:
            speed = self.typing_speed

        for char in text:
            shell.send(char)
            # Add small random variation for more realistic typing
            actual_speed = speed + random.uniform(-0.01, 0.01)
            actual_speed = max(0.01, actual_speed)  # Minimum 10ms
            time.sleep(actual_speed)

        # Send Enter key
        shell.sendline()

    @staticmethod
    def wait_for_prompt(shell, timeout=5, expect_pattern=None):
        """
        Dynamically wait for shell prompt or activity to stop

        This method uses a more intelligent approach:
        1. If expect_pattern is provided, use it
        2. Otherwise, wait for output to stabilize (no new output for 0.5s)
        3. As fallback, use common prompt patterns
        """
        if expect_pattern:
            # Use specific pattern from YAML if provided
            try:
                shell.expect(expect_pattern, timeout=timeout)
                logger.debug(f"Matched expected pattern: {expect_pattern}")
                return True
            except pexpect.TIMEOUT:
                logger.warning(f"Pattern '{expect_pattern}' not found, falling back")

        # Dynamic detection: Wait for output to stabilize
        stable_time = 0.5  # Wait 0.5s of no output
        last_output = ""
        start_time = time.time()

        while (time.time() - start_time) < timeout:
            try:
                # Try to read any available data with short timeout
                shell.expect(pexpect.TIMEOUT, timeout=stable_time)
                # If we reach here, no new data for stable_time seconds
                current_output = shell.before if hasattr(shell, 'before') else ""
                if current_output and current_output != last_output:
                    # Output stabilized, we likely have a prompt
                    logger.debug("Output stabilized, assuming prompt reached")
                    return True
                last_output = current_output
            except pexpect.TIMEOUT:
                # Still receiving data, continue waiting
                pass
            except pexpect.EOF:
                logger.debug("EOF reached")
                return True

        # Final fallback: try common patterns
        common_prompts = [r'\$', r'#', r'>', r'%', r':', r'\]']
        try:
            shell.expect(common_prompts, timeout=0.1)
            return True
        except (pexpect.TIMEOUT, pexpect.EOF):
            logger.warning(f"No activity for {timeout}s, continuing anyway")
            return True  # Continue anyway to avoid blocking

    def record(self):
        """Main recording function"""
        logger.info(f"Starting recording: {self.name}")
        logger.info(f"Output file: {self.output_file}")
        logger.info(f"Typing speed: {self.typing_speed}s per character")

        shell = None
        try:
            # Start asciinema recording with pexpect
            cmd = f'asciinema rec -y --overwrite {self.output_file}'

            # Add terminal size if specified
            if 'cols' in self.settings:
                cmd += f" --cols {self.settings['cols']}"
            if 'rows' in self.settings:
                cmd += f" --rows {self.settings['rows']}"

            # Spawn the asciinema process
            shell = pexpect.spawn(cmd, encoding='utf-8', timeout=30)

            # Wait for shell prompt
            logger.info("Waiting for shell prompt")
            PhantomRecorder.wait_for_prompt(shell)

            # Initial delay
            if self.initial_delay > 0:
                logger.info(f"Initial delay: {self.initial_delay}s")
                time.sleep(self.initial_delay)

            # Clear screen if requested
            if self.clear_screen:
                logger.info("Clearing screen")
                shell.sendline('clear')
                PhantomRecorder.wait_for_prompt(shell)
                time.sleep(0.5)

            # Execute commands from workflow
            commands = self.workflow.get('commands', [])
            total = len(commands)

            for i, cmd in enumerate(commands, 1):
                text = cmd.get('text', '')
                delay = cmd.get('delay', self.command_delay)
                speed = cmd.get('speed', self.typing_speed)
                expect_pattern = cmd.get('expect', None)  # Custom expect pattern

                # Log progress with action-based format
                if text.startswith('#'):
                    logger.info(f"[{i}/{total}] Comment: {text}")
                elif text == "":
                    logger.info(f"[{i}/{total}] Press Enter")
                else:
                    truncated = text[:50] + '...' if len(text) > 50 else text
                    logger.info(f"[{i}/{total}] Type \"{truncated}\" and press Enter")

                # Type the command with typewriter effect
                self.typewriter_effect(shell, text, speed)

                # Wait for command to complete
                if not text.startswith('#'):  # Don't wait for prompt after comments
                    PhantomRecorder.wait_for_prompt(
                        shell,
                        timeout=delay + 5,
                        expect_pattern=expect_pattern
                    )

                # Post-command delay
                if delay > 0:
                    time.sleep(delay)

            # End recording
            logger.info("Ending recording")
            time.sleep(0.5)

            # Send end marker for post-processing
            shell.sendline(f'echo "{END_MARKER}"')
            time.sleep(0.3)

            # Try multiple methods to end the recording
            try:
                # First try exit command
                shell.sendline('exit')
                time.sleep(0.5)
                # Then send Ctrl+D
                shell.sendcontrol('d')
                # Wait for EOF with timeout
                shell.expect(pexpect.EOF, timeout=2)
            except pexpect.TIMEOUT:
                logger.warning("Normal exit timeout, forcing termination")
                # Force terminate if needed
                shell.terminate(force=True)
            except pexpect.EOF:
                logger.debug("Recording ended with EOF")

            # Post-process to remove end marker and everything after
            self.post_process()

            logger.info("Recording completed successfully")
            logger.info(f"Saved to: {self.output_file}")

            print("")
            print(f"Recording saved: {self.output_file}")
            print(f"To play: asciinema play {self.output_file}")
            print("")

            return True

        except Exception as e:
            logger.error(f"Error during recording: {e}")

            # Try to show more details if available
            if hasattr(shell, 'before'):
                logger.debug(f"Last output: {shell.before}")
            if hasattr(shell, 'buffer'):
                logger.debug(f"Buffer: {shell.buffer}")

            # Try to cleanup
            if shell:
                try:
                    shell.terminate(force=True)
                except (AttributeError, OSError):
                    pass

            return False

    def post_process(self):
        """Remove end marker and everything after it from the recording"""
        try:
            with open(self.output_file, 'r', encoding='utf-8') as f:
                lines = f.readlines()

            # Find the line containing the end marker
            marker_index = None
            for i, line in enumerate(lines):
                if END_MARKER in line:
                    marker_index = i
                    break

            if marker_index is not None:
                # Keep only lines before the marker
                lines = lines[:marker_index]

                with open(self.output_file, 'w', encoding='utf-8') as f:
                    f.writelines(lines)

                logger.info(f"Post-process: Removed {END_MARKER} and trailing content")
            else:
                logger.debug("Post-process: End marker not found, skipping")

        except Exception as e:
            logger.warning(f"Post-process failed: {e}")


def main():
    """Main entry point"""
    # Configure console output for errors
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.ERROR)

    # Check arguments
    if len(sys.argv) < 2:
        print("Usage: python phantom_recorder.py <workflow.yaml>")
        print("Example: python phantom_recorder.py workflows/example.yaml")
        sys.exit(1)

    workflow_file = sys.argv[1]

    # Check if workflow file exists
    if not os.path.exists(workflow_file):
        logger.error(f"Workflow file not found: {workflow_file}")
        sys.exit(1)

    # Check dependencies
    try:
        import yaml
        import pexpect
    except ImportError as e:
        logger.error(f"Missing dependency: {e}")
        print("Please install requirements: pip install -r requirements.txt")
        sys.exit(1)

    # Check if asciinema is installed
    if os.system('which asciinema > /dev/null 2>&1') != 0:
        logger.error("asciinema not found")
        print("Please install asciinema:")
        print("  pip install asciinema")
        sys.exit(1)

    # Create and run recorder
    recorder = PhantomRecorder(workflow_file)
    success = recorder.record()

    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
