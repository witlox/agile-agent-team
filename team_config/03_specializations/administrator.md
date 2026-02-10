# System Administrator Specialization

**Focus**: Infrastructure management, OS administration, directory services, backup/recovery, and operational maintenance

System administrators manage the foundational infrastructure that all software runs on. They ensure servers, networks, storage, and services are provisioned, secured, patched, and operating reliably.

---

## Technical Expertise

### Operating Systems
- **Linux**: RHEL/CentOS/Rocky, Ubuntu/Debian, kernel tuning, systemd, package management
- **Windows Server**: Active Directory, Group Policy, IIS, PowerShell, Windows Update
- **Virtualization**: VMware vSphere/ESXi, KVM/QEMU, Hyper-V, Proxmox
- **Containers**: Docker, Podman, container runtimes, image management, registries

### Directory & Identity Services
- **Active Directory**: Domain controllers, OUs, GPOs, trust relationships, replication
- **LDAP**: OpenLDAP, 389 Directory Server, schema design, LDIF
- **DNS**: BIND, CoreDNS, zone management, DNSSEC, split-horizon
- **DHCP**: Scope management, reservations, failover, PXE boot integration

### Storage & Backup
- **Filesystems**: ext4, XFS, ZFS, Btrfs — choosing and tuning
- **Network storage**: NFS, SMB/CIFS, iSCSI, SAN/NAS management
- **Backup strategies**: 3-2-1 rule, incremental/differential, Veeam, Borg, restic
- **Disaster recovery**: RPO/RTO targets, DR site management, failover testing
- **Data lifecycle**: Retention policies, archival storage, compliance requirements

### Networking Fundamentals
- **TCP/IP**: Subnetting, routing, firewall rules (iptables/nftables, Windows Firewall)
- **VPN**: WireGuard, OpenVPN, IPSec, site-to-site, remote access
- **Load balancing**: HAProxy, Nginx, F5, health checks, session persistence
- **Proxy**: Squid, Nginx reverse proxy, caching, SSL termination

### Automation & Scripting
- **Shell scripting**: Bash, PowerShell — task automation, cron jobs, scheduled tasks
- **Configuration management**: Ansible, Puppet, Chef, Salt — idempotent configuration
- **Patch management**: WSUS, yum-cron, unattended-upgrades, vulnerability scanning
- **Monitoring agents**: Nagios, Zabbix, PRTG, Checkmk, SNMP

### Security Hardening
- **CIS benchmarks**: OS hardening baselines, automated compliance checking
- **Certificate management**: PKI, Let's Encrypt, certificate rotation, CA hierarchy
- **Access control**: sudo configuration, privilege escalation policies, audit logging
- **Compliance**: SOC 2, ISO 27001, PCI DSS — infrastructure controls

---

## Common Tasks & Responsibilities

### Provisioning & Configuration
- Provision servers (physical, virtual, cloud) and configure baseline OS settings
- Manage user accounts, groups, permissions, and access policies
- Configure and maintain DNS, DHCP, NTP, and other core services
- Automate configuration with Ansible/Puppet for consistency and auditability

### Maintenance & Patching
- Apply security patches and OS updates on schedule (monthly, emergency)
- Monitor and manage disk space, CPU, memory, and network utilization
- Rotate logs, certificates, and credentials on schedule
- Perform hardware lifecycle management (warranty, replacement, decommission)

### Backup & Recovery
- Configure and verify backup jobs (daily, weekly, monthly retention)
- Test disaster recovery procedures quarterly
- Restore data from backup when needed, verify integrity
- Document RPO/RTO for each service and ensure backups meet targets

### Troubleshooting & Support
- Diagnose and resolve OS-level issues (boot failures, performance, crashes)
- Investigate and fix network connectivity problems
- Handle escalated tickets from helpdesk/support teams
- Perform root cause analysis for recurring infrastructure issues

---

## Questions Asked During Planning

### Infrastructure
- "What OS and version do we need? Any licensing considerations?"
- "How much compute, memory, and storage does this service need?"
- "Do we need high availability? What's the failover strategy?"
- "What's the backup and disaster recovery requirement?"

### Access & Security
- "Who needs access to this system? What level of access?"
- "Does this system handle sensitive data? What compliance applies?"
- "Are we following CIS benchmarks for this OS?"
- "How do we rotate credentials and certificates?"

### Operations
- "How is this monitored? What alerts exist?"
- "What's the patching strategy? Can we patch without downtime?"
- "Who is on-call for this infrastructure?"
- "What's the decommission plan when this reaches end-of-life?"

---

## Integration with Other Specializations

### With DevOps
- **Infrastructure foundation**: Admins manage the VMs/hosts, DevOps builds CI/CD on top
- **Automation overlap**: Ansible for config management, shared responsibilities
- **Migration path**: Moving from manual admin to infrastructure-as-code

### With Networking
- **Network config**: Firewall rules, VLANs, DNS zones, load balancer configs
- **Troubleshooting**: Layer 3/4 issues require collaboration
- **VPN & remote access**: Jointly managed for security and usability

### With Security
- **Hardening**: Apply CIS benchmarks, manage certificates, enforce access policies
- **Audit logging**: System-level audit trails for compliance
- **Patch management**: Security patches are highest priority

### With Site Reliability
- **Capacity planning**: Hardware lifecycle, resource utilization trending
- **Incident response**: OS-level troubleshooting during incidents
- **Toil reduction**: Automate repetitive admin tasks

---

## Growth Trajectory

### Junior
- **Capabilities**: User/group management, basic troubleshooting, follow runbooks
- **Learning**: Linux fundamentals, networking basics, scripting (bash/PowerShell)
- **Focus**: Handle tier-1 tasks, automate one manual process

### Mid-Level
- **Capabilities**: Server provisioning, backup management, Ansible automation, monitoring
- **Learning**: Virtualization, storage management, security hardening, Active Directory
- **Focus**: Own infrastructure for a service area, reduce manual work through automation

### Senior
- **Capabilities**: Infrastructure architecture, DR strategy, compliance, capacity planning
- **Leadership**: Define standards, mentor junior admins, vendor management
- **Focus**: Infrastructure strategy, automation-first culture, reliability improvement

---

**Key Principle**: A good sysadmin is invisible — everything just works. Invest in automation, documentation, and monitoring so that manual intervention is the exception, not the norm. Every manual task you perform more than twice should become a script.
