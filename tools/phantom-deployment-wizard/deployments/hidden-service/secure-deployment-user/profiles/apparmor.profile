#include <tunables/global>

# ============================================================================
# PHANTOM SECURE DEPLOYMENT USER - AppArmor Profile
# ============================================================================
# Purpose: Strict confinement for deployment-user
# - ONLY allow: SFTP upload to /securepath/incoming/
# - Deny: Command execution, file reading, system access
# - Model: Blind upload quarantine (write-only)
# ============================================================================

profile {{USERNAME}} flags=(attach_disconnected,mediate_deleted) {
  #include <abstractions/base>
  #include <abstractions/nameservice>

  # ========================================================================
  # UPLOAD QUARANTINE - Write-Only Zone (SOLE PURPOSE)
  # ========================================================================

  # Chroot base (needed for navigation)
  /securepath/ r,

  # Upload directory - WRITE ONLY (blind upload)
  /securepath/incoming/ rw,
  /securepath/incoming/** w,           # Can create/write files
  deny /securepath/incoming/** r,      # Cannot read files (blind upload)
  deny /securepath/incoming/** x,      # Cannot execute files

  # Output directory - READ ONLY (safe deployment status)
  /securepath/outputs/ r,
  /securepath/outputs/** r,

  # Explicitly deny everything else under /securepath
  deny /securepath/** rwx,
  deny /securepath/incoming/ x,

  # ========================================================================
  # SFTP-SERVER - Minimal Required Access
  # ========================================================================

  # SFTP server binary (internal-sftp uses this)
  /usr/lib/openssh/sftp-server ix,

  # Required shared libraries for sftp-server
  /lib/x86_64-linux-gnu/** mr,
  /usr/lib/x86_64-linux-gnu/** mr,
  /lib64/ld-linux-x86-64.so.* mr,

  # Alternative library paths (for different architectures)
  /lib/** mr,
  /usr/lib/** mr,

  # ========================================================================
  # SYSTEM FILES - Minimal (SFTP needs only)
  # ========================================================================

  /etc/passwd r,                       # User lookup
  /etc/group r,                        # Group lookup
  /etc/nsswitch.conf r,                # Name service
  /etc/ld.so.cache r,                  # Library cache

  # Explicitly deny sensitive files
  deny /etc/shadow* rwx,
  deny /etc/sudoers* rwx,
  deny /etc/ssh/** rwx,

  # ========================================================================
  # PROC - Minimal Self Access
  # ========================================================================

  @{PROC}/ r,
  @{PROC}/@{pid}/stat r,
  @{PROC}/@{pid}/fd/ r,
  @{PROC}/sys/kernel/ngroups_max r,

  # ========================================================================
  # DEVICES - Essential Only
  # ========================================================================

  /dev/null rw,
  /dev/zero r,
  /dev/urandom r,
  /dev/pts/* rw,

  # Deny all other devices
  deny /dev/** rwx,

  # ========================================================================
  # TEMP - SSH Session Only
  # ========================================================================

  /tmp/ r,
  owner /tmp/ssh-*/** rw,              # SSH session temp files

  # Deny other temp usage
  deny /tmp/** x,
  deny /var/tmp/** rwx,

  # ========================================================================
  # HOME - Deny Everything (chroot should handle this)
  # ========================================================================

  # In chroot, home doesn't exist, but deny anyway
  deny @{HOME}/** rwx,
  deny /home/** rwx,
  deny /root/** rwx,

  # ========================================================================
  # BINARIES - Complete Denial (No Command Execution)
  # ========================================================================

  # Deny ALL command execution
  deny /bin/** x,
  deny /sbin/** x,
  deny /usr/bin/** x,
  deny /usr/sbin/** x,
  deny /usr/local/bin/** x,

  # Explicitly deny dangerous tools
  deny /bin/sh x,
  deny /bin/bash x,
  deny /bin/dash x,
  deny /usr/bin/python* x,
  deny /usr/bin/perl x,
  deny /usr/bin/ruby x,
  deny /bin/busybox x,

  # ========================================================================
  # DEPLOYMENT SECRETS - Complete Denial
  # ========================================================================

  deny /opt/deployment-secrets/** rwx,

  # ========================================================================
  # NETWORK - SSH Only
  # ========================================================================

  network inet stream,                 # IPv4 TCP
  network inet6 stream,                # IPv6 TCP
  network unix stream,                 # Unix sockets

  # Deny other network types
  deny network raw,
  deny network packet,

  # ========================================================================
  # CAPABILITIES - Zero Privileges
  # ========================================================================

  deny capability,

  # ========================================================================
  # DANGEROUS OPERATIONS - All Denied
  # ========================================================================

  deny ptrace,
  deny mount,
  deny umount,
  deny pivot_root,
  deny dbus,
  deny change_profile,

  # ========================================================================
  # DOCKER/CONTAINER - Complete Denial
  # ========================================================================

  deny /var/run/docker.sock rwx,
  deny /run/docker.sock rwx,
  deny /var/lib/docker/** rwx,

  # ========================================================================
  # SYSTEM DIRECTORIES - Deny Access
  # ========================================================================

  deny /sys/** rwx,
  deny /boot/** rwx,
  deny /var/log/** rwx,
  deny /var/lib/** rwx,
  deny /var/spool/** rwx,
}