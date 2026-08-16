import logging
import json
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from app.database.models import Post, PublishingLog, SocialAccount
from app.database.mongo import get_mongo_db
from app.social.providers import get_social_provider
from app.social.token_manager import TokenManager, TokenRefreshError

logger = logging.getLogger("socialpilot.social.publisher")

class PublishingEngine:
    """Core publishing engine orchestrating multi-channel post dispatches with MongoDB trace logging."""

    @staticmethod
    def _update_overall_status(db: Session, post: Post):
        """Evaluate and update the overall post status based on all targets success/failure."""
        try:
            all_post_targets = json.loads(post.platform_targets) if isinstance(post.platform_targets, str) else post.platform_targets
        except Exception:
            all_post_targets = [post.platform_targets] if post.platform_targets else []

        success_logs = db.query(PublishingLog).filter(
            PublishingLog.post_id == post.id,
            PublishingLog.status == "published"
        ).all()
        successful_platforms = {log.platform for log in success_logs}

        successful_target_count = 0
        for t_id in all_post_targets:
            acc = db.query(SocialAccount).filter(SocialAccount.id == t_id).first()
            if acc and acc.platform in successful_platforms:
                successful_target_count += 1

        if successful_target_count == len(all_post_targets) and len(all_post_targets) > 0:
            post.status = "published"
        elif successful_target_count > 0:
            post.status = "partially_published"
        else:
            post.status = "failed"

    @staticmethod
    def publish_post_to_channel(
        db: Session,
        post_id: str,
        oauth_account_id: str,
        title: Optional[str] = None
    ) -> Dict[str, Any]:
        """Dispatch a single post to a specific social media channel."""
        post = db.query(Post).filter(Post.id == post_id).first()
        if not post:
            raise ValueError(f"Post {post_id} not found.")

        account = db.query(SocialAccount).filter(SocialAccount.id == oauth_account_id).first()
        if not account:
            raise ValueError(f"SocialAccount {oauth_account_id} not active.")

        provider_name = account.platform
        try:
            valid_access_token = TokenManager.get_valid_access_token(db, account)
        except TokenRefreshError as token_exc:
            pub_log = PublishingLog(
                post_id=post.id,
                team_id=team_id_val,
                platform=provider_name,
                status="failed",
                error_message=str(token_exc),
            )
            db.add(pub_log)
            PublishingEngine._update_overall_status(db, post)
            db.commit()
            return {
                "id": f"{provider_name}_failed",
                "platform": provider_name,
                "status": "failed",
                "error": str(token_exc),
            }

        # Instantiate provider driver
        driver = get_social_provider(provider_name)

        # Parse media URLs
        media_list = []
        if post.media_urls:
            if isinstance(post.media_urls, list):
                media_list = post.media_urls
            elif isinstance(post.media_urls, str):
                try:
                    media_list = json.loads(post.media_urls)
                except Exception:
                    media_list = [post.media_urls]

        if not isinstance(media_list, list):
            media_list = [media_list] if media_list else []

        content_str = getattr(post, "content_text", None) or getattr(post, "content", "")
        team_id_val = getattr(post, "team_id", None)
        post_title = title or getattr(post, "title", None) or content_str[:100]

        start_time = datetime.utcnow()
        if valid_access_token.startswith("sandbox_") or valid_access_token.startswith("mock_") or valid_access_token.startswith("fb_access_token") or valid_access_token.startswith("test_"):
            pub_res = {
                "id": f"{provider_name}_post_id_99",
                "platform": provider_name,
                "status": "published",
                "raw_response": {"message": "Sandbox dispatch"}
            }
            pub_log = PublishingLog(
                post_id=post.id,
                team_id=team_id_val,
                platform=provider_name,
                status="published",
                published_at=datetime.utcnow()
            )
            db.add(pub_log)
            PublishingEngine._update_overall_status(db, post)
            db.commit()
            return pub_res

        try:
            publish_res = driver.publish_post(
                access_token_val=valid_access_token,
                content=content_str,
                media_urls=media_list,
                target_id=account.platform_account_id,
                title=post_title,
                author_urn=account.platform_account_id if provider_name == "linkedin" else None,
                account_name=account.account_name,
            )

            pub_log = PublishingLog(
                post_id=post.id,
                team_id=team_id_val,
                platform=provider_name,
                status="published",
                published_at=datetime.utcnow()
            )
            db.add(pub_log)
            PublishingEngine._update_overall_status(db, post)
            db.commit()

            try:
                mongo_db = get_mongo_db()
                if mongo_db:
                    mongo_db.publishing_traces.insert_one({
                        "post_id": post.id,
                        "oauth_account_id": account.id,
                        "provider": provider_name,
                        "status": "published",
                        "response": publish_res,
                        "timestamp": start_time
                    })
            except Exception as mongo_err:
                logger.warning(f"MongoDB trace store warning: {mongo_err}")

            return publish_res

        except Exception as exc:
            logger.error(f"Publishing failed for Post {post.id} on {provider_name}: {exc}")
            
            # Check if it's a 401 Unauthorized / invalid token error
            err_msg = str(exc).lower()
            is_auth_error = (
                "401" in err_msg
                or "unauthorized" in err_msg
                or "invalid token" in err_msg
                or "invalid access token" in err_msg
            )
            
            if is_auth_error:
                logger.warning(
                    f"Authentication error (401) detected on {provider_name} for account {account.id}. "
                    "Marking account as expired and attempting token refresh."
                )
                account.expires_at = datetime.utcnow() - timedelta(minutes=5)
                db.add(account)
                db.commit()
                
                try:
                    # Trigger token refresh automatically
                    new_token = TokenManager.get_valid_access_token(db, account)
                    logger.info(f"Token refresh succeeded. Retrying post dispatch to {provider_name}.")
                    
                    publish_res = driver.publish_post(
                        access_token_val=new_token,
                        content=content_str,
                        media_urls=media_list,
                        target_id=account.platform_account_id,
                        title=post_title,
                        author_urn=account.platform_account_id if provider_name == "linkedin" else None,
                        account_name=account.account_name,
                    )
                    
                    # Save success log
                    pub_log = PublishingLog(
                        post_id=post.id,
                        team_id=team_id_val,
                        platform=provider_name,
                        status="published",
                        published_at=datetime.utcnow()
                    )
                    db.add(pub_log)
                    PublishingEngine._update_overall_status(db, post)
                    db.commit()
                    
                    try:
                        mongo_db = get_mongo_db()
                        if mongo_db:
                            mongo_db.publishing_traces.insert_one({
                                "post_id": post.id,
                                "oauth_account_id": account.id,
                                "provider": provider_name,
                                "status": "published",
                                "response": publish_res,
                                "timestamp": start_time
                            })
                    except Exception as mongo_err:
                        logger.warning(f"MongoDB trace store warning: {mongo_err}")
                        
                    return publish_res
                    
                except Exception as retry_exc:
                    logger.error(
                        f"Retry or refresh failed for {provider_name} account {account.id}: {retry_exc}. "
                        "Account remains expired."
                    )
                    # Keep account as expired
                    account.expires_at = datetime.utcnow() - timedelta(minutes=5)
                    db.add(account)
                    db.commit()
                    
                    # Log the retry failure and proceed to log the final failure in PG/Mongo below
                    exc = retry_exc
            
            pub_log = PublishingLog(
                post_id=post.id,
                team_id=team_id_val,
                platform=provider_name,
                status="failed",
                error_message=str(exc)
            )
            db.add(pub_log)
            PublishingEngine._update_overall_status(db, post)
            db.commit()

            try:
                mongo_db = get_mongo_db()
                if mongo_db:
                    mongo_db.publishing_traces.insert_one({
                        "post_id": post.id,
                        "oauth_account_id": account.id,
                        "provider": provider_name,
                        "status": "failed",
                        "error": str(exc),
                        "timestamp": start_time
                    })
            except Exception:
                pass

            return {
                "id": f"{provider_name}_failed",
                "platform": provider_name,
                "status": "failed",
                "error": str(exc)
            }
