"""Test: Verify all Platinum tier modules import correctly."""
from src.platinum.agent_identity import AgentRole, check_permission, require_permission
print("1. Agent Identity: OK")

from src.platinum.vault_structure import ensure_platinum_vault_structure, DOMAINS
print(f"2. Vault Structure: OK (domains={DOMAINS})")

from src.platinum.domain_router import detect_platinum_domain, route_to_domain_folder
print(f"3. Domain Router: OK (email test={detect_platinum_domain('reply to email', 'EMAIL_123.md')})")

from src.platinum.claim_manager import ClaimManager
print("4. Claim Manager: OK")

from src.platinum.vault_sync import VaultSync
print("5. Vault Sync: OK")

from src.platinum.signal_bus import write_signal, read_and_consume_signals
print("6. Signal Bus: OK")

from src.platinum.watchdog import is_process_running, check_sync_freshness
print("7. Watchdog: OK")

# Test permissions
cloud_can_draft = check_permission(AgentRole.CLOUD, "can_draft")
cloud_can_send = check_permission(AgentRole.CLOUD, "can_send")
local_can_send = check_permission(AgentRole.LOCAL, "can_send")
local_can_approve = check_permission(AgentRole.LOCAL, "can_approve")
print(f"8. Permissions: Cloud draft={cloud_can_draft}, Cloud send={cloud_can_send}, Local send={local_can_send}, Local approve={local_can_approve}")

# Test domain routing
tests = [
    ("EMAIL_123.md", "send reply to john", "email"),
    ("FACEBOOK_post.md", "post about AI", "social"),
    ("INVOICE_001.md", "create invoice", "accounting"),
    ("task.md", "write a report", "general"),
]
all_pass = True
for filename, content, expected in tests:
    result = detect_platinum_domain(content, filename)
    status = "OK" if result == expected else "FAIL"
    if result != expected:
        all_pass = False
    print(f"   {filename} → {result} ({status})")

print()
if all_pass:
    print("=== ALL PLATINUM IMPORTS PASSED ===")
else:
    print("=== SOME TESTS FAILED ===")
