"""Test: Generate social media posts for approval"""
from src.config import ensure_vault_structure
from src.social_media.facebook_poster import create_facebook_post_for_approval
from src.social_media.instagram_poster import create_instagram_post_for_approval
from src.social_media.twitter_poster import create_tweet_for_approval

ensure_vault_structure()

# Generate posts for all 3 platforms
fb = create_facebook_post_for_approval("How AI is transforming small businesses in 2026")
ig = create_instagram_post_for_approval("Behind the scenes of building an AI Employee")
tw = create_tweet_for_approval("Latest trends in AI automation")

print(f"Facebook post: {fb.name}")
print(f"Instagram post: {ig.name}")
print(f"Tweet: {tw.name}")
print()
print("Posts are in vault/Pending_Approval/")
print()
print("To approve: move file to vault/Approved/")
print("To reject:  move file to vault/Rejected/")
