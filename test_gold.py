"""Gold Tier - Full Test Suite"""
from pathlib import Path
from src.config import ensure_vault_structure

# 1. Vault structure
ensure_vault_structure()
print("1. Vault structure: OK")

# 2. Domain detection
from src.brain import detect_domain
biz = detect_domain("send invoice to client for payment")
personal = detect_domain("reply to my email from mom")
print(f"2. Domain detection: OK (business={biz}, personal={personal})")

# 3. Odoo accounting
from src.odoo_client import OdooClient
odoo = OdooClient()
inv = odoo.create_invoice("Client D", [{"description": "Web Dev", "quantity": 1, "unit_price": 3000}])
balance = odoo.get_account_balance()
print(f"3. Odoo: OK (Invoice #{inv['id']} = ${inv['amount']}, Bank=${balance['bank_balance']})")

# 4. Social media mocks
from src.social_media.facebook_poster import post_to_facebook, get_facebook_summary
from src.social_media.instagram_poster import post_to_instagram, get_instagram_summary
from src.social_media.twitter_poster import post_tweet, get_twitter_summary

post_to_facebook("Hello from AI Employee")
post_to_instagram("Testing Instagram mock")
post_tweet("Testing Twitter mock")
print("4. Social media mocks: OK (FB, IG, Twitter all posted)")

# 5. Audit logger
from src.audit_logger import audit
audit.log_event("test_event", actor="test", target="gold_tier", result="success")
print("5. Audit logger: OK")

# 6. Retry handler
from src.retry_handler import with_retry, graceful_degrade
with graceful_degrade("test_service"):
    pass
print("6. Retry handler: OK")

# 7. Ralph Wiggum
from src.ralph_wiggum import RalphWiggumLoop
loop = RalphWiggumLoop()
active = loop.get_active_loops()
print(f"7. Ralph Wiggum: OK (active loops: {len(active)})")

# 8. Dashboard
from src.dashboard import update_dashboard
update_dashboard()
print("8. Dashboard updated: OK (check vault/Dashboard.md)")

# 9. Summaries
print("\n--- Social Media Summaries ---")
print(get_facebook_summary())
print(get_twitter_summary())
print(get_instagram_summary())

# 10. Odoo financial summary
summary = odoo.get_financial_summary()
print("--- Odoo Financial Summary ---")
print(f"Total Invoiced: ${summary['total_invoiced']:.2f}")
print(f"Total Paid: ${summary['total_paid']:.2f}")
print(f"Collection Rate: {summary['collection_rate']:.1f}%")

print("\n=== ALL GOLD TIER TESTS PASSED ===")
